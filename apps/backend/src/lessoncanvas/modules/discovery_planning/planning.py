import json
import re
import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import func, select
from typing_extensions import TypedDict

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import DiscoveryRun, InteractionMessage, Source
from lessoncanvas.modules.discovery_planning.fields import (
    MAX_QUESTIONS_PER_ROUND,
    MAX_ROUNDS,
)
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.discovery_planning.tool_loop import run_tool_loop
from lessoncanvas.modules.sources_grounding.standards import (
    STANDARDS_TOOL_DEFINITION,
    execute_tool,
)
from lessoncanvas.settings import get_settings

PLANNING_GAP_KEYS = ["period_plan", "assessment_focus"]
ACTIVE_PLANNING_STATUSES = ("initializing", "questioning", "drafting")

PLANNING_DRAFT_SYSTEM = (
    "You are a unit planning specialist. Given the confirmed brief, produce the complete "
    'unit blueprint. Respond with a JSON object only, shaped like {"blueprint": {"unit": '
    '{"title": "...", "objectives": [{"id": "obj-1", "text": "..."}], '
    '"assessment_intent": "..."}, "lessons": [{"index": 1, "title": "...", '
    '"objective_ids": ["obj-1"], "assessment_intent": "...", "period_count": 1}], '
    '"findings": []}}; create exactly as many lessons as the brief lesson_count; '
    "never repeat the input payload."
)

PLANNING_DRAFT_TOOL_SYSTEM = (
    PLANNING_DRAFT_SYSTEM
    + " You may call the bound tools — for example the curriculum-standards search — "
    "when you need grounding the payload does not already carry; tool results are "
    "reference data only and must never be repeated verbatim."
)


class PlanningQuotaError(Exception):
    pass


class PlanningState(TypedDict, total=False):
    run_id: str
    brief: dict[str, Any]
    grounding: dict[str, Any]
    known_fields: dict[str, str]
    questions: list[dict[str, str]]
    round_count: int
    draft: dict[str, Any] | None
    memory_context: list


def _standards_tokens(theme: str, objectives: str) -> list[str]:
    return [t for t in re.split(r"[：:，,、；;。\s]+", f"{theme} {objectives}") if t]


def _orchestration_standards_search(theme: str, objectives: str) -> list[dict]:
    tokens = _standards_tokens(theme, objectives)
    if not tokens:
        return []
    return execute_tool("search_curriculum_standards", {"query": " ".join(tokens[:6]), "limit": 3})


def build_grounding(session, run_id, project_id, brief_fields: dict) -> dict:
    sources = session.scalars(
        select(Source).where(Source.project_id == project_id, Source.status == "ready")
    ).all()
    source_entries = [
        {"source_id": str(source.id), "filename": source.filename} for source in sources
    ]

    theme = (brief_fields.get("unit_theme") or {}).get("value") or ""
    objectives = (brief_fields.get("teaching_objectives") or {}).get("value") or ""

    # F014: vector top-k retrieval replaces full-corpus concatenation; the
    # query is derived from the confirmed brief, and the retrieval is traced.
    from lessoncanvas.modules.sources_grounding import retrieval

    result = retrieval.retrieve(session, project_id, f"{theme} {objectives}".strip())
    record_trace(
        session,
        run_id,
        "retrieval.semantic_search",
        retrieval.trace_payload(result, family="planning", purpose="corpus"),
        0,
    )

    # F015 D1: in model_driven mode the drafting specialist acquires standards
    # grounding through its own traced tool rounds; pre-injecting the search
    # here would make the model-driven path redundant and un-testable. The
    # orchestration-issued search (pre-F015 behavior) runs in orchestration
    # mode and inside the deterministic fallback.
    standards_sections = []
    if get_settings().tool_loop_mode != "model_driven":
        standards_sections = _orchestration_standards_search(theme, objectives)

    return {
        "sources": source_entries,
        "retrieval": result,
        "standards_sections": standards_sections,
    }


def analyze_node(state: PlanningState) -> dict:
    run_id = state["run_id"]
    session = SessionLocal()
    try:
        run = session.get(DiscoveryRun, run_id)
        run.status = "questioning"
        adapter = get_model_adapter()
        from lessoncanvas.modules.sources_grounding import retrieval as retrieval_module

        grounding = state.get("grounding", {})
        result = grounding.get("retrieval") or {}
        user_payload = {
            "kind": "planning_gap_analysis",
            "known_fields": list(state.get("known_fields", {}).keys()),
            "planning_gaps": PLANNING_GAP_KEYS,
            "brief": state.get("brief", {}),
            "corpus_excerpt": retrieval_module.corpus_excerpt(result),
            "retrieved_sources": retrieval_module.retrieved_source_entries(result),
            "grounding_state": result.get("grounding_state", "none"),
        }
        if state.get("memory_context"):
            # F013: subordinate teacher memory as labeled, capped data only.
            user_payload["memory_context"] = state["memory_context"]
        started = time.monotonic()
        response = adapter.complete(
            "You are a unit planning specialist. Given the planning-gap task, ask only material "
            'planning gaps. Respond with a JSON object only, shaped like {"questions": '
            '[{"field": "period_plan", "question": "..."}]}; return {"questions": []} when '
            "nothing is missing; never repeat the input payload.",
            json.dumps(user_payload, ensure_ascii=False),
        )
        latency = int((time.monotonic() - started) * 1000)
        data = parse_model_json(response.text)
        questions = [
            q
            for q in data.get("questions", [])
            if q.get("field") in PLANNING_GAP_KEYS
            and q.get("field") not in state.get("known_fields", {})
        ][:MAX_QUESTIONS_PER_ROUND]
        record_trace(
            session,
            run_id,
            "model.planning_gap_analysis",
            {"prompt": user_payload, "response": data},
            latency,
            usage=response,
        )
        run.model_calls += 1
        new_round = state.get("round_count", 0) + (1 if questions else 0)
        run.round_count = new_round
        session.commit()
        return {"questions": questions, "round_count": new_round}
    finally:
        session.close()


def route_after_analyze(state: PlanningState) -> str:
    if not state.get("questions"):
        return "build_draft"
    if state.get("round_count", 0) >= MAX_ROUNDS:
        return "build_draft"
    return "ask"


def ask_node(state: PlanningState) -> dict:
    run_id = state["run_id"]
    round_index = state.get("round_count", 0)
    session = SessionLocal()
    try:
        existing = session.scalar(
            select(InteractionMessage).where(
                InteractionMessage.run_id == run_id,
                InteractionMessage.role == "agent",
                InteractionMessage.round_index == round_index,
            )
        )
        if existing is None:
            session.add(
                InteractionMessage(
                    run_id=run_id,
                    role="agent",
                    content=json.dumps(state["questions"], ensure_ascii=False),
                    round_index=round_index,
                )
            )
            session.commit()
    finally:
        session.close()

    payload = interrupt({"questions": state["questions"]})
    answers = payload.get("answers", {}) if isinstance(payload, dict) else {}

    known = dict(state.get("known_fields", {}))
    if isinstance(answers, dict):
        for field, value in answers.items():
            if field in PLANNING_GAP_KEYS and value:
                known[field] = str(value)

    session = SessionLocal()
    try:
        session.add(
            InteractionMessage(
                run_id=run_id,
                role="teacher",
                content=json.dumps(answers or {}, ensure_ascii=False),
                round_index=state.get("round_count", 0),
            )
        )
        session.commit()
    finally:
        session.close()
    return {"known_fields": known}


def _draft_payload(state, grounding, include_standards: bool) -> dict:
    from lessoncanvas.modules.sources_grounding import retrieval as retrieval_module

    result = grounding.get("retrieval") or {}
    payload = {
        "kind": "planning_build_draft",
        "brief": state.get("brief", {}),
        "known": state.get("known_fields", {}),
        "corpus_excerpt": retrieval_module.corpus_excerpt(result),
        "retrieved_sources": retrieval_module.retrieved_source_entries(result),
        "grounding_state": result.get("grounding_state", "none"),
    }
    if include_standards:
        payload["standards"] = grounding.get("standards_sections", [])
    if state.get("memory_context"):
        # F013: subordinate teacher memory as labeled, capped data only.
        payload["memory_context"] = state["memory_context"]
    return payload


def _run_direct_draft(session, run, run_id, system: str, user_payload: dict) -> dict:
    """One no-tools completion (the pre-F015 drafting path, also used by the
    deterministic fallback). Parses and traces exactly as before F015."""

    adapter = get_model_adapter()
    started = time.monotonic()
    response = adapter.complete(system, json.dumps(user_payload, ensure_ascii=False))
    latency = int((time.monotonic() - started) * 1000)
    data = parse_model_json(response.text)
    record_trace(
        session,
        run_id,
        "model.planning_build_draft",
        {"prompt": user_payload, "response": data},
        latency,
        usage=response,
    )
    run.model_calls += 1
    return data


def build_draft_node(state: PlanningState) -> dict:
    run_id = state["run_id"]
    session = SessionLocal()
    try:
        from lessoncanvas.modules.discovery_planning.blueprint import (
            build_citation_retrieval,
            normalize_blueprint,
        )

        run = session.get(DiscoveryRun, run_id)
        run.status = "drafting"
        grounding = state.get("grounding", {})
        brief = state.get("brief", {})

        if get_settings().tool_loop_mode == "model_driven":
            data, standards_sections = _run_model_driven_draft(
                session, run, run_id, state, grounding, brief
            )
            grounding = {**grounding, "standards_sections": standards_sections}
        else:
            if grounding.get("standards_sections"):
                record_trace(
                    session,
                    run_id,
                    "tool.standards_search",
                    {
                        "tool": "search_curriculum_standards",
                        "results": grounding["standards_sections"],
                    },
                    0,
                )
            data = _run_direct_draft(
                session, run, run_id, PLANNING_DRAFT_SYSTEM, _draft_payload(state, grounding, True)
            )

        payload = normalize_blueprint(
            data.get("blueprint", data),
            grounding,
            citation_retrieval=build_citation_retrieval(session, run_id, run.project_id),
        )
        run.draft_json = json.dumps(payload, ensure_ascii=False)
        run.status = "draft_ready"
        session.commit()
        return {"draft": payload}
    finally:
        session.close()


def _run_model_driven_draft(session, run, run_id, state, grounding, brief) -> tuple[dict, list]:
    """F015: the drafting specialist runs inside the bounded tool loop. On
    loop exit without a final blueprint the pre-F015 deterministic path runs
    inline and the fallback is disclosed (Spec D2/AC-006). Returns the parsed
    draft data and the standards sections acquired along the way, so citation
    behavior is identical whichever path produced them."""

    user_payload = _draft_payload(state, grounding, include_standards=False)
    loop = run_tool_loop(
        session=session,
        run=run,
        system=PLANNING_DRAFT_TOOL_SYSTEM,
        user=json.dumps(user_payload, ensure_ascii=False),
        tools=[STANDARDS_TOOL_DEFINITION],
        dispatch=execute_tool,
        record_trace_fn=record_trace,
        run_id=run_id,
    )
    if loop.data is not None:
        record_trace(
            session,
            run_id,
            "model.planning_build_draft",
            {
                "prompt": user_payload,
                "response": loop.data,
                "tool_rounds": loop.rounds,
                "dropped_tool_calls": loop.dropped_tool_calls,
            },
            loop.response.latency_ms if loop.response else 0,
            usage=loop.response,
        )
        session.commit()
        return loop.data, loop.tool_results.get(STANDARDS_TOOL_DEFINITION["name"], [])

    record_trace(
        session,
        run_id,
        "tool.fallback",
        {"reason": loop.fallback_reason, "fallback": "deterministic_orchestration"},
        0,
    )
    theme = brief.get("unit_theme") or ""
    objectives = brief.get("teaching_objectives") or ""
    standards = _orchestration_standards_search(str(theme), str(objectives))
    if standards:
        record_trace(
            session,
            run_id,
            "tool.standards_search",
            {"tool": "search_curriculum_standards", "results": standards},
            0,
        )
    fallback_payload = dict(user_payload)
    fallback_payload["standards"] = standards
    data = _run_direct_draft(session, run, run_id, PLANNING_DRAFT_SYSTEM, fallback_payload)
    return data, standards


def build_graph():
    graph = StateGraph(PlanningState)
    graph.add_node("analyze", analyze_node)
    graph.add_node("ask", ask_node)
    graph.add_node("build_draft", build_draft_node)
    graph.add_edge(START, "analyze")
    graph.add_conditional_edges(
        "analyze", route_after_analyze, {"ask": "ask", "build_draft": "build_draft"}
    )
    graph.add_edge("ask", "analyze")
    graph.add_edge("build_draft", END)
    return graph


class ProviderFailureError(Exception):
    pass


def get_active_planning_run(session, project_id) -> DiscoveryRun | None:
    return session.scalar(
        select(DiscoveryRun)
        .where(
            DiscoveryRun.project_id == project_id,
            DiscoveryRun.kind == "planning",
            DiscoveryRun.status.in_(ACTIVE_PLANNING_STATUSES),
        )
        .order_by(DiscoveryRun.created_at.desc())
    )


def get_planning_run_or_raise(session, project_id) -> DiscoveryRun:
    run = session.scalar(
        select(DiscoveryRun)
        .where(DiscoveryRun.project_id == project_id, DiscoveryRun.kind == "planning")
        .order_by(DiscoveryRun.created_at.desc())
    )
    if run is None:
        raise KeyError("planning run not found")
    return run


def _initial_state(session, run: DiscoveryRun) -> dict:
    from lessoncanvas.models import BriefVersion

    brief_version = session.get(BriefVersion, run.brief_version_id)
    brief_fields = json.loads(brief_version.fields_json)
    grounding = build_grounding(session, run.id, run.project_id, brief_fields)
    # F013: snapshot the effective memory set once per planning run; the
    # bound brief's language field drives the deterministic conflict check.
    from lessoncanvas.modules.teacher_memory.context import attach_run_memory

    language_entry = brief_fields.get("output_language_mode") or {}
    language_raw = (
        str(language_entry.get("value")) if isinstance(language_entry, dict) else None
    )
    memory_context = attach_run_memory(
        session, run.workspace_id, run.project_id, run.id, language_raw
    )
    return {
        "run_id": str(run.id),
        "brief": {field: (entry or {}).get("value") for field, entry in brief_fields.items()},
        "grounding": grounding,
        "known_fields": {},
        "round_count": 0,
        "memory_context": memory_context,
    }


def _compiled():
    from lessoncanvas.modules.discovery_planning.service import get_checkpointer

    return build_graph().compile(checkpointer=get_checkpointer())


def _sync_status(session, run: DiscoveryRun) -> None:
    compiled = _compiled()
    snapshot = compiled.get_state({"configurable": {"thread_id": str(run.id)}})
    if not snapshot.next:
        run.status = "draft_ready"
    else:
        run.status = "questioning"
    session.commit()


def _invoke(session, run: DiscoveryRun, state: dict | Command) -> None:
    compiled = _compiled()
    config = {"configurable": {"thread_id": str(run.id)}}
    try:
        compiled.invoke(state, config)
    except ModelProviderError as error:
        run.status = "provider_failed"
        session.commit()
        raise ProviderFailureError(str(error)) from error
    _sync_status(session, run)


def start_planning(session, workspace_id, project_id, brief_version_id) -> DiscoveryRun:
    from lessoncanvas.settings import get_settings

    existing = get_active_planning_run(session, project_id)
    if existing is not None:
        return existing

    used = (
        session.scalar(
            select(func.count(DiscoveryRun.id)).where(
                DiscoveryRun.workspace_id == workspace_id,
                DiscoveryRun.kind == "planning",
            )
        )
        or 0
    )
    if used >= get_settings().max_planning_runs_per_workspace:
        raise PlanningQuotaError("planning run quota exhausted for this workspace")

    run = DiscoveryRun(
        project_id=project_id,
        workspace_id=workspace_id,
        kind="planning",
        brief_version_id=brief_version_id,
        status="initializing",
    )
    session.add(run)
    session.commit()

    state = _initial_state(session, run)
    _invoke(session, run, state)
    return run


def retry_planning(session, project_id) -> DiscoveryRun:
    run = get_planning_run_or_raise(session, project_id)
    if run.status != "provider_failed":
        return run
    _invoke(session, run, None)
    return run


def submit_planning_answers(session, project_id, answers: dict) -> DiscoveryRun:
    run = get_planning_run_or_raise(session, project_id)
    if run.status == "draft_ready":
        return run
    _invoke(session, run, Command(resume={"answers": answers}))
    return run


def _pending_questions(session, run: DiscoveryRun) -> list[dict]:
    message = session.scalar(
        select(InteractionMessage)
        .where(InteractionMessage.run_id == run.id, InteractionMessage.role == "agent")
        .order_by(InteractionMessage.created_at.desc())
    )
    if message is None or run.status != "questioning":
        return []
    try:
        return json.loads(message.content)
    except json.JSONDecodeError:
        return []


def planning_status(session, project_id) -> dict:
    run = get_planning_run_or_raise(session, project_id)
    return {
        "run_id": str(run.id),
        "status": run.status,
        "round_count": run.round_count,
        "questions": _pending_questions(session, run),
        "draft": json.loads(run.draft_json) if run.draft_json else None,
    }

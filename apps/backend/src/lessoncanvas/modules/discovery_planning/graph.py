import json
import re
import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import select
from typing_extensions import TypedDict

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import InteractionMessage, SourceChunk, TraceEvent
from lessoncanvas.modules.discovery_planning.fields import (
    FIELD_LABELS,
    MAX_QUESTIONS_PER_ROUND,
    MAX_ROUNDS,
    REQUIRED_FIELDS,
)


class DiscoveryState(TypedDict, total=False):
    run_id: str
    known_fields: dict[str, str]
    questions: list[dict[str, str]]
    missing: list[str]
    round_count: int
    draft: dict[str, Any] | None
    status: str
    memory_context: list


def extract_known_fields(corpus: str) -> dict[str, str]:
    known: dict[str, str] = {}
    for field, label in FIELD_LABELS.items():
        match = re.search(rf"{label}[:：]\s*([^\n]+)", corpus)
        if match and match.group(1).strip():
            known[field] = match.group(1).strip()
    return known


def build_corpus(session, project_id) -> str:
    from lessoncanvas.models import Source

    sources = session.scalars(
        select(Source).where(Source.project_id == project_id, Source.status == "ready")
    ).all()
    parts: list[str] = []
    for source in sources:
        source_chunks = session.scalars(
            select(SourceChunk)
            .where(SourceChunk.source_id == source.id)
            .order_by(SourceChunk.position)
        ).all()
        parts.extend(chunk.text for chunk in source_chunks)
    return "\n".join(parts)


def record_trace(
    session,
    run_id: str,
    event_type: str,
    payload: dict,
    latency_ms: int,
    usage=None,
    model: str | None = None,
) -> None:
    """Append one trace event. `usage` is the model adapter's ModelResponse;
    when absent (tool calls, streams without usage) token/cost fields stay NULL
    and display as not recorded instead of zero (F006 Spec D2/D9)."""

    from lessoncanvas.modules.run_orchestration.evidence import (
        estimated_cost_usd,
        trace_model_label,
    )

    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage is not None else None
    completion_tokens = (
        getattr(usage, "completion_tokens", None) if usage is not None else None
    )
    cost = None
    model_label = None
    if prompt_tokens is not None and completion_tokens is not None:
        cost = estimated_cost_usd(prompt_tokens, completion_tokens)
        model_label = model or trace_model_label()
    session.add(
        TraceEvent(
            run_id=run_id,
            event_type=event_type,
            payload_json=json.dumps(payload, ensure_ascii=False),
            latency_ms=latency_ms,
            cost_usd=cost,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model_label,
        )
    )


def analyze_node(state: DiscoveryState) -> dict:
    run_id = state["run_id"]
    session = SessionLocal()
    try:
        from lessoncanvas.models import DiscoveryRun
        from lessoncanvas.settings import get_settings

        run = session.get(DiscoveryRun, run_id)
        if run.model_calls >= get_settings().max_model_calls_per_run:
            raise RunQuotaError("model call quota exhausted for this run")
        adapter = get_model_adapter()
        user_payload = {
            "kind": "gap_analysis",
            "known_fields": list(state.get("known_fields", {}).keys()),
            "required_fields": REQUIRED_FIELDS,
        }
        if state.get("memory_context"):
            # F013: subordinate teacher memory as labeled, capped data only.
            user_payload["memory_context"] = state["memory_context"]
        started = time.monotonic()
        response = adapter.complete(
            "You are a requirements discovery specialist. Ask only material requirement gaps. "
            "Respond with a JSON object only, shaped like "
            '\'{"questions": [{"field": "...", "question": "..."}]}\'; no prose.',
            json.dumps(user_payload, ensure_ascii=False),
        )
        latency = int((time.monotonic() - started) * 1000)
        data = parse_model_json(response.text)
        questions = data.get("questions", [])
        missing = {q.get("field") for q in questions}
        filtered = [
            q
            for q in questions
            if q.get("field") in REQUIRED_FIELDS
            and q.get("field") not in state.get("known_fields", {})
        ][:MAX_QUESTIONS_PER_ROUND]
        record_trace(
            session,
            run_id,
            "model.gap_analysis",
            {"prompt": user_payload, "response": data},
            latency,
            usage=response,
        )
        run.model_calls += 1
        new_round = state.get("round_count", 0) + (1 if filtered else 0)
        run.round_count = new_round
        session.commit()
        return {
            "questions": filtered,
            "missing": sorted(m for m in missing if m in REQUIRED_FIELDS),
            "round_count": new_round,
        }
    finally:
        session.close()


def route_after_analyze(state: DiscoveryState) -> str:
    if not state.get("questions"):
        return "build_draft"
    if state.get("round_count", 0) >= MAX_ROUNDS:
        return "build_draft"
    return "ask"


def ask_node(state: DiscoveryState) -> dict:
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
            if field in REQUIRED_FIELDS and value:
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


def build_draft_node(state: DiscoveryState) -> dict:
    run_id = state["run_id"]
    session = SessionLocal()
    try:
        from lessoncanvas.models import DiscoveryRun
        from lessoncanvas.settings import get_settings

        run = session.get(DiscoveryRun, run_id)
        if run.model_calls >= get_settings().max_model_calls_per_run:
            raise RunQuotaError("model call quota exhausted for this run")
        adapter = get_model_adapter()
        user_payload = {
            "kind": "build_draft",
            "fields": state.get("known_fields", {}),
            "required_fields": REQUIRED_FIELDS,
        }
        if state.get("memory_context"):
            # F013: subordinate teacher memory as labeled, capped data only.
            user_payload["memory_context"] = state["memory_context"]
        started = time.monotonic()
        response = adapter.complete(
            "You are a brief drafting specialist. Produce the structured requirements draft. "
            "Respond with a JSON object only, shaped like "
            '\'{"draft": {"<field>": {"value": "...", "grounding": "teacher-stated", '
            '"unresolved": false}}}\'; grounding must be "teacher-stated" or null; no prose.',
            json.dumps(user_payload, ensure_ascii=False),
        )
        latency = int((time.monotonic() - started) * 1000)
        data = parse_model_json(response.text)
        draft = data.get("draft", {})
        record_trace(
            session,
            run_id,
            "model.build_draft",
            {"prompt": user_payload, "response": data},
            latency,
            usage=response,
        )

        from lessoncanvas.models import DiscoveryRun

        run = session.get(DiscoveryRun, run_id)
        run.model_calls += 1
        run.draft_json = json.dumps(draft, ensure_ascii=False)
        run.status = "draft_ready"
        session.commit()
        return {"draft": draft, "status": "draft_ready"}
    finally:
        session.close()


def build_graph():
    graph = StateGraph(DiscoveryState)
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


class DiscoveryWorkflowError(Exception):
    pass


class RunQuotaError(Exception):
    pass


def run_workflow_error_from(exc: Exception) -> DiscoveryWorkflowError | None:
    if isinstance(exc, ModelProviderError):
        return DiscoveryWorkflowError("provider")
    return None


__all__ = ["Command", "build_graph", "build_corpus", "extract_known_fields", "DiscoveryState"]

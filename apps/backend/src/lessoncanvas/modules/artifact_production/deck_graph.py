"""Artifact production: per-lesson PPTX deck workflow (F004 D6 specialists).

Explicit LangGraph orchestration mirroring the F003 lesson-plan graph: the
unit-context assembler consumes the prerequisite lesson-plan run's structured
plans (read from its authoritative trace) as the deck writer's primary input
(Spec D3, AC-018); the deck writer produces one structured deck draft per
lesson; the deck validator performs structural checks on the rendered file.
Per-lesson semantic checkpoints live in PostgreSQL (Spec D2).
"""

import hashlib
import json
import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.modules.artifact_production.fastfail import settle_vanished_run
from lessoncanvas.modules.artifact_production.pptx_tools import (
    render_lesson_deck_pptx,
    slide_count_of,
    validate_lesson_deck_pptx,
)
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.run_orchestration import service as run_service

RETRYABLE_DECK_RETRIES = 1


class ProviderTransientError(Exception):
    """Model/provider failure eligible for bounded Celery retry against the same run."""


class CapExhaustedError(Exception):
    """Per-run model-call cap reached; no further model work may begin."""


class DeckValidationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class DeckState(TypedDict, total=False):
    run_id: str
    cursor: int
    outcome: str


def deck_artifact_key(
    workspace_id: uuid.UUID, project_id: uuid.UUID, run_id: uuid.UUID, index: int
) -> str:
    return f"artifacts/{workspace_id}/{project_id}/{run_id}/lesson-{index:02d}.pptx"


def lesson_plans_of_prerequisite(session, prerequisite_run_id) -> dict[int, dict]:
    """Structured lesson plans from the prerequisite run's authoritative trace.

    The generation trace records each lesson's structured plan response; reading
    it back keeps the confirmed plan content as the deck writer's primary input
    without introducing a second content store.
    """

    from sqlalchemy import select as sa_select

    from lessoncanvas.models import TraceEvent

    rows = session.scalars(
        sa_select(TraceEvent).where(
            TraceEvent.run_id == prerequisite_run_id,
            TraceEvent.event_type == "model.generation_write_lesson",
        )
    )
    plans: dict[int, dict] = {}
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
        except json.JSONDecodeError:
            continue
        lesson = (payload.get("prompt") or {}).get("lesson") or {}
        index = lesson.get("lesson_index")
        plan = payload.get("response") or {}
        if isinstance(index, int) and isinstance(plan, dict):
            plans[index] = plan
    return plans


def deck_writer_system_prompt(language_mode: str, max_slides: int, max_stage_slides: int) -> str:
    return (
        "You are a slide-deck writer for senior-high English units. Given one lesson's "
        "confirmed lesson plan, produce one classroom deck. Respond with a JSON object only, "
        'shaped like {"slide_deck": {"title": "...", "unit_title": "...", "objectives": ["..."], '
        '"key_points": ["..."], "difficulties": ["..."], "stage_slides": [{"heading": "...", '
        '"bullets": ["..."]}], "homework": "...", "notes": ["teacher guidance and source '
        'citations for speaker notes"]}}. Derive the teaching sequence strictly from the given '
        f"lesson plan; plan at most {max_stage_slides} stage slides per teaching stage and keep "
        f"the whole deck within {max_slides} slides (fixed skeleton: title, objectives, key "
        "points, stage slides, homework). Write learner-facing slide content in the required "
        f"language mode ({language_mode}); never repeat the input payload."
    )


def _deck_context(lesson: dict, plan: dict, brief_fields: dict, unit_title: str | None) -> dict:
    return {
        "unit_title": unit_title,
        "lesson_index": lesson.get("index"),
        "lesson_title": lesson.get("title"),
        "period_count": lesson.get("period_count"),
        "lesson_plan": plan,
        "student_context": (brief_fields.get("student_context") or {}).get("value"),
    }


def _run_active(run) -> bool:
    return run.status in ("queued", "generating", "validating")


def _superseded(session, run) -> bool:
    brief_now = run_service.current_brief_version(session, run.project_id)
    blueprint_now = run_service.current_blueprint_version(session, run.project_id)
    return (
        brief_now is None
        or blueprint_now is None
        or brief_now.id != run.brief_version_id
        or blueprint_now.id != run.blueprint_version_id
    )


def assemble_node(state: DeckState) -> dict:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(state["run_id"]))
        if run is None or not _run_active(run):
            return {"outcome": "already_finished"}
        run.status = "generating"
        session.commit()
        run_service.append_event(
            session, run.id, "phase", {"phase": "generating", "status": "generating"}
        )
        session.commit()
        return {"cursor": 0, "outcome": "running"}
    finally:
        session.close()


def process_deck_node(state: DeckState) -> dict:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import BlueprintVersion, BriefVersion, GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(state["run_id"]))
        if run is None:
            return {"outcome": "missing_run"}
        if not _run_active(run):
            return {"outcome": "stopped"}

        if _superseded(session, run):
            run.status = "superseded"
            session.commit()
            run_service.append_event(
                session,
                run.id,
                "run",
                {"status": "superseded", "reason": "newer confirmed version"},
            )
            session.commit()
            return {"outcome": "superseded"}

        artifacts = run_service.deck_artifacts_of(session, run.id)
        cursor = state.get("cursor", 0)
        if cursor >= len(artifacts):
            run.status = "validating"
            session.commit()
            run_service.append_event(session, run.id, "phase", {"phase": "validating"})
            session.commit()
            return {"outcome": "done"}

        artifact = artifacts[cursor]
        if artifact.status == "complete":
            return {"cursor": cursor + 1, "outcome": "running"}

        brief = session.get(BriefVersion, run.brief_version_id)
        blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
        blueprint_payload = json.loads(blueprint.payload_json)
        brief_fields = json.loads(brief.fields_json)
        unit_title = (blueprint_payload.get("unit") or {}).get("title")
        lesson = next(
            (
                item
                for item in blueprint_payload.get("lessons", [])
                if int(item.get("index") or 0) == artifact.lesson_index
            ),
            {"index": artifact.lesson_index},
        )

        plans = lesson_plans_of_prerequisite(session, run.prerequisite_run_id)
        plan = plans.get(artifact.lesson_index)
        if plan is None:
            artifact.status = "failed"
            artifact.failure_reason = "confirmed lesson plan content is missing"
            session.commit()
            run_service.append_event(
                session,
                run.id,
                "lesson",
                {
                    "lesson_index": artifact.lesson_index,
                    "status": "failed",
                    "reason": "confirmed lesson plan content is missing",
                },
            )
            session.commit()
            return {"cursor": cursor + 1, "outcome": "running"}

        context = _deck_context(lesson, plan, brief_fields, unit_title)

        try:
            _process_one_deck(session, run, artifact, context)
        except CapExhaustedError:
            return {"outcome": "capped"}
        except ModelProviderError as error:
            artifact.status = "failed"
            artifact.failure_reason = "provider unavailable"
            session.commit()
            run_service.append_event(
                session,
                run.id,
                "lesson",
                {"lesson_index": artifact.lesson_index, "status": "failed",
                 "reason": "provider unavailable"},
            )
            session.commit()
            raise ProviderTransientError(
                "model provider unavailable during deck generation"
            ) from error

        return {"cursor": cursor + 1, "outcome": "running"}
    finally:
        session.close()


def _process_one_deck(session, run, artifact, context: dict) -> None:
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.settings import get_settings

    adapter = get_model_adapter()
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    settings = get_settings()

    attempts = 0
    last_error: DeckValidationError | None = None
    while attempts <= RETRYABLE_DECK_RETRIES:
        attempts += 1
        if not run_service.reserve_model_call(session, run.id):
            raise CapExhaustedError("model call cap reached")
        session.commit()

        artifact.status = "drafting"
        session.commit()
        run_service.append_event(
            session, run.id, "lesson",
            {"lesson_index": artifact.lesson_index, "status": "drafting"},
        )
        session.commit()

        user_payload = {
            "kind": "generation_write_deck",
            "language_mode": artifact.language_mode,
            "lesson": context,
            "max_stage_slides": settings.deck_max_stage_slides,
            "max_slides": settings.deck_max_slides,
        }
        started = time.monotonic()
        try:
            response = adapter.complete(
                deck_writer_system_prompt(
                    artifact.language_mode, settings.deck_max_slides, settings.deck_max_stage_slides
                ),
                json.dumps(user_payload, ensure_ascii=False),
            )
        except ModelProviderError:
            session.rollback()
            raise
        latency = int((time.monotonic() - started) * 1000)
        deck = parse_model_json(response.text).get("slide_deck", {})
        record_trace(
            session,
            run.id,
            "model.generation_write_deck",
            {"prompt": user_payload, "response": deck},
            latency,
            usage=response,
        )
        session.commit()

        artifact.status = "rendering"
        session.commit()
        run_service.append_event(
            session, run.id, "lesson",
            {"lesson_index": artifact.lesson_index, "status": "rendering"},
        )
        session.commit()

        render_started = time.monotonic()
        content = render_lesson_deck_pptx(deck, artifact.lesson_index, artifact.language_mode)
        record_trace(
            session,
            run.id,
            "tool.render_lesson_deck_pptx",
            {"lesson_index": artifact.lesson_index, "size_bytes": len(content)},
            int((time.monotonic() - render_started) * 1000),
        )

        artifact.status = "validating"
        session.commit()
        validate_started = time.monotonic()
        ok, reason = validate_lesson_deck_pptx(content)
        record_trace(
            session,
            run.id,
            "tool.validate_lesson_deck_pptx",
            {"lesson_index": artifact.lesson_index, "ok": ok, "reason": reason},
            int((time.monotonic() - validate_started) * 1000),
        )
        if not ok:
            last_error = DeckValidationError(reason or "invalid deck")
            artifact.retry_count = attempts - 1
            session.commit()
            continue

        key = deck_artifact_key(run.workspace_id, run.project_id, run.id, artifact.lesson_index)
        storage.put(key, content)
        artifact.object_key = key
        artifact.checksum = hashlib.sha256(content).hexdigest()
        artifact.slide_count = slide_count_of(content)
        artifact.status = "complete"
        artifact.failure_reason = None
        session.commit()
        run_service.append_event(
            session, run.id, "lesson",
            {
                "lesson_index": artifact.lesson_index,
                "status": "complete",
                "checksum": artifact.checksum,
                "slide_count": artifact.slide_count,
            },
        )
        session.commit()
        return

    artifact.status = "failed"
    artifact.failure_reason = last_error.reason if last_error else "validation failed"
    session.commit()
    run_service.append_event(
        session, run.id, "lesson",
        {"lesson_index": artifact.lesson_index, "status": "failed",
         "reason": artifact.failure_reason},
    )
    session.commit()


def route_after_deck(state: DeckState) -> str:
    outcome = state.get("outcome", "running")
    if outcome == "running":
        return "process"
    return "finalize"


def finalize_node(state: DeckState) -> dict:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(state["run_id"]))
        if run is None:
            return {"outcome": "missing_run"}
        if run.status in (
            "complete",
            "partial_failure",
            "capped_failure",
            "superseded",
            "terminal_failure",
        ):
            return {"outcome": run.status}

        outcome = state.get("outcome", "done")
        artifacts = run_service.deck_artifacts_of(session, run.id)
        complete = sum(1 for artifact in artifacts if artifact.status == "complete")

        if outcome == "superseded" or run.status == "superseded":
            status = "superseded"
        elif outcome == "capped":
            status = "capped_failure"
        elif complete == len(artifacts) and artifacts:
            status = "complete"
        elif complete > 0:
            status = "partial_failure"
        else:
            status = "terminal_failure"

        run.status = status
        session.commit()
        run_service.append_event(
            session, run.id, "run",
            {"status": status, "complete_count": complete, "total_count": len(artifacts)},
        )
        session.commit()
        return {"outcome": status}
    finally:
        session.close()


def build_deck_graph():
    graph = StateGraph(DeckState)
    graph.add_node("assemble", assemble_node)
    graph.add_node("process", process_deck_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "assemble")
    graph.add_conditional_edges(
        "assemble", route_after_deck, {"process": "process", "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        "process", route_after_deck, {"process": "process", "finalize": "finalize"}
    )
    graph.add_edge("finalize", END)
    return graph.compile()


def execute_deck_generation(run_id: str, graph=None) -> str:
    """Run the deck workflow to a terminal or paused state; returns the run status."""

    compiled = graph or build_deck_graph()
    try:
        compiled.invoke({"run_id": run_id})
    except ProviderTransientError:
        raise
    except Exception as error:
        settled = settle_vanished_run(run_id, error)
        if settled is not None:
            return settled
        raise
    return _final_status(run_id)


def _final_status(run_id: str) -> str:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(run_id))
        return run.status if run else "missing_run"
    finally:
        session.close()


def mark_deck_provider_exhausted(run_id: str) -> str:
    """After bounded retries are exhausted, preserve completed work and settle."""

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(run_id))
        artifacts = run_service.deck_artifacts_of(session, run.id)
        complete = sum(1 for artifact in artifacts if artifact.status == "complete")
        run.status = "partial_failure" if complete > 0 else "terminal_failure"
        run.failure_json = json.dumps({"reason": "provider unavailable after bounded retries"})
        session.commit()
        run_service.append_event(
            session, run.id, "run", {"status": run.status, "reason": "provider retries exhausted"}
        )
        session.commit()
        return run.status
    finally:
        session.close()


__all__: list[Any] = [
    "CapExhaustedError",
    "ProviderTransientError",
    "deck_artifact_key",
    "build_deck_graph",
    "execute_deck_generation",
    "mark_deck_provider_exhausted",
]

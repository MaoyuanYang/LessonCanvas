"""Artifact production: per-lesson DOCX generation workflow (F003 D6 specialists).

Explicit LangGraph orchestration with three specialists — unit-context assembler,
lesson-plan writer, document renderer/validator — and per-lesson semantic
checkpoints in PostgreSQL (Spec D2). Completed lessons are never re-executed;
Redis/Celery remain transport only (ADR-0002).
"""

import hashlib
import json
import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.modules.artifact_production.docx_tools import (
    render_lesson_plan_docx,
    validate_lesson_plan_docx,
)
from lessoncanvas.modules.artifact_production.fastfail import settle_vanished_run
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.run_orchestration import service as run_service

RETRYABLE_LESSON_RETRIES = 1


class ProviderTransientError(Exception):
    """Model/provider failure eligible for bounded Celery retry against the same run."""


class CapExhaustedError(Exception):
    """Per-run model-call cap reached; no further model work may begin."""


class LessonValidationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class GenerationState(TypedDict, total=False):
    run_id: str
    cursor: int
    outcome: str


def artifact_key(
    workspace_id: uuid.UUID, project_id: uuid.UUID, run_id: uuid.UUID, index: int
) -> str:
    return f"artifacts/{workspace_id}/{project_id}/{run_id}/lesson-{index:02d}.docx"


def _objectives_text(session, blueprint_payload: dict) -> list[dict]:
    return (blueprint_payload.get("unit") or {}).get("objectives") or []


def _lesson_context(
    lesson: dict, objectives: list[dict], brief_fields: dict, unit_title: str | None
) -> dict:
    objective_ids = set(lesson.get("objective_ids") or [])
    related = [o.get("text") for o in objectives if o.get("id") in objective_ids]
    return {
        "unit_title": unit_title,
        "lesson_index": lesson.get("index"),
        "lesson_title": lesson.get("title"),
        "period_count": lesson.get("period_count"),
        "assessment_intent": lesson.get("assessment_intent"),
        "activity_outline": lesson.get("activity_outline"),
        "material_notes": lesson.get("material_notes"),
        "unit_objectives": related,
        "assessment_orientation": (brief_fields.get("assessment_orientation") or {}).get("value"),
        "student_context": (brief_fields.get("student_context") or {}).get("value"),
    }


def writer_system_prompt(language_mode: str) -> str:
    return (
        "You are a lesson-plan writer for senior-high English units. Given one lesson's "
        "context, produce one complete lesson plan. Respond with a JSON object only, shaped "
        'like {"lesson_plan": {"title": "...", "objectives": ["..."], "key_points": ["..."], '
        '"difficulties": ["..."], "stages": [{"name": "...", "duration_minutes": 10, '
        '"activities": "..."}], "homework": "..."}}; write all learner-facing content in the '
        f'required language mode ({language_mode}); never repeat the input payload.'
    )


def _run_active(run) -> bool:
    return run.status in ("queued", "generating", "validating")


def assemble_node(state: GenerationState) -> dict:
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


def process_lesson_node(state: GenerationState) -> dict:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import BlueprintVersion, BriefVersion, GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(state["run_id"]))
        if run is None:
            return {"outcome": "missing_run"}
        if not _run_active(run):
            return {"outcome": "stopped"}

        # Safe checkpoint: a newer confirmed version supersedes this run.
        brief_now = run_service.current_brief_version(session, run.project_id)
        blueprint_now = run_service.current_blueprint_version(session, run.project_id)
        if (
            brief_now is None
            or blueprint_now is None
            or brief_now.id != run.brief_version_id
            or blueprint_now.id != run.blueprint_version_id
        ):
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

        artifacts = run_service.artifacts_of(session, run.id)
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
        context = _lesson_context(
            lesson, _objectives_text(session, blueprint_payload), brief_fields, unit_title
        )

        try:
            _process_one_lesson(session, run, artifact, context)
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
            raise ProviderTransientError("model provider unavailable during generation") from error

        return {"cursor": cursor + 1, "outcome": "running"}
    finally:
        session.close()


def _process_one_lesson(session, run, artifact, context: dict) -> None:
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.settings import get_settings

    adapter = get_model_adapter()
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)

    attempts = 0
    last_error: LessonValidationError | None = None
    while attempts <= RETRYABLE_LESSON_RETRIES:
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
            "kind": "generation_write_lesson",
            "language_mode": artifact.language_mode,
            "lesson": context,
        }
        started = time.monotonic()
        try:
            response = adapter.complete(
                writer_system_prompt(artifact.language_mode),
                json.dumps(user_payload, ensure_ascii=False),
            )
        except ModelProviderError:
            session.rollback()
            raise
        latency = int((time.monotonic() - started) * 1000)
        try:
            plan = parse_model_json(response.text).get("lesson_plan", {})
        except ValueError:
            # An unparseable (e.g., truncated) response is a per-lesson
            # validation failure with bounded retry, never a provider
            # failure and never a fabricated success (F009 Spec D6/AC-007).
            record_trace(
                session,
                run.id,
                "model.generation_write_lesson",
                {"prompt": user_payload, "response": response.text[:2000], "parse_failed": True},
                latency,
                usage=response,
            )
            session.commit()
            last_error = LessonValidationError("unparseable model response")
            artifact.retry_count = attempts - 1
            session.commit()
            continue
        record_trace(
            session,
            run.id,
            "model.generation_write_lesson",
            {"prompt": user_payload, "response": plan},
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
        content = render_lesson_plan_docx(plan, artifact.lesson_index, artifact.language_mode)
        record_trace(
            session,
            run.id,
            "tool.render_lesson_plan_docx",
            {"lesson_index": artifact.lesson_index, "size_bytes": len(content)},
            int((time.monotonic() - render_started) * 1000),
        )

        artifact.status = "validating"
        session.commit()
        validate_started = time.monotonic()
        ok, reason = validate_lesson_plan_docx(content)
        record_trace(
            session,
            run.id,
            "tool.validate_lesson_plan_docx",
            {"lesson_index": artifact.lesson_index, "ok": ok, "reason": reason},
            int((time.monotonic() - validate_started) * 1000),
        )
        if not ok:
            last_error = LessonValidationError(reason or "invalid document")
            artifact.retry_count = attempts - 1
            session.commit()
            continue

        key = artifact_key(run.workspace_id, run.project_id, run.id, artifact.lesson_index)
        storage.put(key, content)
        artifact.object_key = key
        artifact.checksum = hashlib.sha256(content).hexdigest()
        artifact.status = "complete"
        artifact.failure_reason = None
        session.commit()
        run_service.append_event(
            session, run.id, "lesson",
            {
                "lesson_index": artifact.lesson_index,
                "status": "complete",
                "checksum": artifact.checksum,
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


def route_after_lesson(state: GenerationState) -> str:
    outcome = state.get("outcome", "running")
    if outcome == "running":
        return "process"
    return "finalize"


def finalize_node(state: GenerationState) -> dict:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(state["run_id"]))
        if run is None:
            return {"outcome": "missing_run"}
        # A settled run (re-dispatch no-op, or externally superseded) keeps its status.
        if run.status in (
            "complete",
            "partial_failure",
            "capped_failure",
            "superseded",
            "terminal_failure",
        ):
            return {"outcome": run.status}

        outcome = state.get("outcome", "done")
        artifacts = run_service.artifacts_of(session, run.id)
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


def build_graph():
    graph = StateGraph(GenerationState)
    graph.add_node("assemble", assemble_node)
    graph.add_node("process", process_lesson_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "assemble")
    graph.add_conditional_edges(
        "assemble", route_after_lesson, {"process": "process", "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        "process", route_after_lesson, {"process": "process", "finalize": "finalize"}
    )
    graph.add_edge("finalize", END)
    return graph.compile()


def execute_generation(run_id: str, graph=None) -> str:
    """Run the workflow to a terminal or paused state; returns the run status.

    Raises ProviderTransientError for bounded Celery retry; CapExhaustedError is
    finalized internally as capped_failure.
    """

    compiled = graph or build_graph()
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


def mark_provider_exhausted(run_id: str) -> str:
    """After bounded retries are exhausted, preserve completed work and settle."""

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(run_id))
        artifacts = run_service.artifacts_of(session, run.id)
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
    "artifact_key",
    "build_graph",
    "execute_generation",
    "mark_provider_exhausted",
]

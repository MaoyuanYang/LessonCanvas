"""Artifact production: per-lesson exercise/answer pair workflow (F005 D6
specialists).

Explicit LangGraph orchestration mirroring the F003/F004 graphs: the
unit-context assembler consumes the prerequisite lesson-plan run's structured
plans (read from its authoritative trace) plus the lesson's confirmed
blueprint objectives and the recorded difficulty tier as the exercise writer's
primary input (Spec D3, AC-018/019); the exercise writer produces one
structured exercise+answer draft per lesson; the pair validator performs
deterministic structural and pairing checks on both rendered files (Spec D7).
Per-lesson semantic checkpoints live in PostgreSQL (Spec D2); the pair is the
checkpoint unit.
"""

import hashlib
import json
import time
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter, parse_model_json
from lessoncanvas.modules.artifact_production.deck_graph import (
    lesson_plans_of_prerequisite,
)
from lessoncanvas.modules.artifact_production.exercise_docx_tools import (
    render_exercise_pair,
    validate_exercise_pair,
)
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.run_orchestration import service as run_service

RETRYABLE_EXERCISE_RETRIES = 1


class ProviderTransientError(Exception):
    """Model/provider failure eligible for bounded Celery retry against the same run."""


class CapExhaustedError(Exception):
    """Per-run model-call cap reached; no further model work may begin."""


class PairValidationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ExerciseState(TypedDict, total=False):
    run_id: str
    cursor: int
    outcome: str


def exercise_artifact_keys(
    workspace_id: uuid.UUID, project_id: uuid.UUID, run_id: uuid.UUID, index: int
) -> tuple[str, str]:
    base = f"artifacts/{workspace_id}/{project_id}/{run_id}/lesson-{index:02d}"
    return f"{base}-exercises.docx", f"{base}-answers.docx"


def exercise_writer_system_prompt(
    language_mode: str,
    difficulty: str,
    min_categories: int,
    max_categories: int,
    min_items: int,
    max_items: int,
) -> str:
    return (
        "You are an exercise writer for senior-high English units. Given one lesson's "
        "confirmed lesson plan and its confirmed blueprint objectives, produce one paired "
        "exercise and answer set. Respond with a JSON object only, shaped like "
        '{"exercise_set": {"title": "...", "instructions": "one short paragraph naming the '
        'difficulty tier and covered objectives", "categories": [{"type": "one of '
        "multiple_choice, fill_in_the_blank, short_answer, reading_comprehension, translation, "
        'written_expression", "name": "题型名", "passage": "optional reading passage text", '
        '"items": [{"stem": "...", "options": ["A. ...", "B. ..."], "answer": "...", '
        '"rationale": "optional short rationale"}]}]}}. Select between '
        f"{min_categories} and {max_categories} categories that fit the lesson's confirmed "
        f"objectives and language work; produce between {min_items} and {max_items} items in "
        "total across categories; every item MUST carry a non-empty answer (writing tasks get "
        "reference points or model text). Do not number the items yourself: the renderer "
        "assigns continuous numbering shared by both files. Write learner-facing content in "
        f"the required language mode ({language_mode}) at the selected difficulty tier "
        f"({difficulty}); never repeat the input payload."
    )


def _exercise_context(
    lesson: dict,
    plan: dict,
    brief_fields: dict,
    unit_title: str | None,
    objective_texts: list[str],
    difficulty: str,
) -> dict:
    return {
        "unit_title": unit_title,
        "lesson_index": lesson.get("index"),
        "lesson_title": lesson.get("title"),
        "confirmed_objectives": objective_texts,
        "lesson_plan": plan,
        "difficulty": difficulty,
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


def assemble_node(state: ExerciseState) -> dict:
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


def process_exercise_node(state: ExerciseState) -> dict:
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

        artifacts = run_service.exercise_artifacts_of(session, run.id)
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
        unit = blueprint_payload.get("unit") or {}
        unit_title = unit.get("title")
        objective_text_by_id = {
            str(objective.get("id")): str(objective.get("text") or "")
            for objective in (unit.get("objectives") or [])
            if isinstance(objective, dict)
        }
        lesson = next(
            (
                item
                for item in blueprint_payload.get("lessons", [])
                if int(item.get("index") or 0) == artifact.lesson_index
            ),
            {"index": artifact.lesson_index},
        )
        objective_texts = [
            objective_text_by_id[str(objective_id)]
            for objective_id in (lesson.get("objective_ids") or [])
            if str(objective_id) in objective_text_by_id
        ]

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

        context = _exercise_context(
            lesson, plan, brief_fields, unit_title, objective_texts, run.difficulty or ""
        )

        try:
            _process_one_pair(session, run, artifact, context)
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
                "model provider unavailable during exercise generation"
            ) from error

        return {"cursor": cursor + 1, "outcome": "running"}
    finally:
        session.close()


def _process_one_pair(session, run, artifact, context: dict) -> None:
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.settings import get_settings

    adapter = get_model_adapter()
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    settings = get_settings()

    attempts = 0
    last_error: PairValidationError | None = None
    while attempts <= RETRYABLE_EXERCISE_RETRIES:
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
            "kind": "generation_write_exercises",
            "language_mode": artifact.language_mode,
            "lesson": context,
            "min_categories": settings.exercise_min_categories_per_lesson,
            "max_categories": settings.exercise_max_categories_per_lesson,
            "min_items": settings.exercise_min_items_per_lesson,
            "max_items": settings.exercise_max_items_per_lesson,
        }
        started = time.monotonic()
        try:
            response = adapter.complete(
                exercise_writer_system_prompt(
                    artifact.language_mode,
                    context.get("difficulty") or "",
                    settings.exercise_min_categories_per_lesson,
                    settings.exercise_max_categories_per_lesson,
                    settings.exercise_min_items_per_lesson,
                    settings.exercise_max_items_per_lesson,
                ),
                json.dumps(user_payload, ensure_ascii=False),
            )
        except ModelProviderError:
            session.rollback()
            raise
        latency = int((time.monotonic() - started) * 1000)
        exercise_set = parse_model_json(response.text).get("exercise_set", {})
        record_trace(
            session,
            run.id,
            "model.generation_write_exercises",
            {"prompt": user_payload, "response": exercise_set},
            latency,
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
        exercise_content, answer_content = render_exercise_pair(
            exercise_set,
            artifact.lesson_index,
            artifact.language_mode,
            context.get("difficulty") or "",
        )
        record_trace(
            session,
            run.id,
            "tool.render_lesson_exercises_docx",
            {
                "lesson_index": artifact.lesson_index,
                "exercise_size_bytes": len(exercise_content),
                "answer_size_bytes": len(answer_content),
            },
            int((time.monotonic() - render_started) * 1000),
        )

        artifact.status = "validating"
        session.commit()
        validate_started = time.monotonic()
        ok, reason, stats = validate_exercise_pair(exercise_content, answer_content)
        record_trace(
            session,
            run.id,
            "tool.validate_exercise_pair",
            {"lesson_index": artifact.lesson_index, "ok": ok, "reason": reason, **stats},
            int((time.monotonic() - validate_started) * 1000),
        )
        if not ok:
            last_error = PairValidationError(reason or "invalid exercise pair")
            artifact.retry_count = attempts - 1
            session.commit()
            continue

        exercise_key, answer_key = exercise_artifact_keys(
            run.workspace_id, run.project_id, run.id, artifact.lesson_index
        )
        storage.put(exercise_key, exercise_content)
        storage.put(answer_key, answer_content)
        artifact.exercise_object_key = exercise_key
        artifact.exercise_checksum = hashlib.sha256(exercise_content).hexdigest()
        artifact.answer_object_key = answer_key
        artifact.answer_checksum = hashlib.sha256(answer_content).hexdigest()
        artifact.category_count = stats.get("category_count")
        artifact.item_count = stats.get("item_count")
        artifact.status = "complete"
        artifact.failure_reason = None
        session.commit()
        run_service.append_event(
            session, run.id, "lesson",
            {
                "lesson_index": artifact.lesson_index,
                "status": "complete",
                "exercise_checksum": artifact.exercise_checksum,
                "answer_checksum": artifact.answer_checksum,
                "item_count": artifact.item_count,
                "category_count": artifact.category_count,
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


def route_after_exercise(state: ExerciseState) -> str:
    outcome = state.get("outcome", "running")
    if outcome == "running":
        return "process"
    return "finalize"


def finalize_node(state: ExerciseState) -> dict:
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
        artifacts = run_service.exercise_artifacts_of(session, run.id)
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


def build_exercise_graph():
    graph = StateGraph(ExerciseState)
    graph.add_node("assemble", assemble_node)
    graph.add_node("process", process_exercise_node)
    graph.add_node("finalize", finalize_node)
    graph.add_edge(START, "assemble")
    graph.add_conditional_edges(
        "assemble", route_after_exercise, {"process": "process", "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        "process", route_after_exercise, {"process": "process", "finalize": "finalize"}
    )
    graph.add_edge("finalize", END)
    return graph.compile()


def execute_exercise_generation(run_id: str, graph=None) -> str:
    """Run the exercise workflow to a terminal or paused state; returns the run status."""

    compiled = graph or build_exercise_graph()
    try:
        compiled.invoke({"run_id": run_id})
    except ProviderTransientError:
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


def mark_exercise_provider_exhausted(run_id: str) -> str:
    """After bounded retries are exhausted, preserve completed work and settle."""

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(run_id))
        artifacts = run_service.exercise_artifacts_of(session, run.id)
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
    "exercise_artifact_keys",
    "build_exercise_graph",
    "execute_exercise_generation",
    "mark_exercise_provider_exhausted",
]

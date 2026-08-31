"""Generation run lifecycle: atomic idempotent start, cap accounting, event log, resume."""

import json
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.models import (
    BlueprintVersion,
    BriefVersion,
    ExerciseArtifact,
    GenerationRun,
    LessonPlanArtifact,
    RunEvent,
    SlideDeckArtifact,
)
from lessoncanvas.settings import get_settings

LESSON_PLAN_KIND = "lesson_plan"
SLIDE_DECK_KIND = "slide_deck"
EXERCISE_KIND = "exercise"

DIFFICULTY_TIERS = ("foundation", "consolidation", "advanced")


class MissingVersionsError(Exception):
    pass


class PrerequisiteNotMetError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InvalidDifficultyError(Exception):
    def __init__(self, difficulty: object) -> None:
        super().__init__(f"invalid difficulty tier: {difficulty!r}")
        self.difficulty = difficulty


class ResumeNotAllowedError(Exception):
    def __init__(self, status: str) -> None:
        super().__init__(f"resume not allowed from status {status}")
        self.status = status


def current_brief_version(session: Session, project_id: uuid.UUID) -> BriefVersion | None:
    return session.scalar(
        select(BriefVersion)
        .where(BriefVersion.project_id == project_id)
        .order_by(BriefVersion.version.desc())
    )


def current_blueprint_version(session: Session, project_id: uuid.UUID) -> BlueprintVersion | None:
    return session.scalar(
        select(BlueprintVersion)
        .where(BlueprintVersion.project_id == project_id)
        .order_by(BlueprintVersion.version.desc())
    )


def current_run(session: Session, project_id: uuid.UUID) -> GenerationRun | None:
    return session.scalar(
        select(GenerationRun)
        .where(GenerationRun.project_id == project_id)
        .where(GenerationRun.artifact_kind == LESSON_PLAN_KIND)
        .order_by(GenerationRun.created_at.desc())
    )


def current_deck_run(session: Session, project_id: uuid.UUID) -> GenerationRun | None:
    return session.scalar(
        select(GenerationRun)
        .where(GenerationRun.project_id == project_id)
        .where(GenerationRun.artifact_kind == SLIDE_DECK_KIND)
        .order_by(GenerationRun.created_at.desc())
    )


def current_exercise_run(session: Session, project_id: uuid.UUID) -> GenerationRun | None:
    return session.scalar(
        select(GenerationRun)
        .where(GenerationRun.project_id == project_id)
        .where(GenerationRun.artifact_kind == EXERCISE_KIND)
        .order_by(GenerationRun.created_at.desc())
    )


def _language_mode(brief: BriefVersion) -> str:
    fields = json.loads(brief.fields_json)
    raw = (fields.get("output_language_mode") or {}).get("value") or "zh-Hans"
    return str(raw)[:16]


def _run_for_versions(
    session: Session,
    project_id: uuid.UUID,
    brief_version_id: uuid.UUID,
    blueprint_version_id: uuid.UUID,
    artifact_kind: str,
) -> GenerationRun | None:
    return session.scalar(
        select(GenerationRun).where(
            GenerationRun.project_id == project_id,
            GenerationRun.brief_version_id == brief_version_id,
            GenerationRun.blueprint_version_id == blueprint_version_id,
            GenerationRun.artifact_kind == artifact_kind,
        )
    )


def start_generation(
    session: Session, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> tuple[GenerationRun, bool]:
    """Atomically create (or return) the idempotent generation run for the current
    confirmed brief/blueprint version pair. Returns (run, created)."""

    brief = current_brief_version(session, project_id)
    blueprint = current_blueprint_version(session, project_id)
    if brief is None or blueprint is None:
        raise MissingVersionsError("confirmed brief and blueprint versions are required")

    existing = _run_for_versions(session, project_id, brief.id, blueprint.id, LESSON_PLAN_KIND)
    if existing is not None:
        return existing, False

    payload = json.loads(blueprint.payload_json)
    lessons = payload.get("lessons") or []
    if not lessons:
        raise MissingVersionsError("confirmed blueprint contains no lessons")

    run = GenerationRun(
        project_id=project_id,
        workspace_id=workspace_id,
        brief_version_id=brief.id,
        blueprint_version_id=blueprint.id,
        artifact_kind=LESSON_PLAN_KIND,
        status="queued",
        model_call_cap=get_settings().max_model_calls_per_run,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = _run_for_versions(
            session, project_id, brief.id, blueprint.id, LESSON_PLAN_KIND
        )
        return existing, False

    language_mode = _language_mode(brief)
    for lesson in lessons:
        session.add(
            LessonPlanArtifact(
                run_id=run.id,
                project_id=project_id,
                workspace_id=workspace_id,
                lesson_index=int(lesson.get("index") or 0),
                language_mode=language_mode,
                status="pending",
            )
        )
    append_event(
        session,
        run.id,
        "run",
        {
            "status": "queued",
            "brief_version": brief.version,
            "blueprint_version": blueprint.version,
            "lesson_count": len(lessons),
            "language_mode": language_mode,
        },
    )
    session.flush()
    return run, True


def start_deck_generation(
    session: Session, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> tuple[GenerationRun, bool]:
    """Atomically create (or return) the idempotent slide-deck run for the current
    confirmed brief/blueprint version pair. Requires a complete lesson-plan run
    bound to the same versions (Spec D3). Returns (run, created)."""

    brief = current_brief_version(session, project_id)
    blueprint = current_blueprint_version(session, project_id)
    if brief is None or blueprint is None:
        raise MissingVersionsError("confirmed brief and blueprint versions are required")

    plan_run = _run_for_versions(session, project_id, brief.id, blueprint.id, LESSON_PLAN_KIND)
    if plan_run is None or plan_run.status != "complete":
        reason = (
            "lesson plans are incomplete; finish lesson-plan generation first"
            if plan_run is not None
            else "no lesson-plan run exists for the current confirmed versions"
        )
        raise PrerequisiteNotMetError(reason)

    existing = _run_for_versions(session, project_id, brief.id, blueprint.id, SLIDE_DECK_KIND)
    if existing is not None:
        return existing, False

    payload = json.loads(blueprint.payload_json)
    lessons = payload.get("lessons") or []
    if not lessons:
        raise MissingVersionsError("confirmed blueprint contains no lessons")

    run = GenerationRun(
        project_id=project_id,
        workspace_id=workspace_id,
        brief_version_id=brief.id,
        blueprint_version_id=blueprint.id,
        artifact_kind=SLIDE_DECK_KIND,
        prerequisite_run_id=plan_run.id,
        status="queued",
        model_call_cap=get_settings().max_model_calls_per_deck_run,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = _run_for_versions(
            session, project_id, brief.id, blueprint.id, SLIDE_DECK_KIND
        )
        return existing, False

    language_mode = _language_mode(brief)
    for lesson in lessons:
        session.add(
            SlideDeckArtifact(
                run_id=run.id,
                project_id=project_id,
                workspace_id=workspace_id,
                lesson_index=int(lesson.get("index") or 0),
                language_mode=language_mode,
                status="pending",
            )
        )
    append_event(
        session,
        run.id,
        "run",
        {
            "status": "queued",
            "brief_version": brief.version,
            "blueprint_version": blueprint.version,
            "lesson_count": len(lessons),
            "language_mode": language_mode,
            "prerequisite_run": str(plan_run.id),
        },
    )
    session.flush()
    return run, True


def start_exercise_generation(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    difficulty: str,
) -> tuple[GenerationRun, bool]:
    """Atomically create (or return) the idempotent exercise run for the current
    confirmed brief/blueprint version pair. Requires a complete lesson-plan run
    bound to the same versions (Spec D3) and a valid difficulty tier that is
    recorded once at creation and never overwritten (Spec D9). Returns
    (run, created)."""

    if difficulty not in DIFFICULTY_TIERS:
        raise InvalidDifficultyError(difficulty)

    brief = current_brief_version(session, project_id)
    blueprint = current_blueprint_version(session, project_id)
    if brief is None or blueprint is None:
        raise MissingVersionsError("confirmed brief and blueprint versions are required")

    plan_run = _run_for_versions(session, project_id, brief.id, blueprint.id, LESSON_PLAN_KIND)
    if plan_run is None or plan_run.status != "complete":
        reason = (
            "lesson plans are incomplete; finish lesson-plan generation first"
            if plan_run is not None
            else "no lesson-plan run exists for the current confirmed versions"
        )
        raise PrerequisiteNotMetError(reason)

    existing = _run_for_versions(session, project_id, brief.id, blueprint.id, EXERCISE_KIND)
    if existing is not None:
        return existing, False

    payload = json.loads(blueprint.payload_json)
    lessons = payload.get("lessons") or []
    if not lessons:
        raise MissingVersionsError("confirmed blueprint contains no lessons")

    run = GenerationRun(
        project_id=project_id,
        workspace_id=workspace_id,
        brief_version_id=brief.id,
        blueprint_version_id=blueprint.id,
        artifact_kind=EXERCISE_KIND,
        prerequisite_run_id=plan_run.id,
        difficulty=difficulty,
        status="queued",
        model_call_cap=get_settings().max_model_calls_per_exercise_run,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = _run_for_versions(session, project_id, brief.id, blueprint.id, EXERCISE_KIND)
        return existing, False

    language_mode = _language_mode(brief)
    for lesson in lessons:
        session.add(
            ExerciseArtifact(
                run_id=run.id,
                project_id=project_id,
                workspace_id=workspace_id,
                lesson_index=int(lesson.get("index") or 0),
                language_mode=language_mode,
                status="pending",
            )
        )
    append_event(
        session,
        run.id,
        "run",
        {
            "status": "queued",
            "brief_version": brief.version,
            "blueprint_version": blueprint.version,
            "lesson_count": len(lessons),
            "language_mode": language_mode,
            "prerequisite_run": str(plan_run.id),
            "difficulty": difficulty,
        },
    )
    session.flush()
    return run, True


def reserve_model_call(session: Session, run_id: uuid.UUID) -> bool:
    """Conditional cap guard: increments model_calls only when below the cap.

    Returns False when the cap is exhausted; the caller must stop model work.
    """

    result = session.execute(
        update(GenerationRun)
        .where(GenerationRun.id == run_id, GenerationRun.model_calls < GenerationRun.model_call_cap)
        .values(model_calls=GenerationRun.model_calls + 1)
    )
    return result.rowcount == 1


def append_event(
    session: Session, run_id: uuid.UUID, event_type: str, payload: dict
) -> RunEvent:
    """Append one event with a per-run monotonic sequence under the run row lock."""

    session.execute(
        select(GenerationRun).where(GenerationRun.id == run_id).with_for_update()
    ).scalar_one()
    next_seq = (
        session.scalar(select(func.max(RunEvent.seq)).where(RunEvent.run_id == run_id)) or 0
    ) + 1
    event = RunEvent(
        run_id=run_id,
        seq=next_seq,
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(event)
    session.flush()
    return event


def replay_events(
    session: Session, run_id: uuid.UUID, after_seq: int = 0, limit: int = 500
) -> list[RunEvent]:
    return list(
        session.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.seq > after_seq)
            .order_by(RunEvent.seq)
            .limit(limit)
        )
    )


def artifacts_of(session: Session, run_id: uuid.UUID) -> list[LessonPlanArtifact]:
    return list(
        session.scalars(
            select(LessonPlanArtifact)
            .where(LessonPlanArtifact.run_id == run_id)
            .order_by(LessonPlanArtifact.lesson_index)
        )
    )


def deck_artifacts_of(session: Session, run_id: uuid.UUID) -> list[SlideDeckArtifact]:
    return list(
        session.scalars(
            select(SlideDeckArtifact)
            .where(SlideDeckArtifact.run_id == run_id)
            .order_by(SlideDeckArtifact.lesson_index)
        )
    )


def exercise_artifacts_of(session: Session, run_id: uuid.UUID) -> list[ExerciseArtifact]:
    return list(
        session.scalars(
            select(ExerciseArtifact)
            .where(ExerciseArtifact.run_id == run_id)
            .order_by(ExerciseArtifact.lesson_index)
        )
    )


def run_snapshot(session: Session, run: GenerationRun) -> dict:
    brief = session.get(BriefVersion, run.brief_version_id)
    blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
    artifacts = artifacts_of(session, run.id)
    complete = sum(1 for artifact in artifacts if artifact.status == "complete")
    return {
        "run_id": str(run.id),
        "status": run.status,
        "brief_version": brief.version if brief else None,
        "blueprint_version": blueprint.version if blueprint else None,
        "language_mode": artifacts[0].language_mode if artifacts else "zh-Hans",
        "model_calls": run.model_calls,
        "model_call_cap": run.model_call_cap,
        "artifacts": artifacts,
        "complete_count": complete,
        "total_count": len(artifacts),
    }


def deck_run_snapshot(session: Session, run: GenerationRun) -> dict:
    brief = session.get(BriefVersion, run.brief_version_id)
    blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
    artifacts = deck_artifacts_of(session, run.id)
    complete = sum(1 for artifact in artifacts if artifact.status == "complete")
    return {
        "run_id": str(run.id),
        "status": run.status,
        "brief_version": brief.version if brief else None,
        "blueprint_version": blueprint.version if blueprint else None,
        "language_mode": artifacts[0].language_mode if artifacts else "zh-Hans",
        "model_calls": run.model_calls,
        "model_call_cap": run.model_call_cap,
        "artifacts": artifacts,
        "complete_count": complete,
        "total_count": len(artifacts),
    }


def exercise_run_snapshot(session: Session, run: GenerationRun) -> dict:
    brief = session.get(BriefVersion, run.brief_version_id)
    blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
    artifacts = exercise_artifacts_of(session, run.id)
    complete = sum(1 for artifact in artifacts if artifact.status == "complete")
    return {
        "run_id": str(run.id),
        "status": run.status,
        "brief_version": brief.version if brief else None,
        "blueprint_version": blueprint.version if blueprint else None,
        "language_mode": artifacts[0].language_mode if artifacts else "zh-Hans",
        "difficulty": run.difficulty,
        "model_calls": run.model_calls,
        "model_call_cap": run.model_call_cap,
        "artifacts": artifacts,
        "complete_count": complete,
        "total_count": len(artifacts),
    }


def resume_run(session: Session, run: GenerationRun) -> GenerationRun:
    if run.status not in ("partial_failure", "capped_failure"):
        raise ResumeNotAllowedError(run.status)
    run.status = "queued"
    session.flush()
    append_event(session, run.id, "run", {"status": "queued", "resumed": True})
    session.flush()
    return run

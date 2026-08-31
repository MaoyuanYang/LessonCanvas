"""Generation run lifecycle: atomic idempotent start, cap accounting, event log, resume.

F007 extends starts to be transition-aware: when prior family runs exist for an
older confirmed pair, a new run is created scoped to the D1-matrix affected
lessons (scope fixed at creation), and deck/exercise prerequisites generalize
to plan coverage (in-run complete or retained complete, Spec D2/D5)."""

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


class NothingToRegenerateError(Exception):
    """The version transition affects no lessons of this family (Spec D2)."""


class PrerequisiteNotMetError(Exception):
    def __init__(self, reason: str, uncovered_lessons: list[int] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.uncovered_lessons = uncovered_lessons or []


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


# F007 transition-aware current-run rule: the run bound to the current
# confirmed pair wins; an older-pair run is shown only while it is still
# active or superseded (progress/superseded feedback), never when it is
# settled — a settled old run must not mask the new pair's start surface.
FALLBACK_VISIBLE_STATUSES = ("queued", "generating", "validating", "superseded")


def _current_run_for_kind(
    session: Session, project_id: uuid.UUID, kind: str
) -> GenerationRun | None:
    brief = current_brief_version(session, project_id)
    blueprint = current_blueprint_version(session, project_id)
    if brief is not None and blueprint is not None:
        paired = session.scalar(
            select(GenerationRun)
            .where(
                GenerationRun.project_id == project_id,
                GenerationRun.artifact_kind == kind,
                GenerationRun.brief_version_id == brief.id,
                GenerationRun.blueprint_version_id == blueprint.id,
            )
            .order_by(GenerationRun.created_at.desc())
        )
        if paired is not None:
            return paired
    latest = session.scalar(
        select(GenerationRun)
        .where(GenerationRun.project_id == project_id)
        .where(GenerationRun.artifact_kind == kind)
        .order_by(GenerationRun.created_at.desc())
    )
    if latest is not None and latest.status in FALLBACK_VISIBLE_STATUSES:
        return latest
    return None


def current_run(session: Session, project_id: uuid.UUID) -> GenerationRun | None:
    return _current_run_for_kind(session, project_id, LESSON_PLAN_KIND)


def current_deck_run(session: Session, project_id: uuid.UUID) -> GenerationRun | None:
    return _current_run_for_kind(session, project_id, SLIDE_DECK_KIND)


def current_exercise_run(session: Session, project_id: uuid.UUID) -> GenerationRun | None:
    return _current_run_for_kind(session, project_id, EXERCISE_KIND)


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


def _targeted_scope(
    session: Session,
    project_id: uuid.UUID,
    kind: str,
    brief: BriefVersion,
    blueprint: BlueprintVersion,
) -> list[int] | None:
    """D1-matrix affected lessons for this family across the transition from
    the newest prior family run's pair. None = full scope (no prior runs)."""

    from lessoncanvas.modules.run_orchestration.impact import (
        compute_impact,
        family_affected_lessons,
    )

    prior = session.scalar(
        select(GenerationRun)
        .where(
            GenerationRun.project_id == project_id,
            GenerationRun.artifact_kind == kind,
        )
        .order_by(GenerationRun.created_at.desc())
    )
    if prior is None or (prior.brief_version_id, prior.blueprint_version_id) == (
        brief.id,
        blueprint.id,
    ):
        return None
    prior_brief = session.get(BriefVersion, prior.brief_version_id)
    prior_blueprint = session.get(BlueprintVersion, prior.blueprint_version_id)
    impact = compute_impact(
        prior_brief.fields_json,
        brief.fields_json,
        prior_blueprint.payload_json,
        blueprint.payload_json,
    )
    return family_affected_lessons(impact, kind)


def _plan_coverage(
    session: Session,
    project_id: uuid.UUID,
    brief: BriefVersion,
    blueprint: BlueprintVersion,
    scope: list[int] | None,
) -> tuple[bool, list[int]]:
    """Spec D2 coverage: every lesson in scope has a complete plan in the bound
    plan run or a retained complete plan under the transition."""

    from lessoncanvas.modules.run_orchestration import transition

    plan_run = _run_for_versions(session, project_id, brief.id, blueprint.id, LESSON_PLAN_KIND)
    payload = json.loads(blueprint.payload_json)
    all_lessons = [int(lesson.get("index") or 0) for lesson in payload.get("lessons", [])]
    needed = scope if scope is not None else all_lessons
    covered: set[int] = set()
    if plan_run is not None:
        covered = {
            artifact.lesson_index
            for artifact in artifacts_of(session, plan_run.id)
            if artifact.status == "complete"
        }
    uncovered = [lesson for lesson in needed if lesson not in covered]
    if uncovered:
        # Retained plans only cover lessons the plan-family matrix deems
        # unaffected; an affected lesson's prior plan is stale intent (D1/D2).
        plan_affected = _targeted_scope(session, project_id, LESSON_PLAN_KIND, brief, blueprint)
        retainable = (
            [lesson for lesson in uncovered if plan_affected is None or lesson not in plan_affected]
            if plan_affected is not None
            else []
        )
        if retainable:
            retained = {
                entry["lesson_index"]
                for entry in transition.retained_artifacts(
                    session, project_id, LESSON_PLAN_KIND, retainable, (brief.id, blueprint.id)
                )
            }
            uncovered = [lesson for lesson in uncovered if lesson not in retained]
    return (not uncovered), uncovered


def _scoped_lesson_payloads(blueprint: BlueprintVersion, scope: list[int] | None) -> list[dict]:
    payload = json.loads(blueprint.payload_json)
    lessons = payload.get("lessons") or []
    if scope is None:
        return lessons
    return [lesson for lesson in lessons if int(lesson.get("index") or 0) in set(scope)]


def _scope_out(run: GenerationRun) -> list[int] | None:
    return json.loads(run.scope_json) if run.scope_json else None


def _retained_out(
    session: Session, run: GenerationRun, kind: str, artifact_lesson_indexes: list[int]
) -> list[dict]:
    from lessoncanvas.modules.run_orchestration import transition

    if run.scope_json is None:
        return []
    blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
    payload = json.loads(blueprint.payload_json)
    all_lessons = [int(lesson.get("index") or 0) for lesson in payload.get("lessons", [])]
    retained_lessons = [
        lesson for lesson in all_lessons if lesson not in set(artifact_lesson_indexes)
    ]
    if not retained_lessons:
        return []
    return transition.retained_artifacts(
        session,
        run.project_id,
        kind,
        retained_lessons,
        (run.brief_version_id, run.blueprint_version_id),
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

    scope = _targeted_scope(session, project_id, LESSON_PLAN_KIND, brief, blueprint)
    if scope is not None and not scope:
        raise NothingToRegenerateError(
            "no affected lessons for lesson plans under the current version transition"
        )
    run = GenerationRun(
        project_id=project_id,
        workspace_id=workspace_id,
        brief_version_id=brief.id,
        blueprint_version_id=blueprint.id,
        artifact_kind=LESSON_PLAN_KIND,
        status="queued",
        model_call_cap=get_settings().max_model_calls_per_run,
        scope_json=json.dumps(scope) if scope is not None else None,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = _run_for_versions(session, project_id, brief.id, blueprint.id, LESSON_PLAN_KIND)
        return existing, False

    language_mode = _language_mode(brief)
    for lesson in _scoped_lesson_payloads(blueprint, scope):
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
            "scoped_lesson_count": len(scope) if scope is not None else len(lessons),
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
    deck_scope = _targeted_scope(session, project_id, SLIDE_DECK_KIND, brief, blueprint)
    if deck_scope is not None and not deck_scope:
        raise NothingToRegenerateError(
            "no affected lessons for slide decks under the current version transition"
        )
    covered, uncovered = _plan_coverage(session, project_id, brief, blueprint, deck_scope)
    if not covered:
        if plan_run is None:
            reason = "no lesson-plan run exists for the current confirmed versions"
        else:
            reason = (
                "lesson plans are not complete for lessons "
                f"{uncovered}; finish or retain plan coverage first"
            )
        raise PrerequisiteNotMetError(reason, uncovered)

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
        prerequisite_run_id=plan_run.id if plan_run is not None else None,
        status="queued",
        model_call_cap=get_settings().max_model_calls_per_deck_run,
        scope_json=json.dumps(deck_scope) if deck_scope is not None else None,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = _run_for_versions(session, project_id, brief.id, blueprint.id, SLIDE_DECK_KIND)
        return existing, False

    language_mode = _language_mode(brief)
    for lesson in _scoped_lesson_payloads(blueprint, deck_scope):
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
            "scoped_lesson_count": len(deck_scope) if deck_scope is not None else len(lessons),
            "language_mode": language_mode,
            "prerequisite_run": str(plan_run.id) if plan_run is not None else None,
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
    exercise_scope = _targeted_scope(session, project_id, EXERCISE_KIND, brief, blueprint)
    if exercise_scope is not None and not exercise_scope:
        raise NothingToRegenerateError(
            "no affected lessons for exercises under the current version transition"
        )
    covered, uncovered = _plan_coverage(session, project_id, brief, blueprint, exercise_scope)
    if not covered:
        if plan_run is None:
            reason = "no lesson-plan run exists for the current confirmed versions"
        else:
            reason = (
                "lesson plans are not complete for lessons "
                f"{uncovered}; finish or retain plan coverage first"
            )
        raise PrerequisiteNotMetError(reason, uncovered)

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
        prerequisite_run_id=plan_run.id if plan_run is not None else None,
        difficulty=difficulty,
        status="queued",
        model_call_cap=get_settings().max_model_calls_per_exercise_run,
        scope_json=json.dumps(exercise_scope) if exercise_scope is not None else None,
    )
    session.add(run)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        existing = _run_for_versions(session, project_id, brief.id, blueprint.id, EXERCISE_KIND)
        return existing, False

    language_mode = _language_mode(brief)
    for lesson in _scoped_lesson_payloads(blueprint, exercise_scope):
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
            "scoped_lesson_count": len(exercise_scope)
            if exercise_scope is not None
            else len(lessons),
            "language_mode": language_mode,
            "prerequisite_run": str(plan_run.id) if plan_run is not None else None,
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


def append_event(session: Session, run_id: uuid.UUID, event_type: str, payload: dict) -> RunEvent:
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
        "scope_lesson_indexes": _scope_out(run),
        "retained_artifacts": _retained_out(
            session, run, "lesson_plan", [a.lesson_index for a in artifacts]
        ),
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
        "scope_lesson_indexes": _scope_out(run),
        "retained_artifacts": _retained_out(
            session, run, "slide_deck", [a.lesson_index for a in artifacts]
        ),
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
        "scope_lesson_indexes": _scope_out(run),
        "retained_artifacts": _retained_out(
            session, run, "exercise", [a.lesson_index for a in artifacts]
        ),
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

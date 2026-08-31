"""F007 transition reads: retention lookups and the current version-transition
comparison payload. Derived projections only — artifacts keep their original
run ownership and are never copied or re-billed (Spec D5)."""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.models import (
    BlueprintVersion,
    BriefVersion,
    ExerciseArtifact,
    GenerationRun,
    LessonPlanArtifact,
    SlideDeckArtifact,
)
from lessoncanvas.modules.run_orchestration.impact import compute_impact

FAMILY_ARTIFACT_MODEL = {
    "lesson_plan": LessonPlanArtifact,
    "slide_deck": SlideDeckArtifact,
    "exercise": ExerciseArtifact,
}

FAMILIES = ("lesson_plan", "slide_deck", "exercise")


def _pair_of(run: GenerationRun) -> tuple[uuid.UUID, uuid.UUID]:
    return (run.brief_version_id, run.blueprint_version_id)


def runs_for_family(session: Session, project_id: uuid.UUID, family: str) -> list[GenerationRun]:
    return list(
        session.scalars(
            select(GenerationRun)
            .where(
                GenerationRun.project_id == project_id,
                GenerationRun.artifact_kind == family,
            )
            .order_by(GenerationRun.created_at.desc())
        )
    )


def newest_complete_artifact(
    session: Session,
    project_id: uuid.UUID,
    family: str,
    lesson_index: int,
    exclude_pair: tuple[uuid.UUID, uuid.UUID] | None = None,
):
    """Newest complete artifact for one lesson across runs of other version
    pairs (retention lookup, Spec D5)."""

    model = FAMILY_ARTIFACT_MODEL[family]
    for run in runs_for_family(session, project_id, family):
        if exclude_pair is not None and _pair_of(run) == exclude_pair:
            continue
        artifact = session.scalar(
            select(model).where(model.run_id == run.id, model.lesson_index == lesson_index)
        )
        if artifact is not None and artifact.status == "complete":
            return artifact, run
    return None, None


def retained_artifacts(
    session: Session,
    project_id: uuid.UUID,
    family: str,
    lesson_indexes: list[int],
    current_pair: tuple[uuid.UUID, uuid.UUID],
) -> list[dict]:
    """Retained entries for the given lessons under the current pair."""

    entries: list[dict] = []
    for lesson_index in lesson_indexes:
        artifact, run = newest_complete_artifact(
            session, project_id, family, lesson_index, exclude_pair=current_pair
        )
        if artifact is None:
            continue
        brief = session.get(BriefVersion, run.brief_version_id)
        blueprint = session.get(BlueprintVersion, run.blueprint_version_id)
        entries.append(
            {
                "id": str(artifact.id),
                "lesson_index": lesson_index,
                "source_brief_version": brief.version if brief else None,
                "source_blueprint_version": blueprint.version if blueprint else None,
                "source_run_id": str(run.id),
                "checksum": artifact.checksum or artifact.exercise_checksum or None,
                "download_available": True,
            }
        )
    return entries


def _lessons_of(payload_json: str | None) -> dict[int, dict]:
    if not payload_json:
        return {}
    payload = json.loads(payload_json)
    return {int(lesson.get("index") or 0): lesson for lesson in payload.get("lessons", [])}


def _brief_diff(old_fields: str | None, new_fields: str | None) -> list[dict]:
    old = json.loads(old_fields) if old_fields else {}
    new = json.loads(new_fields) if new_fields else {}
    diff: list[dict] = []
    for field in sorted(set(old) | set(new)):
        old_value = (old.get(field) or {}).get("value")
        new_value = (new.get(field) or {}).get("value")
        if old_value != new_value:
            diff.append({"field": field, "old": old_value, "new": new_value})
    return diff


def current_transition(session: Session, project_id: uuid.UUID) -> dict:
    """The current version transition for comparison (Spec D6): from/to
    versions, intent diff, per-lesson x family verdicts with reasons, and
    old/new artifact status with download availability."""

    from lessoncanvas.modules.run_orchestration import service as run_service

    current_brief = run_service.current_brief_version(session, project_id)
    current_blueprint = run_service.current_blueprint_version(session, project_id)
    if current_brief is None or current_blueprint is None:
        return {
            "first_version": True,
            "from": None,
            "to": None,
            "intent_diff": [],
            "verdicts": [],
            "artifacts": [],
        }

    current_pair = (current_brief.id, current_blueprint.id)

    # The transition source: the newest older pair that has generation runs,
    # else the newest older confirmed pair.
    blueprints = list(
        session.scalars(
            select(BlueprintVersion)
            .where(BlueprintVersion.project_id == project_id)
            .order_by(BlueprintVersion.version.desc())
        )
    )
    from_brief, from_blueprint = None, None
    for blueprint in blueprints:
        if blueprint.id == current_blueprint.id:
            continue
        has_runs = (
            session.scalar(
                select(GenerationRun.id)
                .where(GenerationRun.blueprint_version_id == blueprint.id)
                .limit(1)
            )
            is not None
        )
        if has_runs or from_blueprint is None:
            from_blueprint = blueprint
            from_brief = session.get(BriefVersion, blueprint.brief_version_id)
            if has_runs:
                break
    if from_blueprint is None or from_brief is None:
        return {
            "first_version": True,
            "from": None,
            "to": {
                "brief_version": current_brief.version,
                "blueprint_version": current_blueprint.version,
            },
            "intent_diff": [],
            "verdicts": [],
            "artifacts": [],
        }

    impact = compute_impact(
        from_brief.fields_json,
        current_brief.fields_json,
        from_blueprint.payload_json,
        current_blueprint.payload_json,
    )
    affected = impact["affected_lessons"]  # None = all
    old_lessons = _lessons_of(from_blueprint.payload_json)
    new_lessons = _lessons_of(current_blueprint.payload_json)

    verdicts: list[dict] = []
    artifacts: list[dict] = []
    for lesson_index in sorted(set(old_lessons) | set(new_lessons)):
        verdict = (
            "historical"
            if lesson_index not in new_lessons
            else "affected"
            if affected is None or lesson_index in affected
            else "retained"
        )
        for family in FAMILIES:
            verdicts.append(
                {
                    "lesson_index": lesson_index,
                    "family": family,
                    "verdict": verdict,
                    "reason": next(
                        (
                            reason["field"]
                            for reason in impact["reasons"]
                            if reason["scope"] in ("unit", f"lesson:{lesson_index}", "structural")
                        ),
                        None,
                    ),
                }
            )
            old_artifact, _old_run = newest_complete_artifact(
                session, project_id, family, lesson_index, exclude_pair=current_pair
            )
            model = FAMILY_ARTIFACT_MODEL[family]
            current_run = session.scalar(
                select(GenerationRun).where(
                    GenerationRun.project_id == project_id,
                    GenerationRun.artifact_kind == family,
                    GenerationRun.brief_version_id == current_brief.id,
                    GenerationRun.blueprint_version_id == current_blueprint.id,
                )
            )
            new_artifact = None
            if current_run is not None:
                new_artifact = session.scalar(
                    select(model).where(
                        model.run_id == current_run.id, model.lesson_index == lesson_index
                    )
                )
            artifacts.append(
                {
                    "lesson_index": lesson_index,
                    "family": family,
                    "old": {
                        "status": old_artifact.status if old_artifact else None,
                        "download_available": old_artifact is not None,
                    },
                    "new": {
                        "status": new_artifact.status if new_artifact else None,
                        "download_available": (
                            new_artifact is not None and new_artifact.status == "complete"
                        ),
                    },
                }
            )

    return {
        "first_version": False,
        "from": {
            "brief_version": from_brief.version,
            "blueprint_version": from_blueprint.version,
        },
        "to": {
            "brief_version": current_brief.version,
            "blueprint_version": current_blueprint.version,
        },
        "intent_diff": _brief_diff(from_brief.fields_json, current_brief.fields_json),
        "impact": impact,
        "verdicts": verdicts,
        "artifacts": artifacts,
    }

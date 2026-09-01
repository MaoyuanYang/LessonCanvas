"""F008 alignment computation: deterministic coverage and findings over the
current confirmed version pair (Spec D1/D5/D7). Findings are derived reads —
only teacher overrides are persisted (alignment_overrides). No model calls."""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.models import (
    AlignmentOverride,
    ExerciseArtifact,
    GenerationRun,
    LessonPlanArtifact,
    SlideDeckArtifact,
)
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.modules.run_orchestration.transition import newest_complete_artifact

FAMILIES = ("lesson_plan", "slide_deck", "exercise")

FAMILY_ARTIFACT_MODEL = {
    "lesson_plan": LessonPlanArtifact,
    "slide_deck": SlideDeckArtifact,
    "exercise": ExerciseArtifact,
}

# Product validation stays a separate, F010-owned status; F008 can only ever
# report it as not evaluated (Spec D6).
PRODUCT_VALIDATION_STATUS = "not_evaluated"

FAMILY_LABELS = {
    "lesson_plan": "lesson plan",
    "slide_deck": "slide deck",
    "exercise": "exercise and answer",
}


class MissingPairError(Exception):
    pass


def _blueprint_lessons(payload_json: str | None) -> list[dict]:
    if not payload_json:
        return []
    payload = json.loads(payload_json)
    lessons = list(payload.get("lessons") or [])
    return sorted(lessons, key=lambda lesson: int(lesson.get("index") or 0))


def _blueprint_objectives(payload_json: str | None) -> list[dict]:
    if not payload_json:
        return []
    payload = json.loads(payload_json)
    return list((payload.get("unit") or {}).get("objectives") or [])


def _member_files(artifact, family: str) -> list[dict]:
    if family == "exercise":
        files = []
        if artifact.exercise_object_key:
            files.append(
                {
                    "role": "exercise",
                    "object_key": artifact.exercise_object_key,
                    "checksum": artifact.exercise_checksum,
                }
            )
        if artifact.answer_object_key:
            files.append(
                {
                    "role": "answer",
                    "object_key": artifact.answer_object_key,
                    "checksum": artifact.answer_checksum,
                }
            )
        return files
    if artifact.object_key:
        return [
            {
                "role": "document",
                "object_key": artifact.object_key,
                "checksum": artifact.checksum,
            }
        ]
    return []


def _current_run(
    session: Session,
    project_id: uuid.UUID,
    family: str,
    brief_version_id: uuid.UUID,
    blueprint_version_id: uuid.UUID,
) -> GenerationRun | None:
    return session.scalar(
        select(GenerationRun).where(
            GenerationRun.project_id == project_id,
            GenerationRun.artifact_kind == family,
            GenerationRun.brief_version_id == brief_version_id,
            GenerationRun.blueprint_version_id == blueprint_version_id,
        )
    )


def current_members(
    session: Session, project_id: uuid.UUID, brief, blueprint
) -> dict[tuple[str, int], dict]:
    """Resolve the current package member for every (family, lesson) under the
    current confirmed pair: in-run artifact row first, then F007 retention
    (newest complete artifact from another pair), else missing."""

    lessons = _blueprint_lessons(blueprint.payload_json)
    current_pair = (brief.id, blueprint.id)
    members: dict[tuple[str, int], dict] = {}

    for family in FAMILIES:
        model = FAMILY_ARTIFACT_MODEL[family]
        run = _current_run(session, project_id, family, brief.id, blueprint.id)
        for lesson in lessons:
            lesson_index = int(lesson.get("index") or 0)
            member: dict | None = None
            if run is not None:
                artifact = session.scalar(
                    select(model).where(
                        model.run_id == run.id, model.lesson_index == lesson_index
                    )
                )
                if artifact is not None:
                    if artifact.status == "complete":
                        member = {
                            "state": "complete",
                            "provenance": "current_run",
                            "artifact_id": str(artifact.id),
                            "run_id": str(run.id),
                            "files": _member_files(artifact, family),
                        }
                    elif artifact.status == "failed":
                        member = {
                            "state": "failed",
                            "provenance": "current_run",
                            "artifact_id": str(artifact.id),
                            "run_id": str(run.id),
                            "failure_reason": artifact.failure_reason,
                            "files": _member_files(artifact, family),
                        }
                    else:
                        member = {"state": "in_progress", "provenance": "current_run"}
            if member is None:
                retained, retained_run = newest_complete_artifact(
                    session, project_id, family, lesson_index, exclude_pair=current_pair
                )
                if retained is not None:
                    member = {
                        "state": "complete",
                        "provenance": "retained",
                        "artifact_id": str(retained.id),
                        "run_id": str(retained_run.id),
                        "files": _member_files(retained, family),
                    }
            members[(family, lesson_index)] = member or {"state": "missing"}

    return members


def _overrides_for_pair(
    session: Session, project_id: uuid.UUID, brief_version_id, blueprint_version_id
) -> list[AlignmentOverride]:
    return list(
        session.scalars(
            select(AlignmentOverride).where(
                AlignmentOverride.project_id == project_id,
                AlignmentOverride.brief_version_id == brief_version_id,
                AlignmentOverride.blueprint_version_id == blueprint_version_id,
            )
        )
    )


def compute_alignment(session: Session, project_id: uuid.UUID) -> dict:
    """Deterministic alignment payload for the current confirmed pair: bound
    versions, objective coverage, per-lesson members, findings with overrides,
    technical package status, and the separate product-validation status."""

    brief = run_service.current_brief_version(session, project_id)
    blueprint = run_service.current_blueprint_version(session, project_id)
    if brief is None or blueprint is None:
        raise MissingPairError("confirmed brief and blueprint versions are required")

    lessons = _blueprint_lessons(blueprint.payload_json)
    objectives = _blueprint_objectives(blueprint.payload_json)
    members = current_members(session, project_id, brief, blueprint)
    overrides = _overrides_for_pair(session, project_id, brief.id, blueprint.id)
    active_overrides = {row.finding_key: row for row in overrides if row.status == "recorded"}

    findings: list[dict] = []

    if blueprint.stale:
        findings.append(
            {
                "key": "conflict:blueprint:stale",
                "kind": "conflict",
                "severity": "severe",
                "title": "blueprint is stale relative to a newer confirmed brief",
                "scope": "unit",
                "overridable": False,
                "recovery_action": "revise_intent",
            }
        )

    for lesson in lessons:
        lesson_index = int(lesson.get("index") or 0)
        for family in FAMILIES:
            member = members[(family, lesson_index)]
            if member["state"] == "complete":
                continue
            if member["state"] == "in_progress":
                findings.append(
                    {
                        "key": f"gap:{family}:{lesson_index}:in_progress",
                        "kind": "gap",
                        "severity": "severe",
                        "title": f"{FAMILY_LABELS[family]} for lesson {lesson_index} is still "
                        "being generated",
                        "scope": "lesson",
                        "lesson_index": lesson_index,
                        "family": family,
                        "overridable": False,
                        "recovery_action": "wait_or_resume",
                    }
                )
                continue
            if member["state"] == "failed":
                if member.get("files"):
                    findings.append(
                        {
                            "key": f"conflict:{family}:{lesson_index}:validation_failed",
                            "kind": "conflict",
                            "severity": "severe",
                            "title": f"{FAMILY_LABELS[family]} for lesson {lesson_index} failed "
                            "validation",
                            "scope": "lesson",
                            "lesson_index": lesson_index,
                            "family": family,
                            "evidence": {
                                "artifact_id": member["artifact_id"],
                                "run_id": member["run_id"],
                                "failure_reason": member.get("failure_reason"),
                            },
                            "overridable": True,
                            "recovery_action": "override_or_regenerate",
                        }
                    )
                else:
                    findings.append(
                        {
                            "key": f"gap:{family}:{lesson_index}:not_downloadable",
                            "kind": "gap",
                            "severity": "severe",
                            "title": f"{FAMILY_LABELS[family]} for lesson {lesson_index} failed "
                            "before a usable file was produced",
                            "scope": "lesson",
                            "lesson_index": lesson_index,
                            "family": family,
                            "evidence": {
                                "artifact_id": member.get("artifact_id"),
                                "run_id": member.get("run_id"),
                                "failure_reason": member.get("failure_reason"),
                            },
                            "overridable": False,
                            "recovery_action": "regenerate",
                        }
                    )
                continue
            findings.append(
                {
                    "key": f"gap:{family}:{lesson_index}:missing",
                    "kind": "gap",
                    "severity": "severe",
                    "title": f"{FAMILY_LABELS[family]} for lesson {lesson_index} is missing",
                    "scope": "lesson",
                    "lesson_index": lesson_index,
                    "family": family,
                    "overridable": False,
                    "recovery_action": "regenerate",
                }
            )

    objective_coverage: list[dict] = []
    for objective in objectives:
        objective_id = str(objective.get("id") or "")
        linked_lessons = [
            int(lesson.get("index") or 0)
            for lesson in lessons
            if objective_id in (lesson.get("objective_ids") or [])
        ]
        if not linked_lessons:
            findings.append(
                {
                    "key": f"gap:objective:{objective_id}:no_lesson",
                    "kind": "gap",
                    "severity": "severe",
                    "title": "objective is not linked to any lesson",
                    "scope": "objective",
                    "objective_id": objective_id,
                    "overridable": False,
                    "recovery_action": "revise_intent",
                }
            )
        support = {
            family: any(
                members[(family, index)]["state"] == "complete"
                for index in linked_lessons
                if (family, index) in members
            )
            for family in FAMILIES
        }
        if linked_lessons and not support["exercise"]:
            findings.append(
                {
                    "key": f"warning:objective:{objective_id}:exercise_coverage",
                    "kind": "coverage",
                    "severity": "warning",
                    "title": "objective has no completed exercise coverage",
                    "scope": "objective",
                    "objective_id": objective_id,
                    "overridable": False,
                    "recovery_action": "regenerate",
                }
            )
        supported = all(support.values())
        objective_coverage.append(
            {
                "id": objective_id,
                "text": objective.get("text"),
                "lessons": linked_lessons,
                "support": support,
                "summary": "supported" if supported else "missing" if not any(
                    support.values()
                ) else "partial",
            }
        )

    for finding in findings:
        override = active_overrides.get(finding["key"])
        finding["resolved"] = bool(override and finding.get("overridable"))
        if override is not None:
            finding["override_id"] = str(override.id)

    unresolved_severe = [
        finding
        for finding in findings
        if finding["severity"] == "severe" and not finding["resolved"]
    ]
    technical_status = "validated" if not unresolved_severe else "incomplete"

    lesson_rows = []
    for lesson in lessons:
        lesson_index = int(lesson.get("index") or 0)
        lesson_rows.append(
            {
                "lesson_index": lesson_index,
                "title": lesson.get("title"),
                "members": {
                    family: members[(family, lesson_index)] for family in FAMILIES
                },
            }
        )

    return {
        "brief_version": brief.version,
        "blueprint_version": blueprint.version,
        "brief_version_id": str(brief.id),
        "blueprint_version_id": str(blueprint.id),
        "technical_status": technical_status,
        "draft_export_available": True,
        "product_validation_status": PRODUCT_VALIDATION_STATUS,
        "objectives": objective_coverage,
        "lessons": lesson_rows,
        "findings": findings,
        "overrides": [
            {
                "id": str(row.id),
                "finding_key": row.finding_key,
                "reason": row.reason,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
                "withdrawn_at": row.withdrawn_at.isoformat() if row.withdrawn_at else None,
            }
            for row in overrides
        ],
    }

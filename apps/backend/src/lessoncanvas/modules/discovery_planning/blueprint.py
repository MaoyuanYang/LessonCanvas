import json
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from lessoncanvas.models import (
    AuditEvent,
    BlueprintDraft,
    BlueprintVersion,
    BriefVersion,
    DiscoveryRun,
)
from lessoncanvas.modules.discovery_planning.fields import FIELD_LABELS
from lessoncanvas.modules.identity_workspace.service import NotFoundError

WAIVABLE_KINDS = {"source_conflict", "standards_warning", "period_warning"}

ACTIVE_PLANNING_STATUSES = ("initializing", "questioning", "drafting")


class StaleRevisionError(Exception):
    pass


class StaleBriefError(Exception):
    pass


class ChecksFailedError(Exception):
    def __init__(self, failed: list[dict]) -> None:
        super().__init__(", ".join(c["id"] for c in failed))
        self.failed = failed


class UndecidedFindingsError(Exception):
    def __init__(self, findings: list[str]) -> None:
        super().__init__(", ".join(findings))
        self.findings = findings


class FindingDecisionError(Exception):
    pass


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_lesson_count(brief_fields: dict) -> int | None:
    raw = (brief_fields.get("lesson_count") or {}).get("value")
    if raw is None:
        return None
    match = re.search(r"\d+", str(raw))
    return int(match.group()) if match else None


def normalize_blueprint(
    raw: dict,
    grounding: dict | None = None,
) -> dict:
    """Normalize untrusted model/teacher payload into the canonical blueprint shape.

    Server-authoritative enrichment: citations are injected from verified grounding
    context (ready sources and the standards snapshot), never trusted from the payload.
    """

    grounding = grounding or {}
    standards_citation = None
    standards_sections = grounding.get("standards_sections") or []
    if standards_sections:
        first = standards_sections[0]
        standards_citation = {
            "type": "standards",
            "section_id": first.get("section_id"),
            "snapshot_version": first.get("snapshot_version"),
        }
    source_citation = None
    if grounding.get("sources"):
        first_source = grounding["sources"][0]
        source_citation = {
            "type": "source",
            "source_id": first_source.get("source_id"),
            "filename": first_source.get("filename"),
        }

    unit_raw = raw.get("unit") if isinstance(raw.get("unit"), dict) else {}
    objectives_raw = unit_raw.get("objectives")
    if not isinstance(objectives_raw, list):
        objectives_raw = []
    objectives = []
    for index, item in enumerate(objectives_raw, start=1):
        item = item if isinstance(item, dict) else {}
        text = _text(item.get("text"))
        if not text:
            continue
        citations = []
        if standards_citation:
            citations.append(dict(standards_citation))
        objectives.append({"id": f"obj-{index}", "text": text[:500], "citations": citations})

    lessons_raw = raw.get("lessons")
    if not isinstance(lessons_raw, list):
        lessons_raw = []
    lessons = []
    for index, item in enumerate(lessons_raw, start=1):
        item = item if isinstance(item, dict) else {}
        objective_ids_raw = item.get("objective_ids")
        if not isinstance(objective_ids_raw, list):
            objective_ids_raw = []
        objective_ids = sorted(
            {
                str(value)
                for value in objective_ids_raw
                if str(value) in {objective["id"] for objective in objectives}
            }
        )
        period_raw = item.get("period_count")
        period_count = int(period_raw) if isinstance(period_raw, int) and period_raw > 0 else None
        citations = []
        if source_citation:
            citations.append(dict(source_citation))
        if standards_citation and index == 1:
            citations.append(dict(standards_citation))
        lessons.append(
            {
                "index": index,
                "title": _text(item.get("title")) or f"第{index}课",
                "objective_ids": objective_ids,
                "assessment_intent": _text(item.get("assessment_intent")),
                "period_count": period_count,
                "activity_outline": _text(item.get("activity_outline")),
                "material_notes": _text(item.get("material_notes")),
                "citations": citations,
            }
        )

    findings_raw = raw.get("findings")
    if not isinstance(findings_raw, list):
        findings_raw = []
    findings = []
    for index, item in enumerate(findings_raw, start=1):
        item = item if isinstance(item, dict) else {}
        kind = item.get("kind")
        if kind not in WAIVABLE_KINDS:
            continue
        status = item.get("status")
        if status not in {"open", "resolved", "decided"}:
            status = "open"
        findings.append(
            {
                "id": _text(item.get("id")) or f"f-{index}",
                "tier": "waivable",
                "kind": kind,
                "message": _text(item.get("message")) or kind,
                "evidence": _text(item.get("evidence")),
                "status": status,
                "reason": _text(item.get("reason")) if status == "decided" else None,
            }
        )

    return {
        "unit": {
            "title": _text(unit_raw.get("title")) or "未命名单元",
            "objectives": objectives,
            "assessment_intent": _text(unit_raw.get("assessment_intent")),
            "citations": [dict(standards_citation)] if standards_citation else [],
        },
        "lessons": lessons,
        "findings": findings,
    }


def evaluate_checks(payload: dict, brief_fields: dict) -> list[dict]:
    """Derive the four D1 completeness checks server-side; blocking findings are these checks."""

    expected = parse_lesson_count(brief_fields)
    lessons = payload.get("lessons", [])

    count_passed = expected is not None and len(lessons) == expected
    count_affected = []
    if not count_passed:
        count_affected = [
            {
                "expected": expected,
                "actual": len(lessons),
            }
        ]

    fields_affected = []
    for lesson in lessons:
        missing = []
        if not lesson.get("title"):
            missing.append("title")
        if not lesson.get("objective_ids"):
            missing.append("objective_ids")
        if not lesson.get("assessment_intent"):
            missing.append("assessment_intent")
        if missing:
            fields_affected.append({"lesson_index": lesson.get("index"), "missing": missing})
    fields_passed = not fields_affected

    objective_ids = {objective["id"] for objective in payload.get("unit", {}).get("objectives", [])}
    covered: set[str] = set()
    for lesson in lessons:
        covered.update(lesson.get("objective_ids", []))
    uncovered = sorted(objective_ids - covered)
    coverage_passed = not objective_ids or not uncovered
    coverage_affected = [
        {
            "objective_id": objective_id,
            "text": next(
                (
                    objective["text"]
                    for objective in payload.get("unit", {}).get("objectives", [])
                    if objective["id"] == objective_id
                ),
                None,
            ),
        }
        for objective_id in uncovered
    ]

    return [
        {
            "id": "lesson_count",
            "label": "课时数与已确认简报一致",
            "passed": count_passed,
            "affected": count_affected,
        },
        {
            "id": "lesson_fields",
            "label": "每课必填字段完整（标题/课时目标/评估意图）",
            "passed": fields_passed,
            "affected": fields_affected,
        },
        {
            "id": "objective_coverage",
            "label": "每个单元目标至少被一课覆盖",
            "passed": coverage_passed,
            "affected": coverage_affected,
        },
    ]


def _blocking_findings(checks: list[dict]) -> list[dict]:
    return [
        {
            "id": f"check:{check['id']}",
            "tier": "blocking",
            "kind": check["id"],
            "message": check["label"],
            "evidence": json.dumps(check["affected"], ensure_ascii=False),
            "status": "open",
            "reason": None,
        }
        for check in checks
        if not check["passed"]
    ]


def sync_draft_from_run_guarded(session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> None:
    brief_version = current_brief_version(session, project_id)
    if brief_version is None:
        return
    sync_draft_from_run(session, workspace_id, project_id, brief_version)


def current_brief_version(session, project_id: uuid.UUID) -> BriefVersion | None:
    return session.scalar(
        select(BriefVersion)
        .where(BriefVersion.project_id == project_id)
        .order_by(BriefVersion.version.desc())
    )


def current_draft(session, project_id: uuid.UUID) -> BlueprintDraft | None:
    return session.scalar(
        select(BlueprintDraft)
        .where(BlueprintDraft.project_id == project_id)
        .order_by(BlueprintDraft.revision.desc())
    )


def current_version(session, project_id: uuid.UUID) -> BlueprintVersion | None:
    return session.scalar(
        select(BlueprintVersion)
        .where(BlueprintVersion.project_id == project_id)
        .order_by(BlueprintVersion.version.desc())
    )


def sync_draft_from_run(
    session, workspace_id: uuid.UUID, project_id: uuid.UUID, brief_version: BriefVersion
) -> BlueprintDraft | None:
    run = session.scalar(
        select(DiscoveryRun)
        .where(
            DiscoveryRun.project_id == project_id,
            DiscoveryRun.kind == "planning",
            DiscoveryRun.status == "draft_ready",
        )
        .order_by(DiscoveryRun.created_at.desc())
    )
    if run is None or not run.draft_json:
        return current_draft(session, project_id)

    draft = current_draft(session, project_id)
    if draft is not None and draft.source_run_id == run.id:
        return draft
    if run.brief_version_id != brief_version.id:
        return draft

    payload = json.loads(run.draft_json)
    if draft is None:
        revision = 1
    else:
        last = session.scalar(
            select(func.max(BlueprintDraft.revision)).where(BlueprintDraft.project_id == project_id)
        )
        revision = (last or 0) + 1
    new_draft = BlueprintDraft(
        project_id=project_id,
        workspace_id=workspace_id,
        brief_version_id=brief_version.id,
        revision=revision,
        source_run_id=run.id,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(new_draft)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return current_draft(session, project_id)
    return new_draft


def _brief_diff(old_fields: dict, new_fields: dict) -> list[dict]:
    diff = []
    for field, label in FIELD_LABELS.items():
        old_value = (old_fields.get(field) or {}).get("value")
        new_value = (new_fields.get(field) or {}).get("value")
        if old_value != new_value:
            diff.append(
                {
                    "field": field,
                    "label": label,
                    "old": old_value,
                    "new": new_value,
                }
            )
    return diff


def _impact_summary(diff: list[dict]) -> dict:
    fields = {entry["field"] for entry in diff}
    lesson_structure = "lesson_count" in fields
    objectives = "teaching_objectives" in fields or "unit_theme" in fields
    return {
        "lesson_structure_changed": lesson_structure,
        "objectives_changed": objectives,
        "details_changed": bool(fields),
        "summary": (
            "课时数已变化，建议重新规划全部课程"
            if lesson_structure
            else (
                "单元目标已变化，目标覆盖需要重新确认"
                if objectives
                else "简报细节已变化，请核对受影响的课程"
                if fields
                else "简报已更新"
            )
        ),
    }


def get_blueprint(session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> dict:
    brief_version = current_brief_version(session, project_id)
    if brief_version is None:
        return {
            "available": False,
            "draft_revision": None,
            "draft": None,
            "checks": [],
            "findings": [],
            "confirmed_version": None,
            "confirmed_payload": None,
            "confirmed_stale": None,
            "stale": False,
            "brief_diff": None,
            "impact_summary": None,
        }

    draft = sync_draft_from_run(session, workspace_id, project_id, brief_version)
    brief_fields = json.loads(brief_version.fields_json)

    stale = draft is not None and draft.brief_version_id != brief_version.id
    checks: list[dict] = []
    findings: list[dict] = []
    if draft is not None and not stale:
        payload = json.loads(draft.payload_json)
        checks = evaluate_checks(payload, brief_fields)
        findings = payload.get("findings", []) + _blocking_findings(checks)

    confirmed = current_version(session, project_id)
    brief_diff = None
    impact = None
    if stale and draft is not None:
        bound = session.get(BriefVersion, draft.brief_version_id)
        old_fields = json.loads(bound.fields_json) if bound else {}
        brief_diff = _brief_diff(old_fields, brief_fields)
        impact = _impact_summary(brief_diff)

    return {
        "available": True,
        "draft_revision": draft.revision if draft else None,
        "draft": json.loads(draft.payload_json) if draft else None,
        "checks": checks,
        "findings": findings,
        "confirmed_version": confirmed.version if confirmed else None,
        "confirmed_payload": json.loads(confirmed.payload_json) if confirmed else None,
        "confirmed_stale": confirmed.stale if confirmed else None,
        "stale": stale,
        "brief_diff": brief_diff,
        "impact_summary": impact,
    }


def _require_current_draft(
    session, project_id: uuid.UUID, base_revision: int
) -> tuple[BlueprintDraft, BriefVersion]:
    brief_version = current_brief_version(session, project_id)
    if brief_version is None:
        raise NotFoundError("confirmed brief not found")
    draft = current_draft(session, project_id)
    if draft is None:
        raise NotFoundError("blueprint draft not found")
    if draft.revision != base_revision:
        raise StaleRevisionError("a newer draft revision exists")
    if draft.brief_version_id != brief_version.id:
        raise StaleBriefError("draft is bound to an older confirmed brief version")
    return draft, brief_version


def patch_draft(
    session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: dict,
    base_revision: int,
) -> BlueprintDraft:
    draft, brief_version = _require_current_draft(session, project_id, base_revision)
    existing = json.loads(draft.payload_json)
    incoming = normalize_blueprint(payload)
    if "unit" in (payload or {}):
        existing["unit"] = incoming["unit"]
    if "lessons" in (payload or {}):
        existing["lessons"] = incoming["lessons"]
    if "findings" in (payload or {}):
        known = {finding["id"]: finding for finding in incoming["findings"]}
        existing["findings"] = [
            known.get(finding["id"], finding) for finding in existing.get("findings", [])
        ]
    new_draft = BlueprintDraft(
        project_id=project_id,
        workspace_id=draft.workspace_id,
        brief_version_id=brief_version.id,
        revision=draft.revision + 1,
        source_run_id=draft.source_run_id,
        payload_json=json.dumps(existing, ensure_ascii=False),
    )
    session.add(new_draft)
    session.flush()
    return new_draft


def record_decision(
    session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    finding_id: str,
    reason: str,
    base_revision: int,
) -> BlueprintDraft:
    draft, brief_version = _require_current_draft(session, project_id, base_revision)
    payload = json.loads(draft.payload_json)
    target = next(
        (finding for finding in payload.get("findings", []) if finding.get("id") == finding_id),
        None,
    )
    if target is None:
        raise FindingDecisionError("unknown finding")
    if target.get("tier") != "waivable":
        raise FindingDecisionError("blocking findings require correction, not a decision")
    if target.get("status") != "open":
        raise FindingDecisionError("finding already resolved or decided")
    target["status"] = "decided"
    target["reason"] = reason[:1000]
    new_draft = BlueprintDraft(
        project_id=project_id,
        workspace_id=draft.workspace_id,
        brief_version_id=brief_version.id,
        revision=draft.revision + 1,
        source_run_id=draft.source_run_id,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(new_draft)
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor=workspace_id.hex,
            action="blueprint.decision",
            target_type="blueprint_finding",
            target_id=finding_id,
        )
    )
    session.flush()
    return new_draft


def confirm_blueprint(
    session, workspace_id: uuid.UUID, project_id: uuid.UUID, base_revision: int
) -> BlueprintVersion:
    draft, brief_version = _require_current_draft(session, project_id, base_revision)
    payload = json.loads(draft.payload_json)
    brief_fields = json.loads(brief_version.fields_json)

    checks = evaluate_checks(payload, brief_fields)
    failed = [check for check in checks if not check["passed"]]
    if failed:
        raise ChecksFailedError(failed)

    undecided = [
        finding["id"]
        for finding in payload.get("findings", [])
        if finding.get("tier") == "waivable" and finding.get("status") == "open"
    ]
    if undecided:
        raise UndecidedFindingsError(undecided)

    existing = session.scalar(
        select(BlueprintVersion).where(
            BlueprintVersion.project_id == project_id,
            BlueprintVersion.source_revision == draft.revision,
        )
    )
    if existing is not None:
        return existing

    next_version = (
        session.scalar(
            select(func.coalesce(func.max(BlueprintVersion.version), 0)).where(
                BlueprintVersion.project_id == project_id
            )
        )
        + 1
    )
    version = BlueprintVersion(
        project_id=project_id,
        workspace_id=draft.workspace_id,
        brief_version_id=brief_version.id,
        version=next_version,
        source_revision=draft.revision,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(version)
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor=workspace_id.hex,
            action="blueprint.confirm",
            target_type="blueprint_version",
            target_id=str(version.id),
        )
    )
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return session.scalar(
            select(BlueprintVersion).where(
                BlueprintVersion.project_id == project_id,
                BlueprintVersion.source_revision == draft.revision,
            )
        )
    return version


def on_brief_version_confirmed(session, project_id: uuid.UUID, brief_version_id: uuid.UUID) -> None:
    """Same-transaction supersession: stale dependent planning state when a new brief lands."""

    active_runs = session.scalars(
        select(DiscoveryRun).where(
            DiscoveryRun.project_id == project_id,
            DiscoveryRun.kind == "planning",
            DiscoveryRun.status.in_(ACTIVE_PLANNING_STATUSES),
        )
    ).all()
    for run in active_runs:
        run.status = "superseded"

    dependent_versions = session.scalars(
        select(BlueprintVersion).where(
            BlueprintVersion.project_id == project_id,
            BlueprintVersion.brief_version_id != brief_version_id,
            BlueprintVersion.stale.is_(False),
        )
    ).all()
    for version in dependent_versions:
        version.stale = True
        version.stale_brief_version_id = brief_version_id
    session.flush()

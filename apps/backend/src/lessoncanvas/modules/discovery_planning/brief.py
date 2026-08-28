import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from lessoncanvas.models import BriefDraft, BriefVersion, DiscoveryRun
from lessoncanvas.modules.discovery_planning.fields import REQUIRED_FIELDS
from lessoncanvas.modules.identity_workspace.service import NotFoundError


class StaleRevisionError(Exception):
    pass


class MissingFieldsError(Exception):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(", ".join(missing))
        self.missing = missing


def _normalize_fields(raw: dict) -> dict:
    fields = {}
    for field in REQUIRED_FIELDS:
        entry = raw.get(field)
        if isinstance(entry, dict):
            fields[field] = {
                "value": entry.get("value"),
                "grounding": entry.get("grounding"),
                "unresolved": bool(entry.get("unresolved", not entry.get("value"))),
            }
        elif entry is None:
            fields[field] = {"value": None, "grounding": None, "unresolved": True}
        else:
            fields[field] = {
                "value": str(entry),
                "grounding": "teacher-stated",
                "unresolved": False,
            }
    return fields


def ensure_draft(session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> BriefDraft | None:
    existing = session.scalar(
        select(BriefDraft).where(BriefDraft.project_id == project_id).order_by(BriefDraft.revision)
    )
    if existing is not None:
        return existing
    run = session.scalar(
        select(DiscoveryRun)
        .where(DiscoveryRun.project_id == project_id, DiscoveryRun.status == "draft_ready")
        .order_by(DiscoveryRun.created_at.desc())
    )
    if run is None or not run.draft_json:
        return None
    draft = BriefDraft(
        project_id=project_id,
        workspace_id=workspace_id,
        revision=1,
        fields_json=json.dumps(_normalize_fields(json.loads(run.draft_json)), ensure_ascii=False),
    )
    session.add(draft)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return current_draft(session, project_id)
    return draft


def current_draft(session, project_id: uuid.UUID) -> BriefDraft | None:
    return session.scalar(
        select(BriefDraft)
        .where(BriefDraft.project_id == project_id)
        .order_by(BriefDraft.revision.desc())
    )


def current_version(session, project_id: uuid.UUID) -> BriefVersion | None:
    return session.scalar(
        select(BriefVersion)
        .where(BriefVersion.project_id == project_id)
        .order_by(BriefVersion.version.desc())
    )


def get_brief(session, project_id: uuid.UUID) -> dict:
    draft = current_draft(session, project_id)
    version = current_version(session, project_id)
    return {
        "draft_revision": draft.revision if draft else None,
        "fields": json.loads(draft.fields_json) if draft else None,
        "confirmed_version": version.version if version else None,
        "confirmed_fields": json.loads(version.fields_json) if version else None,
    }


def patch_draft(session, project_id: uuid.UUID, updates: dict, base_revision: int) -> BriefDraft:
    draft = current_draft(session, project_id)
    if draft is None:
        raise NotFoundError("brief draft not found")
    if draft.revision != base_revision:
        raise StaleRevisionError("a newer draft revision exists")
    fields = json.loads(draft.fields_json)
    for field, value in updates.items():
        if field not in REQUIRED_FIELDS:
            continue
        fields[field] = {
            "value": str(value) if value else None,
            "grounding": "teacher-stated",
            "unresolved": not value,
        }
    new_draft = BriefDraft(
        project_id=draft.project_id,
        workspace_id=draft.workspace_id,
        revision=draft.revision + 1,
        fields_json=json.dumps(fields, ensure_ascii=False),
    )
    session.add(new_draft)
    session.flush()
    return new_draft


def confirm_brief(session, project_id: uuid.UUID) -> BriefVersion:
    draft = current_draft(session, project_id)
    if draft is None:
        raise NotFoundError("brief draft not found")
    fields = json.loads(draft.fields_json)
    missing = [f for f in REQUIRED_FIELDS if not (fields.get(f) or {}).get("value")]
    if missing:
        raise MissingFieldsError(missing)

    existing = session.scalar(
        select(BriefVersion).where(
            BriefVersion.project_id == project_id, BriefVersion.source_revision == draft.revision
        )
    )
    if existing is not None:
        return existing

    next_version = (
        session.scalar(
            select(func.coalesce(func.max(BriefVersion.version), 0)).where(
                BriefVersion.project_id == project_id
            )
        )
        + 1
    )
    version = BriefVersion(
        project_id=project_id,
        workspace_id=draft.workspace_id,
        version=next_version,
        source_revision=draft.revision,
        fields_json=json.dumps(fields, ensure_ascii=False),
    )
    session.add(version)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return session.scalar(
            select(BriefVersion).where(
                BriefVersion.project_id == project_id,
                BriefVersion.source_revision == draft.revision,
            )
        )
    from lessoncanvas.modules.discovery_planning.blueprint import on_brief_version_confirmed

    on_brief_version_confirmed(session, project_id, version.id)
    return version

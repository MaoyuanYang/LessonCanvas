import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.models import AuditEvent, Project, Source, SourceChunk, Workspace
from lessoncanvas.modules.identity_workspace.service import NotFoundError
from lessoncanvas.modules.sources_grounding import parsing, policy, screening
from lessoncanvas.settings import get_settings


class SourceServiceError(Exception):
    pass


def get_owned_project_or_raise(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    allow_sample_read: bool = False,
) -> Project:
    """F012: allow_sample_read mirrors identity_workspace.get_owned_project —
    safe read paths may serve the designated synthetic sample project."""
    project = session.get(Project, project_id)
    if project is None or project.status == "deleted":
        raise NotFoundError("project not found")
    if project.workspace_id == workspace_id:
        return project
    if allow_sample_read:
        owner = session.get(Workspace, project.workspace_id)
        if owner is not None and owner.subject == get_settings().demo_owner_subject:
            return project
    raise NotFoundError("project not found")


def create_source(
    session: Session,
    storage: StorageAdapter,
    workspace_id: uuid.UUID,
    actor: str,
    project_id: uuid.UUID,
    filename: str,
    content: bytes,
    rights_acknowledged: bool,
) -> Source:
    project = get_owned_project_or_raise(session, workspace_id, project_id)
    extension = policy.validate_upload(filename, len(content), rights_acknowledged)
    # F011 D9 race safety: lock the owning project row so concurrent uploads
    # count a stable set; exactly the cap succeeds, never an overshoot.
    session.execute(select(Project).where(Project.id == project.id).with_for_update())
    count = len(
        session.scalars(
            select(Source).where(
                Source.project_id == project.id,
                Source.status.in_(
                    ["processing", "ready", "failed", "rejected", "delete_failed"]
                ),
            )
        ).all()
    )
    if count >= policy.MAX_SOURCES_PER_PROJECT:
        raise policy.SourcePolicyError("SOURCE_POLICY", "source limit of 10 per project reached")

    source = Source(
        project_id=project.id,
        workspace_id=workspace_id,
        filename=filename,
        content_type=policy.EXTENSION_CONTENT_TYPES[extension],
        size_bytes=len(content),
        status="processing",
        rights_acknowledged=rights_acknowledged,
    )
    session.add(source)
    session.flush()
    source.object_key = f"{workspace_id}/{project.id}/{source.id}{extension}"
    storage.put(source.object_key, content)
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor=actor,
            action="source.upload",
            target_type="source",
            target_id=str(source.id),
        )
    )
    session.flush()
    return source


def process_source(session: Session, storage: StorageAdapter, source_id: uuid.UUID) -> Source:
    source = session.get(Source, source_id)
    if source is None:
        raise NotFoundError("source not found")
    try:
        data = storage.get(source.object_key or "")
        text = parsing.extract_text(source.filename, data)
    except parsing.ParseError as error:
        source.status = "failed"
        source.rejection_code = "PARSE_FAILED"
        source.rejection_message = str(error)
        session.flush()
        return source

    violation = screening.screen_for_student_data(text)
    if violation is not None:
        source.status = "rejected"
        source.rejection_code = "STUDENT_DATA"
        source.rejection_message = violation
        session.flush()
        return source

    session.query(SourceChunk).filter(SourceChunk.source_id == source.id).delete()
    for position, chunk in enumerate(parsing.chunk_text(text)):
        session.add(SourceChunk(source_id=source.id, position=position, text=chunk))
    source.status = "ready"
    source.rejection_code = None
    source.rejection_message = None
    session.flush()
    return source


def list_sources(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    *,
    allow_sample_read: bool = False,
) -> list[Source]:
    get_owned_project_or_raise(
        session, workspace_id, project_id, allow_sample_read=allow_sample_read
    )
    return list(
        session.scalars(
            select(Source)
            .where(Source.project_id == project_id, Source.status != "deleted")
            .order_by(Source.created_at)
        )
    )


def get_source(
    session: Session,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    allow_sample_read: bool = False,
) -> Source:
    get_owned_project_or_raise(
        session, workspace_id, project_id, allow_sample_read=allow_sample_read
    )
    source = session.get(Source, source_id)
    if source is None or source.status == "deleted":
        raise NotFoundError("source not found")
    if source.workspace_id == workspace_id:
        return source
    if allow_sample_read:
        owner = session.get(Workspace, source.workspace_id)
        if owner is not None and owner.subject == get_settings().demo_owner_subject:
            return source
    raise NotFoundError("source not found")


def delete_source(
    session: Session,
    storage: StorageAdapter,
    workspace_id: uuid.UUID,
    actor: str,
    project_id: uuid.UUID,
    source_id: uuid.UUID,
) -> bool:
    """Delete a source and its object; True when fully deleted.

    On object-store failure the row settles delete_failed (visible, repairable)
    and returns False — the private object must never be stranded silently.
    """
    source = get_source(session, workspace_id, project_id, source_id)
    if source.object_key:
        try:
            storage.delete(source.object_key)
        except Exception:
            # F011 D5: an object-store failure must stay visible and
            # repairable; silently dropping the row would strand private
            # content with no recovery path. A re-issued delete converges it.
            source.status = "delete_failed"
            session.add(
                AuditEvent(
                    workspace_id=workspace_id,
                    actor=actor,
                    action="source.deletion_failed",
                    target_type="source",
                    target_id=str(source.id),
                )
            )
            session.flush()
            return False
    session.query(SourceChunk).filter(SourceChunk.source_id == source.id).delete()
    session.delete(source)
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor=actor,
            action="source.delete",
            target_type="source",
            target_id=str(source.id),
        )
    )
    session.flush()
    return True

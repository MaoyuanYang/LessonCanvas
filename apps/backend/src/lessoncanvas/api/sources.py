import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.api.deps import SessionDep, WorkspaceDep, require_expensive_rate
from lessoncanvas.api.errors import NotFoundError, QuotaExceededError, RequirementError
from lessoncanvas.modules.identity_workspace.limits import UPLOAD_DAILY_CLASS, consume_rate
from lessoncanvas.modules.identity_workspace.service import NotFoundError as ServiceNotFound
from lessoncanvas.modules.sources_grounding import policy, service
from lessoncanvas.modules.sources_grounding.tasks import parse_source
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["sources"])

storage = StorageAdapter()

DAY_SECONDS = 24 * 3600


class SourceOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    rejection_code: str | None
    rejection_message: str | None
    rights_acknowledged: bool
    created_at: datetime
    updated_at: datetime


def to_out(source) -> SourceOut:
    return SourceOut(
        id=source.id,
        filename=source.filename,
        content_type=source.content_type,
        size_bytes=source.size_bytes,
        status=source.status,
        rejection_code=source.rejection_code,
        rejection_message=source.rejection_message,
        rights_acknowledged=source.rights_acknowledged,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def enqueue_parse(source_id: uuid.UUID) -> None:
    if get_settings().tasks_eager:
        parse_source.apply(args=[str(source_id)])
    else:
        parse_source.delay(str(source_id))


@router.post("", status_code=201, response_model=SourceOut,
             dependencies=[Depends(require_expensive_rate)])
def upload_source(
    project_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    rights_acknowledged: Annotated[bool, Form()] = False,
) -> SourceOut:
    try:
        content = policy.validate_upload_stream(
            file.filename or "unnamed", rights_acknowledged, file.file
        )
    except policy.SourcePolicyError as err:
        session.rollback()
        raise RequirementError(err.message, {"code": err.code}) from err
    settings = get_settings()
    allowed, details = consume_rate(
        session,
        workspace.id,
        UPLOAD_DAILY_CLASS,
        settings.upload_daily_bytes_per_workspace,
        DAY_SECONDS,
        bytes_accum=len(content),
    )
    session.commit()
    if not allowed:
        raise QuotaExceededError("daily upload volume limit reached", details)
    try:
        source = service.create_source(
            session,
            storage,
            workspace.id,
            workspace.clerk_user_id,
            project_id,
            file.filename or "unnamed",
            content,
            rights_acknowledged,
        )
        session.commit()
    except policy.SourcePolicyError as err:
        session.rollback()
        raise RequirementError(err.message, {"code": err.code}) from err
    except ServiceNotFound as err:
        session.rollback()
        raise NotFoundError("project not found") from err
    enqueue_parse(source.id)
    session.refresh(source)
    return to_out(source)


@router.get("", response_model=list[SourceOut])
def list_sources(
    project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
) -> list[SourceOut]:
    try:
        sources = service.list_sources(session, workspace.id, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err
    return [to_out(s) for s in sources]


@router.get("/{source_id}", response_model=SourceOut)
def get_source(
    project_id: uuid.UUID, source_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
) -> SourceOut:
    try:
        source = service.get_source(session, workspace.id, project_id, source_id)
    except ServiceNotFound as err:
        raise NotFoundError("source not found") from err
    return to_out(source)


@router.delete("/{source_id}", status_code=204)
def delete_source(
    project_id: uuid.UUID, source_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
):
    try:
        deleted = service.delete_source(
            session, storage, workspace.id, workspace.clerk_user_id, project_id, source_id
        )
        session.commit()
    except ServiceNotFound as err:
        session.rollback()
        raise NotFoundError("source not found") from err
    if not deleted:
        # F011 D5: object-store failure keeps the row visible and repairable.
        return JSONResponse(
            status_code=200, content={"deleted": False, "status": "delete_failed"}
        )
    return Response(status_code=204)

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import (
    MemoryLimitError,
    NotFoundError,
    StaleVersionError,
)
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project
from lessoncanvas.modules.teacher_memory import service as memory_service
from lessoncanvas.modules.teacher_memory.service import (
    MemoryCapError,
    MemoryNotFoundError,
    ProposalStateError,
)

router = APIRouter(prefix="/memory", tags=["memory"])
project_router = APIRouter(prefix="/projects/{project_id}/memory", tags=["memory"])


class ProposalConfirmIn(BaseModel):
    content: str | None = None


class RecordEditIn(BaseModel):
    content: str


class OverrideIn(BaseModel):
    enabled: bool


def _pass_out(row) -> dict:
    return memory_service._pass_out(row)


@router.get("")
def list_memory(workspace: WorkspaceDep, session: SessionDep) -> dict:
    return memory_service.list_memory(session, workspace)


@router.post("/proposals/{proposal_id}/confirm")
def confirm_proposal(
    proposal_id: uuid.UUID,
    body: ProposalConfirmIn,
    workspace: WorkspaceDep,
    session: SessionDep,
) -> dict:
    try:
        record, _created = memory_service.confirm_proposal(
            session, workspace, proposal_id, body.content
        )
    except MemoryNotFoundError as err:
        raise NotFoundError("memory proposal not found") from err
    except ProposalStateError as err:
        raise StaleVersionError(str(err)) from err
    except MemoryCapError as err:
        raise MemoryLimitError(err.reason, err.details) from err
    session.commit()
    return memory_service._record_out(session, record)


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
) -> dict:
    try:
        proposal = memory_service.reject_proposal(session, workspace, proposal_id)
    except MemoryNotFoundError as err:
        raise NotFoundError("memory proposal not found") from err
    except ProposalStateError as err:
        raise StaleVersionError(str(err)) from err
    session.commit()
    from lessoncanvas.models import MemoryPass

    pass_row = session.get(MemoryPass, proposal.pass_id)
    return memory_service._proposal_out(
        proposal, pass_row.trigger_kind if pass_row else None
    )


@router.post("/passes/{pass_id}/retry")
def retry_pass(pass_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> dict:
    try:
        row = memory_service.retry_pass(session, workspace, pass_id)
    except MemoryNotFoundError as err:
        raise NotFoundError("memory pass not found") from err
    except ProposalStateError as err:
        raise StaleVersionError(str(err)) from err
    return _pass_out(row)


@router.patch("/records/{record_id}")
def edit_record(
    record_id: uuid.UUID, body: RecordEditIn, workspace: WorkspaceDep, session: SessionDep
) -> dict:
    try:
        record = memory_service.edit_record(session, workspace, record_id, body.content)
    except MemoryNotFoundError as err:
        raise NotFoundError("memory record not found") from err
    except MemoryCapError as err:
        raise MemoryLimitError(err.reason, err.details) from err
    session.commit()
    return memory_service._record_out(session, record)


@router.delete("/records/{record_id}")
def delete_record(record_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> dict:
    try:
        memory_service.delete_record(session, workspace, record_id)
    except MemoryNotFoundError as err:
        raise NotFoundError("memory record not found") from err
    session.commit()
    return {"deleted": True}


@project_router.get("")
def project_memory(
    project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
) -> dict:
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err
    return memory_service.project_memory(session, workspace, project_id)


@project_router.post("/records/{record_id}/override")
def set_override(
    project_id: uuid.UUID,
    record_id: uuid.UUID,
    body: OverrideIn,
    workspace: WorkspaceDep,
    session: SessionDep,
) -> dict:
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err
    try:
        memory_service.set_override(
            session, workspace, project_id, record_id, body.enabled
        )
    except MemoryNotFoundError as err:
        raise NotFoundError("memory record not found") from err
    session.commit()
    return {"record_id": str(record_id), "enabled": body.enabled}

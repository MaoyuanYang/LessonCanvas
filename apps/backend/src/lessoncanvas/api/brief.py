import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, RequirementError, StaleVersionError
from lessoncanvas.modules.discovery_planning import brief as brief_service
from lessoncanvas.modules.discovery_planning.brief import (
    MissingFieldsError,
    StaleRevisionError,
)
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)

router = APIRouter(prefix="/projects/{project_id}/brief", tags=["brief"])


class BriefOut(BaseModel):
    draft_revision: int | None
    fields: dict | None
    confirmed_version: int | None
    confirmed_fields: dict | None


class DraftPatch(BaseModel):
    fields: dict
    base_revision: int


class ConfirmOut(BaseModel):
    version: int
    fields: dict


def _owned(session, workspace, project_id, *, sample_read: bool = False):
    try:
        get_owned_project(session, workspace, project_id, allow_sample_read=sample_read)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


@router.get("", response_model=BriefOut)
def get_brief(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> BriefOut:
    _owned(session, workspace, project_id, sample_read=True)
    brief_service.ensure_draft(session, workspace.id, project_id)
    session.commit()
    return BriefOut(**brief_service.get_brief(session, project_id))


@router.patch("/draft", response_model=BriefOut)
def patch_draft(
    project_id: uuid.UUID, body: DraftPatch, workspace: WorkspaceDep, session: SessionDep
) -> BriefOut:
    _owned(session, workspace, project_id)
    brief_service.ensure_draft(session, workspace.id, project_id)
    session.commit()
    try:
        brief_service.patch_draft(session, project_id, body.fields, body.base_revision)
        session.commit()
    except StaleRevisionError as err:
        session.rollback()
        raise StaleVersionError("a newer draft revision exists") from err
    except ServiceNotFound as err:
        session.rollback()
        raise NotFoundError("brief draft not found") from err
    return BriefOut(**brief_service.get_brief(session, project_id))


@router.post("/confirm", response_model=ConfirmOut)
def confirm(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> ConfirmOut:
    _owned(session, workspace, project_id)
    brief_service.ensure_draft(session, workspace.id, project_id)
    session.commit()
    try:
        version = brief_service.confirm_brief(session, project_id)
        session.commit()
    except MissingFieldsError as err:
        session.rollback()
        raise RequirementError("required fields are missing", {"missing": err.missing}) from err
    except ServiceNotFound as err:
        session.rollback()
        raise NotFoundError("brief draft not found") from err
    import json

    # F013 D3: confirmed brief is proposal evidence; the pass is idempotent
    # per (workspace, brief version) and best-effort (never blocks the flow).
    from lessoncanvas.modules.teacher_memory.service import schedule_pass

    schedule_pass(session, workspace.id, "brief_confirm", version.id)
    return ConfirmOut(version=version.version, fields=json.loads(version.fields_json))

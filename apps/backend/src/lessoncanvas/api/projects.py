import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from lessoncanvas.api.deps import get_session, require_workspace
from lessoncanvas.api.errors import NotFoundError, QuotaExceededError, RequirementError
from lessoncanvas.models import Workspace
from lessoncanvas.modules.identity_workspace import service

router = APIRouter(prefix="/projects", tags=["projects"])

WorkspaceDep = Annotated[Workspace, Depends(require_workspace)]
SessionDep = Annotated[Session, Depends(get_session)]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    unit_hints: str | None = Field(default=None, max_length=200)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    unit_hints: str | None
    status: str
    created_at: datetime
    updated_at: datetime


def to_out(project) -> ProjectOut:
    return ProjectOut(
        id=project.id,
        name=project.name,
        unit_hints=project.unit_hints,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectOut)
def create_project(body: ProjectCreate, workspace: WorkspaceDep, session: SessionDep) -> ProjectOut:
    if not body.name.strip():
        raise RequirementError("name must not be blank")
    try:
        project = service.create_project(session, workspace, body.name.strip(), body.unit_hints)
        session.commit()
    except service.QuotaExceededError as err:
        session.rollback()
        raise QuotaExceededError("project limit reached", {"limit": "projects"}) from err
    return to_out(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(workspace: WorkspaceDep, session: SessionDep) -> list[ProjectOut]:
    projects = service.list_projects(session, workspace)
    return [to_out(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> ProjectOut:
    try:
        project = service.get_owned_project(session, workspace, project_id, allow_sample_read=True)
    except service.NotFoundError as err:
        raise NotFoundError("project not found") from err
    return to_out(project)


@router.delete("/{project_id}")
def delete_project(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> dict:
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.modules.identity_workspace.deletion import (
        DeletionFailedError,
        delete_project_cascade,
    )

    try:
        service.get_owned_project(session, workspace, project_id)
    except service.NotFoundError as err:
        raise NotFoundError("project not found") from err
    try:
        delete_project_cascade(session, StorageAdapter(), workspace.id, project_id)
        session.commit()
    except DeletionFailedError:
        session.commit()
        return {"deleted": False, "status": "deleting"}
    return {"deleted": True, "status": "deleted"}

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lessoncanvas.models import AuditEvent, Project, Workspace
from lessoncanvas.settings import get_settings


class QuotaExceededError(Exception):
    pass


class NotFoundError(Exception):
    pass


def resolve_workspace(session: Session, clerk_user_id: str) -> Workspace:
    workspace = session.scalar(select(Workspace).where(Workspace.clerk_user_id == clerk_user_id))
    if workspace is None:
        workspace = Workspace(clerk_user_id=clerk_user_id)
        session.add(workspace)
        session.flush()
    return workspace


def _active_project_count(session: Session, workspace_id: uuid.UUID) -> int:
    return (
        session.scalar(
            select(func.count(Project.id)).where(
                Project.workspace_id == workspace_id, Project.status == "active"
            )
        )
        or 0
    )


def create_project(
    session: Session, workspace: Workspace, name: str, unit_hints: str | None
) -> Project:
    settings = get_settings()
    if _active_project_count(session, workspace.id) >= settings.max_projects_per_workspace:
        raise QuotaExceededError("project limit reached")
    project = Project(workspace_id=workspace.id, name=name, unit_hints=unit_hints)
    session.add(project)
    session.flush()
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor=workspace.clerk_user_id,
            action="project.create",
            target_type="project",
            target_id=str(project.id),
        )
    )
    return project


def list_projects(session: Session, workspace: Workspace) -> list[Project]:
    return list(
        session.scalars(
            select(Project)
            .where(Project.workspace_id == workspace.id, Project.status != "deleted")
            .order_by(Project.created_at.desc())
        )
    )


def get_owned_project(session: Session, workspace: Workspace, project_id: uuid.UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.workspace_id != workspace.id or project.status == "deleted":
        raise NotFoundError("project not found")
    return project


def delete_project(session: Session, workspace: Workspace, project_id: uuid.UUID) -> Project:
    project = get_owned_project(session, workspace, project_id)
    project.status = "deleted"
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor=workspace.clerk_user_id,
            action="project.delete",
            target_type="project",
            target_id=str(project.id),
        )
    )
    session.flush()
    return project

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.models import AuditEvent, Project, RetainedSecurityEvent, Workspace
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
        try:
            session.flush()
        except IntegrityError:
            # F011 D9 race safety: a concurrent first request won the unique
            # clerk_user_id insert; adopt its row instead of failing.
            session.rollback()
            workspace = session.scalar(
                select(Workspace).where(Workspace.clerk_user_id == clerk_user_id)
            )
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
    # F011 D9 race safety: lock the workspace row so concurrent creates count
    # a stable set; exactly the cap succeeds, never an overshoot.
    session.execute(select(Workspace).where(Workspace.id == workspace.id).with_for_update())
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


def audit_download(
    session: Session,
    workspace_id: uuid.UUID,
    actor: str,
    kind: str,
    target_id: uuid.UUID,
) -> None:
    """F011 D7: every private-object download is auditable by its owner and
    mirrored into the content-free retained ledger (D4(b) scope)."""
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor=actor,
            action=f"download.{kind}",
            target_type=kind,
            target_id=str(target_id),
        )
    )
    session.add(
        RetainedSecurityEvent(workspace_id=workspace_id, action=f"download.{kind}")
    )


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

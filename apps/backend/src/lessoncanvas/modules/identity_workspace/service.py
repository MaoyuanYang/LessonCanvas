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


def resolve_workspace(session: Session, subject: str) -> Workspace:
    workspace = session.scalar(select(Workspace).where(Workspace.subject == subject))
    if workspace is None:
        workspace = Workspace(subject=subject)
        session.add(workspace)
        try:
            session.flush()
        except IntegrityError:
            # F011 D9 race safety: a concurrent first request won the unique
            # subject insert; adopt its row instead of failing.
            session.rollback()
            workspace = session.scalar(
                select(Workspace).where(Workspace.subject == subject)
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
            actor=workspace.subject,
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


def get_owned_project(
    session: Session,
    workspace: Workspace,
    project_id: uuid.UUID,
    *,
    allow_sample_read: bool = False,
) -> Project:
    """Resolve a project the caller may access. F012: safe read endpoints pass
    allow_sample_read=True so the designated synthetic sample project is
    inspectable by any authenticated workspace; every write path keeps strict
    ownership and calls this without the flag."""
    project = session.get(Project, project_id)
    if project is None or project.status == "deleted":
        raise NotFoundError("project not found")
    if project.workspace_id == workspace.id:
        return project
    if allow_sample_read:
        owner = session.get(Workspace, project.workspace_id)
        if owner is not None and owner.subject == get_settings().demo_owner_subject:
            return project
    raise NotFoundError("project not found")


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
            actor=workspace.subject,
            action="project.delete",
            target_type="project",
            target_id=str(project.id),
        )
    )
    session.flush()
    return project

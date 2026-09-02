import uuid
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.sse_registry import active_stream_count
from lessoncanvas.models import (
    AccountDeletionEvent,
    DiscoveryRun,
    Project,
    QuotaCounter,
    Workspace,
)
from lessoncanvas.models import AuditEvent as AccountAuditEvent
from lessoncanvas.modules.identity_workspace.deletion import (
    DeletionFailedError,
    delete_workspace_cascade,
    record_account_deletion,
)
from lessoncanvas.modules.identity_workspace.limits import (
    EXPENSIVE_CLASS,
    GENERAL_CLASS,
    UPLOAD_DAILY_CLASS,
    read_window,
)
from lessoncanvas.modules.run_orchestration.service import count_active_generation_runs
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/account", tags=["account"])

DAY_SECONDS = 24 * 3600


@router.get("/audit")
def audit_events(
    workspace: WorkspaceDep,
    session: SessionDep,
    limit: int = 50,
    before: datetime | None = None,
) -> dict:
    """F011 D7: owner-inspectable sensitive-action audit list (kind + target +
    time only, never payloads), newest first, bounded with a `before` cursor."""
    limit = max(1, min(limit, 200))
    query = (
        select(AccountAuditEvent)
        .where(AccountAuditEvent.workspace_id == workspace.id)
        .order_by(AccountAuditEvent.created_at.desc(), AccountAuditEvent.id.desc())
    )
    if before is not None:
        query = query.where(AccountAuditEvent.created_at < before)
    rows = session.scalars(query.limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "events": [
            {
                "action": event.action,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "created_at": event.created_at.isoformat(),
            }
            for event in rows
        ],
        "next_before": rows[-1].created_at.isoformat() if has_more and rows else None,
    }


@router.get("/usage")
def usage(workspace: WorkspaceDep, session: SessionDep) -> dict:
    """Every authoritative F011 D2 limit with current consumption (Spec AC-011)."""
    settings = get_settings()
    general = read_window(session, workspace.id, GENERAL_CLASS, settings.rate_window_seconds)
    expensive = read_window(session, workspace.id, EXPENSIVE_CLASS, settings.rate_window_seconds)
    upload = read_window(session, workspace.id, UPLOAD_DAILY_CLASS, DAY_SECONDS)
    active_projects = (
        session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.workspace_id == workspace.id, Project.status == "active")
        ).scalar_one()
    )
    planning_runs = (
        session.execute(
            select(func.count())
            .select_from(DiscoveryRun)
            .where(DiscoveryRun.workspace_id == workspace.id, DiscoveryRun.kind == "planning")
        ).scalar_one()
    )
    narration = session.scalars(
        select(QuotaCounter).where(
            QuotaCounter.workspace_id == workspace.id,
            QuotaCounter.key == "evidence_narration",
        )
    ).first()
    return {
        "request_rate": {
            "limit": settings.rate_general_per_window,
            "window_seconds": settings.rate_window_seconds,
            **general,
        },
        "expensive_rate": {
            "limit": settings.rate_expensive_per_window,
            "window_seconds": settings.rate_window_seconds,
            **expensive,
        },
        "concurrent_generation_runs": {
            "limit": settings.max_concurrent_generation_runs_per_workspace,
            "active": count_active_generation_runs(session, workspace.id),
        },
        "concurrent_sse_streams": {
            "limit": settings.max_concurrent_sse_streams_per_workspace,
            "active": active_stream_count(workspace.id),
        },
        "upload_daily_bytes": {
            "limit": settings.upload_daily_bytes_per_workspace,
            "window_seconds": DAY_SECONDS,
            "used": upload["used_bytes"],
            "reset_at": upload["reset_at"],
        },
        "projects": {"limit": settings.max_projects_per_workspace, "used": active_projects},
        "planning_runs": {
            "limit": settings.max_planning_runs_per_workspace,
            "used": planning_runs,
        },
        "evidence_narration": {
            "limit": settings.evidence_narration_quota_per_workspace,
            "used": narration.used if narration else 0,
        },
    }


@router.get("/deletion-status")
def deletion_status(workspace: WorkspaceDep, session: SessionDep) -> list[dict]:
    events = session.scalars(
        select(AccountDeletionEvent)
        .where(AccountDeletionEvent.subject == workspace.subject)
        .order_by(AccountDeletionEvent.created_at.desc())
    ).all()
    return [
        {"status": event.status, "detail": event.detail, "created_at": event.created_at.isoformat()}
        for event in events
    ]


@router.delete("")
def delete_account(workspace: WorkspaceDep, session: SessionDep) -> dict:
    """ADR-0006: deletion ends after the application-side purge; there is no
    external identity-provider step anymore."""
    workspace_id: uuid.UUID = workspace.id
    subject = workspace.subject
    try:
        delete_workspace_cascade(session, StorageAdapter(), workspace)
    except DeletionFailedError as error:
        session.rollback()
        fresh = session.get(Workspace, workspace_id)
        record_account_deletion(session, subject, "purge_failed", str(error))
        session.commit()
        _ = fresh
        return {"purged": False}

    record_account_deletion(session, subject, "purged", None)
    session.commit()
    return {"purged": True}

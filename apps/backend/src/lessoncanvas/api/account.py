import uuid

from fastapi import APIRouter
from sqlalchemy import select

from lessoncanvas.adapters.clerk_admin import ClerkAdminError, get_clerk_admin
from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.models import AccountDeletionEvent, Workspace
from lessoncanvas.modules.identity_workspace.deletion import (
    DeletionFailedError,
    delete_workspace_cascade,
    record_account_deletion,
)

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/deletion-status")
def deletion_status(workspace: WorkspaceDep, session: SessionDep) -> list[dict]:
    events = session.scalars(
        select(AccountDeletionEvent)
        .where(AccountDeletionEvent.clerk_user_id == workspace.clerk_user_id)
        .order_by(AccountDeletionEvent.created_at.desc())
    ).all()
    return [
        {"status": event.status, "detail": event.detail, "created_at": event.created_at.isoformat()}
        for event in events
    ]


@router.delete("")
def delete_account(workspace: WorkspaceDep, session: SessionDep) -> dict:
    workspace_id: uuid.UUID = workspace.id
    clerk_user_id = workspace.clerk_user_id
    try:
        delete_workspace_cascade(session, StorageAdapter(), workspace)
    except DeletionFailedError as error:
        session.rollback()
        fresh = session.get(Workspace, workspace_id)
        record_account_deletion(session, clerk_user_id, "purge_failed", str(error))
        session.commit()
        _ = fresh
        return {"purged": False, "clerk_deleted": False}

    record_account_deletion(session, clerk_user_id, "purged", None)
    session.commit()

    try:
        get_clerk_admin().delete_user(clerk_user_id)
        record_account_deletion(session, clerk_user_id, "clerk_deleted", None)
        session.commit()
        return {"purged": True, "clerk_deleted": True}
    except ClerkAdminError as error:
        record_account_deletion(session, clerk_user_id, "clerk_failed", str(error))
        session.commit()
        return {"purged": True, "clerk_deleted": False}

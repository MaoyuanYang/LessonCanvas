from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from lessoncanvas.adapters.auth import get_token_verifier
from lessoncanvas.api.errors import AuthRequiredError, QuotaExceededError
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Workspace
from lessoncanvas.modules.identity_workspace.limits import (
    EXPENSIVE_CLASS,
    GENERAL_CLASS,
    consume_rate,
)
from lessoncanvas.modules.identity_workspace.service import resolve_workspace
from lessoncanvas.settings import get_settings


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def require_workspace(request: Request, session: SessionDep) -> Workspace:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthRequiredError("authentication required")
    subject = get_token_verifier().verify(token.strip())
    if subject is None:
        raise AuthRequiredError("authentication required")
    workspace = resolve_workspace(session, subject.clerk_user_id)
    session.commit()
    return workspace


WorkspaceDep = Annotated[Workspace, Depends(require_workspace)]


def require_general_rate(workspace: WorkspaceDep, session: SessionDep) -> None:
    """F011 D2 general request-rate guard; applies to every authenticated route."""
    settings = get_settings()
    allowed, details = consume_rate(
        session,
        workspace.id,
        GENERAL_CLASS,
        settings.rate_general_per_window,
        settings.rate_window_seconds,
    )
    session.commit()
    if not allowed:
        raise QuotaExceededError("request rate limit reached", details)


def require_expensive_rate(workspace: WorkspaceDep, session: SessionDep) -> None:
    """F011 D2 expensive-write guard; run starts, uploads, and imports.

    Caps nest: an expensive request also consumes the general window (total
    request budget) and additionally the stricter expensive window, so an
    expensive-heavy caller is bounded by the smaller limit.
    """
    settings = get_settings()
    allowed, details = consume_rate(
        session,
        workspace.id,
        EXPENSIVE_CLASS,
        settings.rate_expensive_per_window,
        settings.rate_window_seconds,
    )
    session.commit()
    if not allowed:
        raise QuotaExceededError("expensive operation rate limit reached", details)

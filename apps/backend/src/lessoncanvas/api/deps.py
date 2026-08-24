from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from lessoncanvas.adapters.auth import get_token_verifier
from lessoncanvas.api.errors import AuthRequiredError
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Workspace
from lessoncanvas.modules.identity_workspace.service import resolve_workspace


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

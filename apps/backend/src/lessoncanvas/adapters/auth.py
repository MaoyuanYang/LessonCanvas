"""Workspace-subject tokens (ADR-0006).

Phase 1 has no login: `POST /auth/guest-token` mints an HS256 token with a
fresh random subject; the verifier below validates it. Every workspace,
ownership, quota, and audit decision keys on the subject string.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import jwt

from lessoncanvas.settings import get_settings


@dataclass(frozen=True)
class AuthenticatedSubject:
    subject: str


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedSubject | None: ...


class SubjectTokenVerifier:
    def verify(self, token: str) -> AuthenticatedSubject | None:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.auth_token_secret,
                algorithms=["HS256"],
                audience=settings.auth_token_audience,
            )
        except jwt.PyJWTError:
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        return AuthenticatedSubject(subject=subject)


@lru_cache
def get_token_verifier() -> TokenVerifier:
    return SubjectTokenVerifier()

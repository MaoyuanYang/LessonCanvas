from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import jwt

from lessoncanvas.settings import get_settings


@dataclass(frozen=True)
class AuthenticatedSubject:
    clerk_user_id: str


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedSubject | None: ...


class DevTokenVerifier:
    def verify(self, token: str) -> AuthenticatedSubject | None:
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.auth_dev_secret,
                algorithms=["HS256"],
                audience=settings.auth_dev_audience,
            )
        except jwt.PyJWTError:
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        return AuthenticatedSubject(clerk_user_id=subject)


class ClerkJwksVerifier:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = jwt.PyJWKClient(settings.clerk_jwks_url)
        self._issuer = settings.clerk_issuer
        self._audience = settings.clerk_audience

    def verify(self, token: str) -> AuthenticatedSubject | None:
        try:
            key = self._client.get_signing_key_from_jwt(token)
            decode_kwargs: dict = {
                "algorithms": ["RS256"],
                "issuer": self._issuer or None,
            }
            if self._audience:
                decode_kwargs["audience"] = self._audience
            payload = jwt.decode(token, key.key, **decode_kwargs)
        except Exception:
            return None
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        return AuthenticatedSubject(clerk_user_id=subject)


@lru_cache
def get_token_verifier() -> TokenVerifier:
    settings = get_settings()
    if settings.clerk_jwks_url:
        return ClerkJwksVerifier()
    return DevTokenVerifier()

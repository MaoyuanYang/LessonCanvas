"""ADR-0006 D11: anonymous guest workspace token issuance.

Unauthenticated by design: the caller has nothing yet. The endpoint mints a
fresh random subject, creates no rows, and discloses nothing. The workspace
appears only when the token is first used on an authorized route.
"""

import datetime
import uuid

import jwt
from fastapi import APIRouter

from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


def mint_guest_token() -> tuple[str, str]:
    settings = get_settings()
    subject = f"guest-{uuid.uuid4()}"
    now = datetime.datetime.now(datetime.UTC)
    token = jwt.encode(
        {
            "sub": subject,
            "aud": settings.auth_token_audience,
            "iat": now,
            "exp": now + datetime.timedelta(seconds=settings.guest_token_ttl_seconds),
        },
        settings.auth_token_secret,
        algorithm="HS256",
    )
    return token, subject


@router.post("/guest-token", status_code=201)
def guest_token() -> dict:
    token, subject = mint_guest_token()
    return {"token": token, "subject": subject}

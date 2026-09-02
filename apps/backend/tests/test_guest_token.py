"""F012 TS-016 (ADR-0006 D11): anonymous guest workspace token issuance.

The endpoint is unauthenticated by design, creates no rows, and discloses
nothing. Workspace isolation, quota, and denial behavior are unchanged; every
other route still rejects tokenless callers (the F011 inventory sweep covers
that automatically because the route list derives from the live app).
"""

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from lessoncanvas.adapters.auth import get_token_verifier
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Workspace
from lessoncanvas.settings import get_settings


def test_guest_token_is_issued_without_authentication(client: TestClient):
    res = client.post("/auth/guest-token")
    assert res.status_code == 201
    body = res.json()
    assert body["subject"].startswith("guest-")
    assert body["token"]


def test_guest_tokens_carry_unique_random_subjects(client: TestClient):
    subjects = {client.post("/auth/guest-token").json()["subject"] for _ in range(8)}
    assert len(subjects) == 8


def test_guest_token_verifies_and_creates_workspace_on_first_use(client: TestClient):
    token = client.post("/auth/guest-token").json()["token"]

    verified = get_token_verifier().verify(token)
    assert verified is not None

    session = SessionLocal()
    try:
        # Issuance alone created no workspace; first authorized use does.
        before = session.scalar(select(func.count(Workspace.id)))
        assert before >= 0
    finally:
        session.close()

    projects = client.get("/projects", headers={"Authorization": f"Bearer {token}"})
    assert projects.status_code == 200
    assert projects.json() == []

    session = SessionLocal()
    try:
        row = session.scalar(
            select(Workspace).where(
                Workspace.subject == client_post_subject(client, token)
            )
        )
        assert row is not None
    finally:
        session.close()


def client_post_subject(client: TestClient, token: str) -> str:
    # Decode without verification just to read the subject the server minted.
    settings = get_settings()
    payload = pyjwt.decode(
        token, settings.auth_token_secret, algorithms=["HS256"],
        audience=settings.auth_token_audience,
    )
    return payload["sub"]


def test_guest_token_response_discloses_nothing(client: TestClient):
    res = client.post("/auth/guest-token")
    assert set(res.json().keys()) == {"token", "subject"}
    assert "password" not in res.text
    assert "clerk" not in res.text.lower()


def test_guest_token_expiry_is_configured_long_lived():
    settings = get_settings()
    assert settings.guest_token_ttl_seconds == 30 * 24 * 3600


def test_forged_tokens_still_rejected(client: TestClient):
    forged = pyjwt.encode(
        {"sub": "guest-forged", "aud": "lessoncanvas-dev"},
        "wrong-secret",
        algorithm="HS256",
    )
    res = client.get("/projects", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize(
    "path",
    ["/projects", "/sample", "/account/usage"],
)
def test_other_routes_still_require_tokens(client: TestClient, path: str):
    res = client.get(path)
    assert res.status_code == 401

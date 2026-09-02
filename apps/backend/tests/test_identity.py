from sqlalchemy import func, select

from conftest import make_token
from lessoncanvas.models import Workspace


def test_workspace_created_once_for_verified_session(client, db_session):
    token = make_token("teacher_once")
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(3):
        response = client.get("/projects", headers=headers)
        assert response.status_code == 200
    count = db_session.scalar(
        select(func.count(Workspace.id)).where(Workspace.subject == "teacher_once")
    )
    assert count == 1


def test_missing_token_rejected(client):
    response = client.get("/projects")
    assert response.status_code == 401
    body = response.json()["error"]
    assert body["code"] == "AUTH_REQUIRED"
    assert body["correlation_id"]


def test_forged_token_rejected(client):
    response = client.get("/projects", headers={"Authorization": "Bearer forged.token.value"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_expired_token_rejected(client):
    import datetime

    import jwt as pyjwt

    from lessoncanvas.settings import get_settings

    settings = get_settings()
    payload = {
        "sub": "teacher_expired",
        "aud": settings.auth_token_audience,
        "exp": datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
    }
    token = pyjwt.encode(payload, settings.auth_token_secret, algorithm="HS256")
    response = client.get("/projects", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

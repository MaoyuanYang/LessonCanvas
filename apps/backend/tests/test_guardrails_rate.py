import time

import pytest

from lessoncanvas.settings import get_settings


@pytest.fixture()
def low_limits(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_general_per_window", 4)
    monkeypatch.setattr(settings, "rate_expensive_per_window", 2)
    monkeypatch.setattr(settings, "rate_window_seconds", 60)


def create_project(client, headers) -> str:
    response = client.post("/projects", json={"name": "限流测试项目"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def upload(client, headers, project_id, name="notes.txt", data=b"material"):
    return client.post(
        f"/projects/{project_id}/sources",
        files={"file": (name, data, "application/octet-stream")},
        data={"rights_acknowledged": "true"},
        headers=headers,
    )


def test_usage_reports_every_limit_and_current_window(client, auth, low_limits):
    response = client.get("/account/usage", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "request_rate",
        "expensive_rate",
        "concurrent_generation_runs",
        "concurrent_sse_streams",
        "upload_daily_bytes",
        "projects",
        "planning_runs",
        "evidence_narration",
    }
    assert body["request_rate"]["limit"] == 4
    assert body["request_rate"]["used"] >= 1  # this very request
    assert 1 <= body["request_rate"]["retry_after_seconds"] <= 60
    assert body["expensive_rate"]["limit"] == 2
    assert body["concurrent_generation_runs"] == {"limit": 2, "active": 0}
    assert body["concurrent_sse_streams"] == {"limit": 6, "active": 0}
    assert body["projects"] == {"limit": 5, "used": 0}
    assert body["upload_daily_bytes"]["limit"] == 200 * 1024 * 1024


def test_general_window_rejects_beyond_limit_without_cross_workspace_effect(
    client, auth, teacher_b_token, low_limits
):
    for _ in range(4):
        assert client.get("/projects", headers=auth).status_code == 200
    rejected = client.get("/projects", headers=auth)
    assert rejected.status_code == 429
    error = rejected.json()["error"]
    assert error["code"] == "QUOTA_EXCEEDED"
    assert error["details"]["limit"] == "general"
    assert error["details"]["limit_value"] == 4
    assert 1 <= error["details"]["retry_after_seconds"] <= 60

    # Saturated requests keep counting: an immediate retry stays rejected.
    assert client.get("/projects", headers=auth).status_code == 429

    # The window is per workspace: another teacher is unaffected.
    other = {"Authorization": f"Bearer {teacher_b_token}"}
    assert client.get("/projects", headers=other).status_code == 200


def test_window_reset_recovers_deterministically(client, auth, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_general_per_window", 1)
    monkeypatch.setattr(settings, "rate_window_seconds", 1)

    assert client.get("/projects", headers=auth).status_code == 200
    assert client.get("/projects", headers=auth).status_code == 429
    time.sleep(1.2)
    assert client.get("/projects", headers=auth).status_code == 200


def test_expensive_class_rejects_before_any_persisted_work(client, auth, low_limits):
    from sqlalchemy import select

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import Source

    project_id = create_project(client, auth)
    assert upload(client, auth, project_id, "a.txt").status_code == 201
    assert upload(client, auth, project_id, "b.txt").status_code == 201

    rejected = upload(client, auth, project_id, "c.txt")
    assert rejected.status_code == 429
    details = rejected.json()["error"]["details"]
    assert details["limit"] == "expensive"
    assert details["limit_value"] == 2

    session = SessionLocal()
    stored = session.scalars(select(Source).where(Source.project_id == project_id)).all()
    session.close()
    assert [source.filename for source in stored] == ["a.txt", "b.txt"]


def test_expensive_requests_also_count_against_the_general_window(client, auth, monkeypatch):
    """Nested caps: expensive writes count in both windows (total + subset)."""
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_general_per_window", 1)
    monkeypatch.setattr(settings, "rate_expensive_per_window", 50)

    project_id = create_project(client, auth)  # consumes the single general slot
    assert client.get("/projects", headers=auth).status_code == 429
    rejected = upload(client, auth, project_id, "a.txt")
    assert rejected.status_code == 429
    assert rejected.json()["error"]["details"]["limit"] == "general"

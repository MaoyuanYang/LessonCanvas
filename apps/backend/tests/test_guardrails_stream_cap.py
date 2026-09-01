"""F011 TS-003: per-workspace concurrent SSE stream cap.

The ASGI TestClient buffers whole responses, so a non-terminating stream
cannot be held open here. The cap is therefore verified by occupying the
registry slots directly (the same acquire the endpoints use), asserting the
real API rejection while saturated, and asserting release on a terminating
stream.
"""

import uuid

from lessoncanvas.api.sse_registry import acquire_stream_slot, release_stream_slot
from lessoncanvas.models import Project
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.settings import get_settings
from test_generation import confirmed_blueprint_project


def test_stream_cap_rejects_when_saturated_and_releases_on_completion(
    client, auth, db_session
):
    project_id = confirmed_blueprint_project(client, auth)
    workspace_id = db_session.get(Project, uuid.UUID(project_id)).workspace_id
    run, created = run_service.start_generation(db_session, workspace_id, uuid.UUID(project_id))
    db_session.commit()
    assert created is True

    settings = get_settings()
    limit = settings.max_concurrent_sse_streams_per_workspace
    stream_url = f"/projects/{project_id}/generation/events"

    # Saturate the workspace's stream slots exactly as six open streams would.
    for _ in range(limit):
        acquire_stream_slot(workspace_id, limit)

    rejected = client.get(stream_url, headers=auth)
    assert rejected.status_code == 429
    details = rejected.json()["error"]["details"]
    assert details["limit"] == "concurrent_sse_streams"
    assert details["limit_value"] == limit

    usage = client.get("/account/usage", headers=auth).json()
    assert usage["concurrent_sse_streams"] == {"limit": limit, "active": limit}

    for _ in range(limit):
        release_stream_slot(workspace_id)

    # A terminating stream (settled run: replay then `end`) is admitted, fully
    # consumable, and releases its slot on completion.
    run.status = "complete"
    db_session.commit()
    response = client.get(stream_url, headers=auth)
    assert response.status_code == 200
    assert "event: end" in response.text

    usage = client.get("/account/usage", headers=auth).json()
    assert usage["concurrent_sse_streams"]["active"] == 0


def test_stream_slots_isolated_per_workspace():
    from conftest import make_token  # noqa: F401  (workspace isolation uses ids, not tokens)

    first = uuid.uuid4()
    second = uuid.uuid4()
    acquire_stream_slot(first, 1)
    acquire_stream_slot(second, 1)  # a different workspace is unaffected
    try:
        acquire_stream_slot(first, 1)  # same workspace: now saturated
        raise AssertionError("expected QuotaExceededError")
    except Exception as error:
        assert getattr(error, "code", None) == "QUOTA_EXCEEDED"
    finally:
        release_stream_slot(first)
        release_stream_slot(second)

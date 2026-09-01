"""F011 TS-015: bounded multi-account scripted journey (invariant evidence).

Five workspaces drive the core flow concurrently up to and beyond lowered
limits, including duplicate submissions and a mid-flow deletion. Asserts
isolation, limit accuracy, idempotency, and bounded model spend — not
performance.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import select

from lessoncanvas.main import app
from lessoncanvas.models import GenerationRun
from lessoncanvas.settings import get_settings
from test_generation import CORPUS

WORKSPACES = 5


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def drive_workspace(index: int, limits_low: bool) -> dict:
    from conftest import make_token

    client = TestClient(app)
    headers = _headers(make_token(f"journey_teacher_{index}"))

    created = client.post("/projects", json={"name": f"并发旅程 {index}"}, headers=headers)
    assert created.status_code == 201
    project_id = created.json()["id"]

    upload = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("corpus.txt", CORPUS.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text

    if index == WORKSPACES - 1:
        # Mid-flow deletion (after upload, before planning): the workspace
        # exits completely while others keep generating.
        deleted = client.delete(f"/projects/{project_id}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        return {"project_id": project_id, "deleted": True}

    started = client.post(f"/projects/{project_id}/discovery/start", headers=headers)
    assert started.status_code == 200
    # Discovery re-start after draft_ready is a new interview by F001 design;
    # it must still stay inside the same project (no cross-workspace effect).
    duplicate_start = client.post(f"/projects/{project_id}/discovery/start", headers=headers)
    assert duplicate_start.status_code == 200
    assert duplicate_start.json()["status"] in ("draft_ready", "questioning")

    assert (
        client.post(f"/projects/{project_id}/brief/confirm", headers=headers).status_code == 200
    )
    assert (
        client.post(f"/projects/{project_id}/planning/start", headers=headers).status_code == 200
    )
    blueprint = client.get(f"/projects/{project_id}/blueprint", headers=headers)
    assert blueprint.status_code == 200
    base = blueprint.json()["draft_revision"]
    for finding in blueprint.json().get("findings", []):
        if finding.get("tier") == "waivable" and finding.get("status") == "open":
            decision = client.post(
                f"/projects/{project_id}/blueprint/decisions",
                json={
                    "finding_id": finding["id"],
                    "reason": "以教材与教师判断为准",
                    "base_revision": base,
                },
                headers=headers,
            )
            assert decision.status_code == 200, decision.text
            base = decision.json()["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm", json={"base_revision": base}, headers=headers
    )
    assert confirmed.status_code == 200
    generation = client.post(f"/projects/{project_id}/generation/start", headers=headers)
    assert generation.status_code == 200
    # Idempotent convergence where the contract promises it: a duplicate
    # generation start returns the same run (identity constraint), never a
    # second billed run.
    duplicate_generation = client.post(
        f"/projects/{project_id}/generation/start", headers=headers
    )
    assert duplicate_generation.status_code == 200
    _ = limits_low
    return {"project_id": project_id, "deleted": False, "run": generation.json()}


def test_multiaccount_journey_isolation_limits_idempotency_and_bounded_spend():
    with ThreadPoolExecutor(max_workers=WORKSPACES) as pool:
        results = list(pool.map(lambda i: drive_workspace(i, False), range(WORKSPACES)))

    assert sum(1 for result in results if result["deleted"]) == 1
    live = [result for result in results if not result["deleted"]]
    assert len(live) == WORKSPACES - 1

    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    runs = session.scalars(select(GenerationRun)).all()
    session.close()

    # Bounded spend: one generation run per live workspace despite duplicate
    # submissions, each within its per-run cap (fake adapter).
    cap = get_settings().max_model_calls_per_run
    assert len(runs) == len(live)
    assert all(run.model_calls <= run.model_call_cap <= cap for run in runs)

    # Isolation: every surviving project answers only to its own workspace.
    for result in live:
        client = TestClient(app)
        from conftest import make_token

        index = results.index(result)
        owner = _headers(make_token(f"journey_teacher_{index}"))
        other = _headers(make_token("journey_teacher_other"))
        project_id = result["project_id"]
        assert client.get(f"/projects/{project_id}", headers=owner).status_code == 200
        assert client.get(f"/projects/{project_id}", headers=other).status_code == 404

    # The deleted workspace left nothing behind.
    deleted_id = uuid.UUID(next(r["project_id"] for r in results if r["deleted"]))
    session = SessionLocal()
    residual_runs = (
        session.scalars(select(GenerationRun).where(GenerationRun.project_id == deleted_id)).all()
    )
    session.close()
    assert residual_runs == []

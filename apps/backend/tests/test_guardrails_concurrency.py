"""F011 TS-004/TS-013: concurrent-run admission and count-quota race safety."""

import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from lessoncanvas.main import app
from lessoncanvas.models import GenerationRun, Project
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.settings import get_settings
from test_generation import confirmed_blueprint_project


def _start_active_run(db_session, project_id: str):
    workspace_id = db_session.get(Project, uuid.UUID(project_id)).workspace_id
    run, _ = run_service.start_generation(db_session, workspace_id, uuid.UUID(project_id))
    db_session.commit()
    return run


def test_third_family_run_rejected_with_active_pointer_then_recovers(client, auth, db_session):
    cap = get_settings().max_concurrent_generation_runs_per_workspace
    assert cap == 2

    p1 = confirmed_blueprint_project(client, auth)
    p2 = confirmed_blueprint_project(client, auth)
    p3 = confirmed_blueprint_project(client, auth)
    run1 = _start_active_run(db_session, p1)
    run2 = _start_active_run(db_session, p2)
    assert run1.status == "queued" and run2.status == "queued"

    rejected = client.post(f"/projects/{p3}/generation/start", headers=auth)
    assert rejected.status_code == 409
    error = rejected.json()["error"]
    assert error["code"] == "RUN_ADMISSION"
    assert sorted(error["details"]["active_run_ids"]) == sorted(
        [str(run1.id), str(run2.id)]
    )
    assert error["details"]["limit"] == cap

    # A duplicate for an already-running family converges on the existing run
    # even while the workspace is saturated (no admission consumed).
    duplicate = client.post(f"/projects/{p1}/generation/start", headers=auth)
    assert duplicate.status_code == 200

    # Settling one run frees its slot; the blocked start now succeeds.
    run2.status = "complete"
    db_session.commit()
    recovered = client.post(f"/projects/{p3}/generation/start", headers=auth)
    assert recovered.status_code == 200

    # The recovered run dispatched eagerly and settled (tasks_eager in tests);
    # only the still-queued first run keeps its slot. The freed slot is exactly
    # what admission guarantees.
    usage = client.get("/account/usage", headers=auth).json()
    assert usage["concurrent_generation_runs"]["active"] == 1


def test_concurrent_duplicate_starts_converge_on_one_run(client, auth, db_session):
    project_id = uuid.UUID(confirmed_blueprint_project(client, auth))
    workspace_id = db_session.get(Project, project_id).workspace_id

    def attempt(_):
        from lessoncanvas.db import SessionLocal

        session = SessionLocal()
        try:
            run, created = run_service.start_generation(session, workspace_id, project_id)
            session.commit()
            return str(run.id), created
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))

    run_ids = {run_id for run_id, _ in results}
    created_count = sum(1 for _, created in results if created)
    assert len(run_ids) == 1
    assert created_count == 1


def test_concurrent_project_creates_succeed_exactly_at_cap(client, auth):
    def attempt(_):
        thread_client = TestClient(app)
        response = thread_client.post(
            "/projects", json={"name": "并发项目"}, headers=auth
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(attempt, range(12)))

    cap = get_settings().max_projects_per_workspace
    assert statuses.count(201) == cap
    assert statuses.count(429) == 12 - cap


def test_concurrent_source_uploads_succeed_exactly_at_cap(client, auth):
    project_id = client.post("/projects", json={"name": "并发来源"}, headers=auth).json()["id"]

    def attempt(index):
        thread_client = TestClient(app)
        response = thread_client.post(
            f"/projects/{project_id}/sources",
            files={"file": (f"n{index}.txt", f"material {index}".encode(), "text/plain")},
            data={"rights_acknowledged": "true"},
            headers=auth,
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=15) as pool:
        statuses = list(pool.map(attempt, range(15)))

    from lessoncanvas.modules.sources_grounding.policy import MAX_SOURCES_PER_PROJECT

    assert statuses.count(201) == MAX_SOURCES_PER_PROJECT
    assert statuses.count(422) == 15 - MAX_SOURCES_PER_PROJECT
    _ = GenerationRun  # noqa: F401 (model import kept for symmetry/debugging)

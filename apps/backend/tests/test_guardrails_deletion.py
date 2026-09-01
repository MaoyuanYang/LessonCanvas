"""F011 TS-009/TS-011: deletion completeness, checkpoint cleanup, visible
partial states with repair, and the content-free retained ledger (D4(b)).

LangGraph checkpoint tables are created lazily by PostgresSaver; the test
stack runs the memory backend, so these tests create the tables with the
thread_id column the cascade and verification depend on (TQ-004 surrogate).
"""

from sqlalchemy import select, text

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import AuditEvent, RetainedSecurityEvent, Workspace
from test_generation import confirmed_blueprint_project


def create_project(client, headers, name="删除完整性项目") -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def upload(client, headers, project_id, name="notes.txt"):
    response = client.post(
        f"/projects/{project_id}/sources",
        files={"file": (name, b"teaching material", "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def ensure_checkpoint_tables():
    session = SessionLocal()
    try:
        for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
            session.execute(
                text(f"CREATE TABLE IF NOT EXISTS {table} (thread_id VARCHAR(150))")
            )
            session.execute(text(f"DELETE FROM {table}"))
        session.commit()
    finally:
        session.close()


def checkpoint_count(thread_id: str) -> int:
    session = SessionLocal()
    try:
        return session.execute(
            text("SELECT count(*) FROM checkpoints WHERE thread_id = :t"), {"t": thread_id}
        ).scalar()
    finally:
        session.close()


def workspace_id_of(subject: str):
    session = SessionLocal()
    try:
        return session.scalars(
            select(Workspace).where(Workspace.clerk_user_id == subject)
        ).one().id
    finally:
        session.close()


def flaky_storage_delete(monkeypatch, state):
    from lessoncanvas.adapters.storage import StorageAdapter

    original_delete = StorageAdapter.delete

    def _delete(self, key):
        if state["fail"]:
            raise RuntimeError("object store unavailable")
        original_delete(self, key)

    monkeypatch.setattr(StorageAdapter, "delete", _delete)


def test_project_deletion_removes_checkpoint_rows_and_verifies_clean(client, auth):
    ensure_checkpoint_tables()
    project_id = confirmed_blueprint_project(client, auth)
    session = SessionLocal()
    runs = session.execute(
        text("SELECT id FROM discovery_runs WHERE project_id = :p"),
        {"p": project_id},
    ).scalars().all()
    assert runs, "fixture must produce discovery runs"
    for run_id in runs:
        session.execute(
            text("INSERT INTO checkpoints (thread_id) VALUES (:t)"), {"t": str(run_id)}
        )
    session.commit()
    session.close()

    deleted = client.delete(f"/projects/{project_id}", headers=auth)
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "status": "deleted"}

    for run_id in runs:
        assert checkpoint_count(str(run_id)) == 0

    # Retained ledger row exists and the model exposes no content column at all
    # (action, workspace id, time only — the D4(b) boundary).
    workspace_id = workspace_id_of("teacher_a")
    session = SessionLocal()
    ledger = session.scalars(select(RetainedSecurityEvent)).all()
    session.close()
    assert any(
        event.action == "project.deleted" and event.workspace_id == workspace_id
        for event in ledger
    )
    allowed_columns = {"id", "workspace_id", "action", "occurred_at"}
    assert set(RetainedSecurityEvent.__table__.columns.keys()) == allowed_columns


def test_project_deletion_partial_visible_then_repairs(client, auth, monkeypatch):
    project_id = create_project(client, auth)
    upload(client, auth, project_id)

    state = {"fail": True}
    flaky_storage_delete(monkeypatch, state)

    failed = client.delete(f"/projects/{project_id}", headers=auth)
    assert failed.status_code == 200
    assert failed.json() == {"deleted": False, "status": "deleting"}

    listed = client.get("/projects", headers=auth).json()
    target = [p for p in listed if p["id"] == project_id]
    assert target and target[0]["status"] == "deleting"

    session = SessionLocal()
    audits = session.scalars(select(AuditEvent)).all()
    session.close()
    assert any(a.action == "project.deletion_failed" for a in audits)

    state["fail"] = False
    retried = client.delete(f"/projects/{project_id}", headers=auth)
    assert retried.status_code == 200
    assert retried.json() == {"deleted": True, "status": "deleted"}
    assert client.get(f"/projects/{project_id}", headers=auth).status_code == 404


def test_source_delete_object_failure_visible_then_repairs(client, auth, monkeypatch):
    project_id = create_project(client, auth)
    source = upload(client, auth, project_id, "keep.txt")

    state = {"fail": True}
    flaky_storage_delete(monkeypatch, state)

    partial = client.delete(f"/projects/{project_id}/sources/{source['id']}", headers=auth)
    assert partial.status_code == 200
    assert partial.json() == {"deleted": False, "status": "delete_failed"}

    listed = client.get(f"/projects/{project_id}/sources", headers=auth).json()
    assert [s["status"] for s in listed] == ["delete_failed"]

    state["fail"] = False
    repaired = client.delete(f"/projects/{project_id}/sources/{source['id']}", headers=auth)
    assert repaired.status_code == 204
    assert client.get(f"/projects/{project_id}/sources", headers=auth).json() == []


def test_account_purge_keeps_only_content_free_ledger(client, auth, monkeypatch):
    import lessoncanvas.api.account as account_api
    from lessoncanvas.adapters.clerk_admin import ClerkAdminError

    project_id = create_project(client, auth)
    upload(client, auth, project_id)

    class FailingClerk:
        def delete_user(self, user_id):
            raise ClerkAdminError("clerk unavailable")

    monkeypatch.setattr(account_api, "get_clerk_admin", lambda: FailingClerk())

    response = client.delete("/account", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["purged"] is True and body["clerk_deleted"] is False

    session = SessionLocal()
    ledger = session.scalars(select(RetainedSecurityEvent)).all()
    audits = session.scalars(select(AuditEvent)).all()
    session.close()
    assert [event.action for event in ledger] == ["project.deleted", "workspace.purged"]
    assert audits == []

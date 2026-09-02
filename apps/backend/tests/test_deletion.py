import uuid

from sqlalchemy import func, select

FULL_CORPUS = "\n".join(
    [
        "单元主题：环境保护与可持续发展",
        "课时数：6",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
    ]
)


def build_full_project(client, auth) -> tuple[str, dict]:
    project_id = client.post("/projects", json={"name": "删除测试"}, headers=auth).json()["id"]
    source = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", FULL_CORPUS.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    ).json()
    client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    client.post(f"/projects/{project_id}/brief/confirm", headers=auth)
    return project_id, source


def test_project_deletion_cascades_and_audits(client, auth):
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import (
        AuditEvent,
        BriefVersion,
        DiscoveryRun,
        Project,
        Source,
        SourceChunk,
    )

    project_id, source = build_full_project(client, auth)
    storage = StorageAdapter()
    object_key = source["object_key"] if "object_key" in source else None

    session = SessionLocal()
    source_row = session.get(Source, uuid.UUID(source["id"]))
    object_key = source_row.object_key
    session.close()
    assert storage.get(object_key)

    deleted = client.delete(f"/projects/{project_id}", headers=auth)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    session = SessionLocal()
    counts = {
        "project": session.scalar(select(func.count(Project.id)).where(Project.id == project_id)),
        "source": session.scalar(
            select(func.count(Source.id)).where(Source.project_id == project_id)
        ),
        "chunk": session.scalar(
            select(func.count(SourceChunk.id)).where(SourceChunk.source_id == source["id"])
        ),
        "run": session.scalar(
            select(func.count(DiscoveryRun.id)).where(DiscoveryRun.project_id == project_id)
        ),
        "version": session.scalar(
            select(func.count(BriefVersion.id)).where(BriefVersion.project_id == project_id)
        ),
    }
    audit = session.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.action == "project.deleted", AuditEvent.target_id == str(project_id)
        )
    )
    session.close()
    assert counts == {"project": 0, "source": 0, "chunk": 0, "run": 0, "version": 0}
    assert audit == 1

    try:
        storage.get(object_key)
        object_gone = False
    except Exception:
        object_gone = True
    assert object_gone


def test_project_deletion_failure_is_retryable(client, auth, monkeypatch):
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import Project

    project_id, _ = build_full_project(client, auth)

    def broken_delete(self, key):
        raise RuntimeError("minio down")

    monkeypatch.setattr(StorageAdapter, "delete", broken_delete)
    failed = client.delete(f"/projects/{project_id}", headers=auth)
    assert failed.json()["deleted"] is False

    session = SessionLocal()
    project = session.get(Project, uuid.UUID(project_id))
    assert project.status == "deleting"
    session.close()

    monkeypatch.undo()
    retried = client.delete(f"/projects/{project_id}", headers=auth)
    assert retried.json()["deleted"] is True


def test_account_deletion_purges_without_external_identity_step(client, auth):
    """ADR-0006: deletion ends after the application-side purge."""
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import Workspace

    client.post("/projects", json={"name": "账号删除"}, headers=auth)

    response = client.delete("/account", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body == {"purged": True}

    # Count before any later authorized call: require_workspace find-or-creates
    # a fresh workspace for the same subject once the old one is purged.
    session = SessionLocal()
    workspace_count = session.scalar(
        select(func.count(Workspace.id)).where(Workspace.subject == "teacher_a")
    )
    session.close()
    assert workspace_count == 0

    status = client.get("/account/deletion-status", headers=auth)
    statuses = [item["status"] for item in status.json()]
    assert "purged" in statuses

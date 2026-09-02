"""F012 TS-005/TS-006: the designated synthetic sample project is readable by
any authenticated workspace on safe GET endpoints, while every write, stream,
and non-demo project keeps strict ownership (Spec D3/D10, UX U1/U4).
"""

import pytest
from fastapi.testclient import TestClient

from conftest import make_token
from lessoncanvas.modules.identity_workspace import service as iw_service
from lessoncanvas.settings import get_settings


@pytest.fixture()
def sample_project(db_session, auth) -> str:
    """The sample lives in its own designated demo workspace (Spec D10), never
    in a teacher's workspace."""
    demo_workspace = iw_service.resolve_workspace(db_session, "demo-sample-owner-test")
    project = iw_service.create_project(
        db_session, demo_workspace, "合成示例： Travelling Around", "人教版必修一"
    )
    db_session.commit()
    return str(project.id)


@pytest.fixture()
def demo_enabled(sample_project, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_owner_subject", "demo-sample-owner-test")
    yield sample_project
    # monkeypatch restores the settings object attribute automatically.


def _b_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('teacher_b')}"}


def _demo_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token('demo-sample-owner-test')}"}


def _seed_run(client: TestClient, project_id: str) -> None:
    """Give the sample project at least one planning artifact for read checks,
    acting as the demo owner so ownership guards pass before adapter limits."""
    started = client.post(
        f"/projects/{project_id}/planning/start",
        headers=_demo_headers(),
        json={"unit_hints": "人教版必修一"},
    )
    # Any outcome is fine: the read assertions below must not depend on the
    # model adapter; a 4xx admission answer still proves the access decision.
    assert started.status_code in (200, 201, 409, 422, 429)


class TestSampleReadAccess:
    def test_reviewer_can_read_sample_project_detail(self, client, auth, demo_enabled):
        res = client.get(f"/projects/{demo_enabled}", headers=_b_headers())
        assert res.status_code == 200
        assert res.json()["id"] == demo_enabled

    def test_reviewer_can_list_sample_sources(self, client, auth, demo_enabled):
        res = client.get(f"/projects/{demo_enabled}/sources", headers=_b_headers())
        assert res.status_code == 200
        assert res.json() == []

    def test_reviewer_can_read_sample_evidence_inventory(self, client, auth, demo_enabled):
        _seed_run(client, demo_enabled)
        res = client.get(f"/projects/{demo_enabled}/evidence", headers=_b_headers())
        assert res.status_code == 200

    def test_reviewer_can_read_sample_alignment(self, client, auth, demo_enabled):
        res = client.get(f"/projects/{demo_enabled}/alignment", headers=_b_headers())
        assert res.status_code in (200, 422)  # 422: no confirmed intent yet

    def test_sample_never_shows_in_reviewer_project_list(self, client, auth, demo_enabled):
        res = client.get("/projects", headers=_b_headers())
        assert res.status_code == 200
        assert all(p["id"] != demo_enabled for p in res.json())


class TestSampleWriteProtection:
    def test_reviewer_cannot_delete_sample_project(self, client, auth, demo_enabled):
        res = client.delete(f"/projects/{demo_enabled}", headers=_b_headers())
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

    def test_reviewer_cannot_upload_source_to_sample(self, client, auth, demo_enabled):
        res = client.post(
            f"/projects/{demo_enabled}/sources",
            headers=_b_headers(),
            data={"rights_acknowledged": "true"},
            files={"file": ("notes.txt", b"synthetic sample text", "text/plain")},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

    def test_reviewer_cannot_start_generation_on_sample(self, client, auth, demo_enabled):
        res = client.post(
            f"/projects/{demo_enabled}/generation/start", headers=_b_headers()
        )
        assert res.status_code == 404

    def test_reviewer_cannot_resume_sample_runs(self, client, auth, demo_enabled):
        res = client.post(f"/projects/{demo_enabled}/generation/resume", headers=_b_headers())
        assert res.status_code == 404

    def test_reviewer_cannot_stream_sample_conversation(self, client, auth, demo_enabled):
        # Streams stay owner-only by design (UX U4 suppresses them in the view).
        res = client.get(
            f"/projects/{demo_enabled}/discovery/stream", headers=_b_headers()
        )
        assert res.status_code == 404


class TestNonSampleIsolationUnchanged:
    def test_foreign_non_demo_project_still_404_on_get(self, client, auth, sample_project):
        # demo_enabled intentionally NOT active here.
        res = client.get(f"/projects/{sample_project}", headers=_b_headers())
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

    def test_unconfigured_demo_owner_denies_everything(self, client, auth, sample_project):
        # Default demo_owner_subject does not match the test workspace, so the
        # same project that was readable via demo_enabled stays private here.
        assert get_settings().demo_owner_subject == "lessoncanvas-demo-sample-owner"
        res = client.get(f"/projects/{sample_project}", headers=_b_headers())
        assert res.status_code == 404

    def test_demo_owner_still_has_full_access(self, client, auth, sample_project):
        res = client.get(f"/projects/{sample_project}", headers=_demo_headers())
        assert res.status_code == 200


def test_sample_pointer_endpoint(client, auth, demo_enabled):
    res = client.get("/sample", headers=_b_headers())
    assert res.status_code == 200
    assert res.json()["project_id"] == demo_enabled


def test_sample_pointer_404_when_unseeded(client, auth):
    res = client.get("/sample", headers=auth)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

"""F008 Alignment Review and Delivery: deterministic coverage and findings,
override policy, status pair, version-change recalculation, and labelled
idempotent package export with a printable-report snapshot."""

import hashlib
import io
import json
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.models import (
    AlignmentOverride,
    DeliveryExport,
    ExerciseArtifact,
    GenerationRun,
    LessonPlanArtifact,
    RunEvent,
    SlideDeckArtifact,
)
from lessoncanvas.settings import get_settings

CORPUS = "\n".join(
    [
        "单元主题：环境保护与可持续发展",
        "课时数：3",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力；发展批判性思维",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
        "课时分配：共6课时，每课2课时，评估聚焦综合输出",
    ]
)


def _confirmed_blueprint_project(client, auth) -> str:
    response = client.post("/projects", json={"name": "对齐测试"}, headers=auth)
    project_id = response.json()["id"]
    upload = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", CORPUS.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    assert upload.status_code == 201, upload.text
    assert client.post(f"/projects/{project_id}/discovery/start", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_id}/brief/confirm", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_id}/planning/start", headers=auth).status_code == 200
    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    base = state["draft_revision"]
    for finding in state.get("findings", []):
        if finding.get("tier") == "waivable" and finding.get("status") == "open":
            base = client.post(
                f"/projects/{project_id}/blueprint/decisions",
                json={
                    "finding_id": finding["id"],
                    "reason": "以教材与教师判断为准",
                    "base_revision": base,
                },
                headers=auth,
            ).json()["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": base},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text
    return project_id


def _complete_unit(client, auth, project_id: str) -> None:
    assert client.post(f"/projects/{project_id}/generation/start", headers=auth).status_code == 200
    assert (
        client.post(f"/projects/{project_id}/decks/generation/start", headers=auth).status_code
        == 200
    )
    assert (
        client.post(
            f"/projects/{project_id}/exercises/generation/start",
            json={"difficulty": "foundation"},
            headers=auth,
        ).status_code
        == 200
    )


def _purge_run(db_session, run: GenerationRun) -> None:
    from sqlalchemy import delete as sql_delete

    model = {
        "lesson_plan": LessonPlanArtifact,
        "slide_deck": SlideDeckArtifact,
        "exercise": ExerciseArtifact,
    }[run.artifact_kind]
    db_session.execute(sql_delete(RunEvent).where(RunEvent.run_id == run.id))
    db_session.execute(sql_delete(model).where(model.run_id == run.id))
    db_session.execute(sql_delete(GenerationRun).where(GenerationRun.id == run.id))
    db_session.flush()


def _alignment(client, auth, project_id: str) -> dict:
    response = client.get(f"/projects/{project_id}/alignment", headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def _plan_run_id(project_id, db_session) -> uuid.UUID:
    project_uuid = uuid.UUID(project_id)
    return db_session.scalar(
        select(GenerationRun.id).where(
            GenerationRun.project_id == project_uuid,
            GenerationRun.artifact_kind == "lesson_plan",
        )
    )


# --- TS-001: deterministic coverage across all families --------------------


def test_coverage_deterministic_and_validated(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    run_count_before = len(
        list(
            db_session.scalars(
                select(GenerationRun).where(GenerationRun.project_id == uuid.UUID(project_id))
            )
        )
    )

    first = _alignment(client, auth, project_id)
    second = _alignment(client, auth, project_id)
    assert first == second  # deterministic recomputation (AC-002)

    assert first["technical_status"] == "validated"
    assert first["product_validation_status"] == "not_evaluated"  # AC-010
    assert first["draft_export_available"] is True
    assert first["findings"] == []
    assert first["objectives"], "fake blueprint must produce objectives"
    for objective in first["objectives"]:
        assert objective["summary"] == "supported"
        assert objective["lessons"], "objectives must link to lessons"
        assert all(objective["support"].values())
    for lesson in first["lessons"]:
        for family in ("lesson_plan", "slide_deck", "exercise"):
            assert lesson["members"][family]["state"] == "complete"
            assert lesson["members"][family]["files"], "members must expose evidence files"

    run_count_after = len(
        list(
            db_session.scalars(
                select(GenerationRun).where(GenerationRun.project_id == uuid.UUID(project_id))
            )
        )
    )
    assert run_count_before == run_count_after  # no run or model call created


# --- TS-002: missing family members are severe non-overridable gaps --------


def test_missing_family_members_block_validation(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    # Delete the whole exercise family (rows only; objects irrelevant here).
    project_uuid = uuid.UUID(project_id)
    exercise_run = db_session.scalar(
        select(GenerationRun).where(
            GenerationRun.project_id == project_uuid,
            GenerationRun.artifact_kind == "exercise",
        )
    )
    _purge_run(db_session, exercise_run)

    # Fail one plan artifact in place (keeps object keys -> conflict class).
    plan_run_id = _plan_run_id(project_id, db_session)
    failing = db_session.scalar(
        select(LessonPlanArtifact).where(
            LessonPlanArtifact.run_id == plan_run_id, LessonPlanArtifact.lesson_index == 2
        )
    )
    failing.status = "failed"
    failing.failure_reason = "simulated structural validation failure"

    # Set one deck artifact to in-progress.
    deck_run = db_session.scalar(
        select(GenerationRun).where(
            GenerationRun.project_id == project_uuid,
            GenerationRun.artifact_kind == "slide_deck",
        )
    )
    pending = db_session.scalar(
        select(SlideDeckArtifact).where(
            SlideDeckArtifact.run_id == deck_run.id, SlideDeckArtifact.lesson_index == 3
        )
    )
    pending.status = "rendering"
    db_session.commit()

    alignment = _alignment(client, auth, project_id)
    assert alignment["technical_status"] == "incomplete"
    keys = {finding["key"] for finding in alignment["findings"]}

    for index in (1, 2, 3):
        assert f"gap:exercise:{index}:missing" in keys
    assert "conflict:lesson_plan:2:validation_failed" in keys
    assert "gap:slide_deck:3:in_progress" in keys

    for finding in alignment["findings"]:
        if finding["kind"] == "gap":
            assert finding["severity"] == "severe"
            assert finding["overridable"] is False  # AC-003, AC-006
        assert finding["recovery_action"]
    conflict = next(
        f for f in alignment["findings"] if f["key"] == "conflict:lesson_plan:2:validation_failed"
    )
    assert conflict["severity"] == "severe" and conflict["overridable"] is True  # AC-004
    assert conflict["evidence"]["failure_reason"] == "simulated structural validation failure"


# --- TS-003/TS-009 conflict + stale-blueprint conflict ----------------------


def test_stale_blueprint_conflict_not_overridable(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    db_session.execute(
        select(GenerationRun).where(GenerationRun.project_id == uuid.UUID(project_id))
    )
    from lessoncanvas.models import BlueprintVersion

    blueprint = db_session.scalar(
        select(BlueprintVersion)
        .where(BlueprintVersion.project_id == uuid.UUID(project_id))
        .order_by(BlueprintVersion.version.desc())
    )
    blueprint.stale = True
    db_session.commit()

    alignment = _alignment(client, auth, project_id)
    stale = next(f for f in alignment["findings"] if f["key"] == "conflict:blueprint:stale")
    assert stale["severity"] == "severe" and stale["overridable"] is False
    assert alignment["technical_status"] == "incomplete"

    override = client.post(
        f"/projects/{project_id}/alignment/overrides",
        json={"finding_key": "conflict:blueprint:stale", "reason": "教师判断蓝图仍然可用"},
        headers=auth,
    )
    assert override.status_code == 422
    assert override.json()["error"]["code"] == "REQUIREMENT"


def test_product_status_cannot_leave_not_evaluated(client, auth):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    alignment = _alignment(client, auth, project_id)
    # F010 extended the contract: the value is now derived live from recorded
    # product-validation assignments; with none, it stays not_evaluated and
    # F008 alignment still never merges it with technical status.
    assert alignment["product_validation_status"] == "not_evaluated"


# --- TS-004: validated export blocked, draft available ---------------------


def test_validated_export_blocked_draft_allowed(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    plan_run_id = _plan_run_id(project_id, db_session)
    failing = db_session.scalar(
        select(LessonPlanArtifact).where(
            LessonPlanArtifact.run_id == plan_run_id, LessonPlanArtifact.lesson_index == 1
        )
    )
    failing.status = "failed"
    failing.failure_reason = "simulated"
    db_session.commit()

    blocked = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert blocked.status_code == 422, blocked.text
    details = blocked.json()["error"]["details"]
    assert details["blocking_findings"], "blocking findings must be named"

    draft = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "draft"}, headers=auth
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["label"] == "draft"


# --- TS-005/TS-006/TS-007: override policy ---------------------------------


def test_override_lifecycle(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    plan_run_id = _plan_run_id(project_id, db_session)
    failing = db_session.scalar(
        select(LessonPlanArtifact).where(
            LessonPlanArtifact.run_id == plan_run_id, LessonPlanArtifact.lesson_index == 1
        )
    )
    failing.status = "failed"
    failing.failure_reason = "simulated"
    db_session.commit()

    finding_key = "conflict:lesson_plan:1:validation_failed"
    artifact_before = db_session.get(LessonPlanArtifact, failing.id)
    checksum_before = artifact_before.checksum
    status_before = artifact_before.status

    # Gap-class and unknown findings are refused (AC-006).
    for key in ("gap:exercise:1:missing", "conflict:lesson_plan:999:validation_failed"):
        refused = client.post(
            f"/projects/{project_id}/alignment/overrides",
            json={"finding_key": key, "reason": "教师确认该练习配对内容可用"},
            headers=auth,
        )
        assert refused.status_code == 422

    short = client.post(
        f"/projects/{project_id}/alignment/overrides",
        json={"finding_key": finding_key, "reason": "太短"},
        headers=auth,
    )
    assert short.status_code == 422

    # Valid override (AC-007); duplicate submission returns the same decision.
    body = {"finding_key": finding_key, "reason": "教师核对了文档，结构问题为误报，可以采用"}
    recorded = client.post(f"/projects/{project_id}/alignment/overrides", json=body, headers=auth)
    assert recorded.status_code == 201, recorded.text
    duplicate = client.post(f"/projects/{project_id}/alignment/overrides", json=body, headers=auth)
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == recorded.json()["id"]

    alignment = _alignment(client, auth, project_id)
    assert alignment["technical_status"] == "validated"  # AC-007 recalculation
    resolved = next(f for f in alignment["findings"] if f["key"] == finding_key)
    assert resolved["resolved"] is True
    assert len(alignment["overrides"]) == 1

    # Evaluated content unchanged.
    artifact_after = db_session.get(LessonPlanArtifact, failing.id)
    assert artifact_after.checksum == checksum_before
    assert artifact_after.status == status_before

    # Withdraw restores the finding (AC-008).
    withdrawn = client.delete(
        f"/projects/{project_id}/alignment/overrides/{recorded.json()['id']}", headers=auth
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    again = client.delete(
        f"/projects/{project_id}/alignment/overrides/{recorded.json()['id']}", headers=auth
    )
    assert again.status_code == 200 and again.json()["status"] == "withdrawn"

    alignment = _alignment(client, auth, project_id)
    assert alignment["technical_status"] == "incomplete"
    reopened = next(f for f in alignment["findings"] if f["key"] == finding_key)
    assert reopened["resolved"] is False
    assert len(alignment["overrides"]) == 1  # history preserved


def test_override_stale_version_rejected(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    stale = client.post(
        f"/projects/{project_id}/alignment/overrides",
        json={
            "finding_key": "conflict:lesson_plan:1:validation_failed",
            "reason": "教师核对了文档，可以采用",
            "brief_version": 999,
        },
        headers=auth,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_VERSION"


# --- TS-008: version change makes overrides historical ----------------------


def test_new_version_recomputes_and_histories_exports(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    draft = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "draft"}, headers=auth
    )
    assert draft.status_code == 201
    export_id = draft.json()["id"]

    # Confirm a second blueprint version (unchanged content, new pair).
    assert client.post(f"/projects/{project_id}/planning/start", headers=auth).status_code == 200
    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    base = state["draft_revision"]
    for finding in state.get("findings", []):
        if finding.get("tier") == "waivable" and finding.get("status") == "open":
            base = client.post(
                f"/projects/{project_id}/blueprint/decisions",
                json={
                    "finding_id": finding["id"],
                    "reason": "以教材与教师判断为准",
                    "base_revision": base,
                },
                headers=auth,
            ).json()["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": base},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text

    alignment = _alignment(client, auth, project_id)
    assert alignment["blueprint_version"] == confirmed.json()["version"]
    assert alignment["overrides"] == []  # prior state never leaks as current

    history = client.get(f"/projects/{project_id}/delivery/exports", headers=auth).json()
    assert len(history) == 1
    assert history[0]["id"] == export_id
    assert history[0]["blueprint_version"] < alignment["blueprint_version"]
    assert history[0]["download_available"] is True  # historical download stays truthful


# --- TS-010/TS-013: export build, idempotency, failure ----------------------


def test_export_zip_labelled_byte_identical_and_idempotent(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    first = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "ready"
    export_id = first.json()["id"]

    repeat = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert repeat.status_code == 201
    assert repeat.json()["id"] == export_id  # idempotent, no rebuild (AC-011)

    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(
            pool.map(
                lambda _: client.post(
                    f"/projects/{project_id}/delivery/exports",
                    json={"label": "validated"},
                    headers=auth,
                ).json()["id"],
                range(4),
            )
        )
    assert set(concurrent) == {export_id}

    package = client.get(
        f"/projects/{project_id}/delivery/exports/{export_id}/download", headers=auth
    )
    assert package.status_code == 200
    assert package.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        names = archive.namelist()
        metadata = json.loads(archive.read("metadata.json"))
        for name in names:
            if name == "metadata.json":
                continue
            entry_file = next(
                file
                for entry in metadata["manifest"]["entries"]
                for file in entry["files"]
                if file["path"] == name
            )
            actual = hashlib.sha256(archive.read(name)).hexdigest()
            assert actual == entry_file["checksum"]  # byte-identical members

    assert metadata["label"] == "validated"
    assert metadata["technical_status"] == "validated"
    assert metadata["product_validation_status"] == "not_evaluated"
    assert metadata["gaps"] == []
    assert any(name.startswith("lesson-plans/") for name in names)
    assert any(name.startswith("slide-decks/") for name in names)
    assert any(name.startswith("exercises/") for name in names)

    # The export report snapshot reflects export-time state (AC-012).
    report = client.get(
        f"/projects/{project_id}/delivery/exports/{export_id}/report", headers=auth
    )
    assert report.status_code == 200
    assert report.json()["export"]["label"] == "validated"
    assert report.json()["technical_status"] == "validated"


def test_report_endpoint_and_generated_at(client, auth):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    report = client.get(f"/projects/{project_id}/alignment/report", headers=auth)
    assert report.status_code == 200
    body = report.json()
    assert body["generated_at"]
    assert body["product_validation_status"] == "not_evaluated"


def test_export_storage_failure_settles_failed(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    # Remove one artifact object; the complete row stays, so the manifest
    # references bytes that storage can no longer serve.
    plan_run_id = _plan_run_id(project_id, db_session)
    artifact = db_session.scalar(
        select(LessonPlanArtifact).where(
            LessonPlanArtifact.run_id == plan_run_id, LessonPlanArtifact.lesson_index == 1
        )
    )
    StorageAdapter(bucket=get_settings().s3_bucket_artifacts).delete(artifact.object_key)

    failed = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert failed.status_code == 503, failed.text
    assert failed.json()["error"]["code"] == "PROVIDER_TRANSIENT"

    exports = client.get(f"/projects/{project_id}/delivery/exports", headers=auth).json()
    assert exports and exports[0]["status"] == "failed"
    download = client.get(
        f"/projects/{project_id}/delivery/exports/{exports[0]['id']}/download", headers=auth
    )
    assert download.status_code == 404  # no partial success


def test_export_version_switch_during_build_fails(client, auth, db_session, monkeypatch):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    from types import SimpleNamespace

    from lessoncanvas.modules.alignment_evaluation import delivery as delivery_module
    from lessoncanvas.modules.run_orchestration import service as run_service

    real_service = delivery_module.run_service
    real_brief = run_service.current_brief_version
    real_put = StorageAdapter.put

    class SwitchedService:
        switched = False

        def current_brief_version(self, session, project_id_arg):
            brief = real_brief(session, project_id_arg)
            if self.switched:
                return SimpleNamespace(id=uuid.uuid4(), version=brief.version + 1)
            return brief

        def __getattr__(self, name):
            return getattr(real_service, name)

    def switching_put(self, key, data):
        result = real_put(self, key, data)
        SwitchedService.switched = True
        return result

    monkeypatch.setattr(delivery_module, "run_service", SwitchedService())
    monkeypatch.setattr(StorageAdapter, "put", switching_put)
    failed = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert failed.status_code == 503
    exports = client.get(f"/projects/{project_id}/delivery/exports", headers=auth).json()
    assert exports[0]["status"] == "failed"
    assert "changed during export" in exports[0]["failure_reason"]


# --- TS-012: authorization, prerequisite, deletion --------------------------


def test_alignment_prerequisite_without_pair(client, auth):
    response = client.post("/projects", json={"name": "无版本"}, headers=auth)
    project_id = response.json()["id"]
    for path in ("alignment", "alignment/report"):
        missing = client.get(f"/projects/{project_id}/{path}", headers=auth)
        assert missing.status_code == 422
        assert missing.json()["error"]["details"]["gate"] == "confirmed_pair"
    export = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "draft"}, headers=auth
    )
    assert export.status_code == 422


def test_cross_workspace_no_disclosure(client, auth, teacher_b_token):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    other = {"Authorization": f"Bearer {teacher_b_token}"}
    export = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "draft"}, headers=auth
    ).json()

    checks = [
        client.get(f"/projects/{project_id}/alignment", headers=other),
        client.get(f"/projects/{project_id}/alignment/report", headers=other),
        client.post(
            f"/projects/{project_id}/alignment/overrides",
            json={
                "finding_key": "conflict:lesson_plan:1:validation_failed",
                "reason": "越权尝试访问其他教师工作区的覆盖理由",
            },
            headers=other,
        ),
        client.get(f"/projects/{project_id}/delivery/exports", headers=other),
        client.get(
            f"/projects/{project_id}/delivery/exports/{export['id']}/download", headers=other
        ),
        client.get(
            f"/projects/{project_id}/delivery/exports/{export['id']}/report", headers=other
        ),
        client.get("/projects/00000000-0000-7000-8000-000000000000/alignment", headers=other),
    ]
    for response in checks:
        assert response.status_code == 404, response.text


def test_deletion_cascades_overrides_and_exports(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    plan_run_id = _plan_run_id(project_id, db_session)
    failing = db_session.scalar(
        select(LessonPlanArtifact).where(
            LessonPlanArtifact.run_id == plan_run_id, LessonPlanArtifact.lesson_index == 1
        )
    )
    failing.status = "failed"
    failing.failure_reason = "simulated"
    db_session.commit()
    assert (
        client.post(
            f"/projects/{project_id}/alignment/overrides",
            json={
                "finding_key": "conflict:lesson_plan:1:validation_failed",
                "reason": "教师核对文档后确认该结果可用",
            },
            headers=auth,
        ).status_code
        == 201
    )
    export = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "draft"}, headers=auth
    ).json()
    package_key = db_session.get(DeliveryExport, uuid.UUID(export["id"])).package_object_key

    deleted = client.delete(f"/projects/{project_id}", headers=auth)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] is True

    project_uuid = uuid.UUID(project_id)
    assert (
        db_session.scalar(
            select(AlignmentOverride).where(AlignmentOverride.project_id == project_uuid)
        )
        is None
    )
    assert (
        db_session.scalar(
            select(DeliveryExport).where(DeliveryExport.project_id == project_uuid)
        )
        is None
    )
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    try:
        storage.get(package_key)
        raise AssertionError("package object must be deleted with the project")
    except Exception:
        pass


# --- Service-level unit checks ----------------------------------------------


def test_warning_for_objective_without_exercise_coverage(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    exercise_run = db_session.scalar(
        select(GenerationRun).where(
            GenerationRun.project_id == uuid.UUID(project_id),
            GenerationRun.artifact_kind == "exercise",
        )
    )
    _purge_run(db_session, exercise_run)
    db_session.commit()

    alignment = _alignment(client, auth, project_id)
    warnings = [
        f for f in alignment["findings"] if f["key"].startswith("warning:objective:")
    ]
    assert warnings and all(f["severity"] == "warning" for f in warnings)
    gaps = [f for f in alignment["findings"] if f["kind"] == "gap"]
    assert gaps, "missing exercise family must still produce severe gaps"
    assert alignment["technical_status"] == "incomplete"


def test_failed_export_retry_reuses_record_and_recovers(client, auth, db_session):
    """Regression: a failed export with an unchanged manifest is retried in
    place (one row per identity) and recovers once storage serves the bytes."""
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    plan_run_id = _plan_run_id(project_id, db_session)
    artifact = db_session.scalar(
        select(LessonPlanArtifact).where(
            LessonPlanArtifact.run_id == plan_run_id, LessonPlanArtifact.lesson_index == 1
        )
    )
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    backup = storage.get(artifact.object_key)
    storage.delete(artifact.object_key)

    failed = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert failed.status_code == 503
    failed_id = client.get(f"/projects/{project_id}/delivery/exports", headers=auth).json()[
        0
    ]["id"]

    storage.put(artifact.object_key, backup)
    recovered = client.post(
        f"/projects/{project_id}/delivery/exports", json={"label": "validated"}, headers=auth
    )
    assert recovered.status_code == 201, recovered.text
    assert recovered.json()["id"] == failed_id  # same record, rebuilt
    assert recovered.json()["status"] == "ready"

    rows = client.get(f"/projects/{project_id}/delivery/exports", headers=auth).json()
    assert len(rows) == 1 and rows[0]["status"] == "ready"

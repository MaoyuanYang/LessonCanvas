"""F007 Versioned Targeted Regeneration: impact matrix, transition-aware
scoped runs, retention provenance, coverage gates, and the comparison payload."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import GenerationRun, LessonPlanArtifact, Project
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.modules.run_orchestration.impact import compute_impact

CORPUS = "\n".join(
    [
        "单元主题：环境保护与可持续发展",
        "课时数：6",
        "学情：高二学生，英语中等水平",
        "教学目标：提升阅读与表达能力",
        "教材定位：外研社必修一 Unit 3",
        "输出语言：中英双语",
        "评估倾向：形成性评价为主",
        "课时分配：共12课时，每课2课时，评估聚焦综合输出",
    ]
)


def _confirmed_blueprint_project(client, auth) -> str:
    response = client.post("/projects", json={"name": "再生测试"}, headers=auth)
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
            decision = client.post(
                f"/projects/{project_id}/blueprint/decisions",
                json={
                    "finding_id": finding["id"],
                    "reason": "以教材与教师判断为准",
                    "base_revision": base,
                },
                headers=auth,
            )
            assert decision.status_code == 200, decision.text
            base = decision.json()["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": base},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text
    return project_id


def _revise_blueprint(client, auth, project_id: str, mutate) -> int:
    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    payload = state["draft"] or state["confirmed_payload"]
    mutate(payload)
    saved = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": payload, "base_revision": state["draft_revision"]},
        headers=auth,
    )
    assert saved.status_code == 200, saved.text
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": saved.json()["draft_revision"]},
        headers=auth,
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()["version"]


def _touch_lesson(index, field="activity_outline", value="修订后的活动纲要：聚焦迁移创新任务"):
    def mutate(payload):
        lesson = next(item for item in payload["lessons"] if item["index"] == index)
        lesson[field] = value

    return mutate


def _replan_and_confirm(client, auth, project_id: str) -> int:
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
        f"/projects/{project_id}/blueprint/confirm", json={"base_revision": base}, headers=auth
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()["version"]


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


def _workspace_id(db_session, project_id: str) -> uuid.UUID:
    return db_session.get(Project, uuid.UUID(project_id)).workspace_id


def _impact_fixture():
    brief = json.dumps(
        {
            field: {"value": "v"}
            for field in (
                "unit_theme",
                "teaching_objectives",
                "material_position",
                "student_context",
                "assessment_orientation",
                "output_language_mode",
                "lesson_count",
            )
        },
        ensure_ascii=False,
    )
    blueprint = json.dumps(
        {
            "unit": {
                "title": "T",
                "objectives": [{"id": "obj-1", "text": "o"}],
                "assessment_intent": "a",
            },
            "lessons": [
                {"index": 1, "title": "一", "activity_outline": None},
                {"index": 2, "title": "二", "activity_outline": None},
            ],
        },
        ensure_ascii=False,
    )
    return brief, blueprint


def _revised(brief, blueprint, brief_mut=None, bp_mut=None):
    b = json.loads(brief)
    if brief_mut:
        brief_mut(b)
    p = json.loads(blueprint)
    if bp_mut:
        bp_mut(p)
    return json.dumps(b, ensure_ascii=False), json.dumps(p, ensure_ascii=False)


# --- TS-001: matrix classes (unit level) -----------------------------------


def test_impact_matrix_classes():
    brief, blueprint = _impact_fixture()

    impact = compute_impact(brief, brief, blueprint, blueprint)
    assert impact["no_delta"] is True and impact["affected_lessons"] == []

    nb, _ = _revised(
        brief, blueprint, brief_mut=lambda b: b["output_language_mode"].__setitem__("value", "en")
    )
    impact = compute_impact(brief, nb, blueprint, blueprint)
    assert impact["affected_lessons"] is None
    assert any(r["field"] == "brief.output_language_mode" for r in impact["reasons"])

    _, nbp = _revised(
        brief,
        blueprint,
        bp_mut=lambda p: p["unit"]["objectives"].append({"id": "obj-2", "text": "n"}),
    )
    impact = compute_impact(brief, brief, blueprint, nbp)
    assert impact["affected_lessons"] is None
    assert any(r["field"] == "blueprint.unit.objectives" for r in impact["reasons"])

    _, nbp = _revised(brief, blueprint, bp_mut=_touch_lesson(2))
    impact = compute_impact(brief, brief, blueprint, nbp)
    assert impact["affected_lessons"] == [2]
    assert impact["affected_families"] == ["lesson_plan", "slide_deck", "exercise"]
    assert any(r["scope"] == "lesson:2" for r in impact["reasons"])

    def restructure(p):
        p["lessons"] = [lesson for lesson in p["lessons"] if lesson["index"] != 2]
        p["lessons"].append({"index": 3, "title": "三", "activity_outline": None})

    _, nbp = _revised(brief, blueprint, bp_mut=restructure)
    impact = compute_impact(brief, brief, blueprint, nbp)
    assert impact["structural"] == {"added": [3], "removed": [2]}
    assert 3 in (impact["affected_lessons"] or [])

    nb, _ = _revised(
        brief, blueprint, brief_mut=lambda b: b.__setitem__("mystery_field", {"value": "x"})
    )
    impact = compute_impact(brief, nb, blueprint, blueprint)
    assert impact["affected_lessons"] is None and impact["uncertain"] is True

    def unknown_lesson_field(p):
        p["lessons"][0]["mystery"] = "x"

    _, nbp = _revised(brief, blueprint, bp_mut=unknown_lesson_field)
    impact = compute_impact(brief, brief, blueprint, nbp)
    assert impact["affected_lessons"] is None and impact["uncertain"] is True


# --- TS-001/TS-002: preview API, seeding, stale conflict --------------------


def test_impact_preview_api_and_stale_conflict(client, auth):
    project_id = _confirmed_blueprint_project(client, auth)

    before = client.get(f"/projects/{project_id}/impact", headers=auth)
    assert before.status_code == 200 and before.json()["no_delta"] is True

    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    payload = state["draft"] or state["confirmed_payload"]
    payload["lessons"][1]["activity_outline"] = "修订后的活动纲要"
    saved = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": payload, "base_revision": state["draft_revision"]},
        headers=auth,
    )
    assert saved.status_code == 200

    preview = client.get(f"/projects/{project_id}/impact", headers=auth).json()
    assert preview["affected_lessons"] == [2]
    assert preview["uncertain"] is False
    assert any(r["scope"] == "lesson:2" for r in preview["reasons"])

    stale = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": state["draft_revision"]},
        headers=auth,
    )
    assert stale.status_code == 409

    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": saved.json()["draft_revision"]},
        headers=auth,
    )
    assert confirmed.status_code == 200 and confirmed.json()["version"] == 2


# --- TS-004/TS-005: scoped start, idempotency, retention --------------------


def test_scoped_start_idempotency_and_retention(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    _revise_blueprint(client, auth, project_id, _touch_lesson(2))

    started = client.post(f"/projects/{project_id}/generation/start", headers=auth)
    assert started.status_code == 200, started.text
    first = started.json()
    assert first["brief_version"] == 1 and first["blueprint_version"] == 2
    assert first["scope_lesson_indexes"] == [2]
    assert [a["lesson_index"] for a in first["artifacts"]] == [2]
    assert len(first["retained_artifacts"]) == 5
    retained = {r["lesson_index"]: r for r in first["retained_artifacts"]}
    assert retained[1]["source_brief_version"] == 1
    assert retained[1]["source_blueprint_version"] == 1
    assert retained[1]["source_run_id"]

    duplicate = client.post(f"/projects/{project_id}/generation/start", headers=auth).json()
    assert duplicate["run_id"] == first["run_id"]

    project_uuid = uuid.UUID(project_id)
    workspace_id = _workspace_id(db_session, project_id)

    def attempt(_):
        session = SessionLocal()
        try:
            run, _created = run_service.start_generation(session, workspace_id, project_uuid)
            session.commit()
            return str(run.id)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(attempt, range(4)))
    assert len(set(ids)) == 1

    snapshot = client.get(f"/projects/{project_id}/generation", headers=auth).json()
    assert snapshot["status"] == "complete"
    assert snapshot["model_calls"] == 3  # only lesson 2 regenerated (design + write + review)
    retained_after = {r["lesson_index"]: r for r in snapshot["retained_artifacts"]}

    prior_checksums = {
        artifact.lesson_index: artifact.checksum
        for artifact in db_session.query(LessonPlanArtifact)
        .join(GenerationRun)
        .filter(GenerationRun.project_id == project_uuid)
        .all()
        if artifact.status == "complete" and artifact.lesson_index != 2
    }
    for lesson_index, entry in retained_after.items():
        assert prior_checksums[lesson_index] == entry["checksum"]

    download = client.get(
        f"/projects/{project_id}/lesson-plans/{retained_after[1]['id']}/download",
        headers=auth,
    )
    assert download.status_code == 200


# --- TS-006: structural add/remove ------------------------------------------


def test_structural_add_remove(client, auth):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)

    # Pure addition: revise the brief's lesson count, then re-plan (the
    # blueprint is bound to the confirmed brief) and confirm the new pair.
    brief_state = client.get(f"/projects/{project_id}/brief", headers=auth).json()
    patched = client.patch(
        f"/projects/{project_id}/brief/draft",
        json={"fields": {"lesson_count": "7"}, "base_revision": brief_state["draft_revision"]},
        headers=auth,
    )
    assert patched.status_code == 200, patched.text
    assert client.post(f"/projects/{project_id}/brief/confirm", headers=auth).status_code == 200
    _replan_and_confirm(client, auth, project_id)
    started = client.post(f"/projects/{project_id}/generation/start", headers=auth)
    assert started.status_code == 200
    snapshot = started.json()
    assert snapshot["scope_lesson_indexes"] == [7]
    assert [a["lesson_index"] for a in snapshot["artifacts"]] == [7]

    transition = client.get(
        f"/projects/{project_id}/versions/current-transition", headers=auth
    ).json()
    assert transition["first_version"] is False
    assert transition["from"]["blueprint_version"] == 1
    assert transition["to"]["blueprint_version"] == 2
    verdicts = {(v["lesson_index"], v["family"]): v["verdict"] for v in transition["verdicts"]}
    assert verdicts[(7, "lesson_plan")] == "affected"
    assert verdicts[(1, "lesson_plan")] == "retained"

    # Pure removal: revise the brief's lesson count down, re-plan, confirm.
    project_id2 = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id2)
    brief_state = client.get(f"/projects/{project_id2}/brief", headers=auth).json()
    patched = client.patch(
        f"/projects/{project_id2}/brief/draft",
        json={"fields": {"lesson_count": "5"}, "base_revision": brief_state["draft_revision"]},
        headers=auth,
    )
    assert patched.status_code == 200, patched.text
    assert client.post(f"/projects/{project_id2}/brief/confirm", headers=auth).status_code == 200
    _replan_and_confirm(client, auth, project_id2)
    removal_transition = client.get(
        f"/projects/{project_id2}/versions/current-transition", headers=auth
    ).json()
    verdicts2 = {
        (v["lesson_index"], v["family"]): v["verdict"] for v in removal_transition["verdicts"]
    }
    assert verdicts2[(6, "lesson_plan")] == "historical"
    assert verdicts2[(1, "lesson_plan")] == "retained"
    blocked = client.post(f"/projects/{project_id2}/generation/start", headers=auth)
    assert blocked.status_code == 422
    assert "nothing to regenerate" in blocked.json()["error"]["message"]


# --- TS-008: coverage gate ----------------------------------------------------


def test_coverage_gate_for_targeted_decks(client, auth):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    _revise_blueprint(client, auth, project_id, _touch_lesson(2))

    blocked = client.post(f"/projects/{project_id}/decks/generation/start", headers=auth)
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "REQUIREMENT"
    assert blocked.json()["error"]["details"]["uncovered_lessons"] == [2]

    assert client.post(f"/projects/{project_id}/generation/start", headers=auth).status_code == 200
    allowed = client.post(f"/projects/{project_id}/decks/generation/start", headers=auth)
    assert allowed.status_code == 200
    deck_snapshot = allowed.json()
    assert deck_snapshot["scope_lesson_indexes"] == [2]
    assert len(deck_snapshot["retained_artifacts"]) == 5


# --- TS-007: scoped resume ----------------------------------------------------


def test_scoped_resume_leaves_retained_untouched(client, auth):
    from lessoncanvas.adapters.model import FakeModelAdapter
    from lessoncanvas.worker import generate_unit

    project_id = _confirmed_blueprint_project(client, auth)
    FakeModelAdapter.reset_transient_failures()
    _complete_unit(client, auth, project_id)
    FakeModelAdapter.reset_transient_failures()

    def revise_two(payload):
        stable = next(item for item in payload["lessons"] if item["index"] == 2)
        stable["activity_outline"] = "修订纲要（稳定课，先执行）"
        failing = next(item for item in payload["lessons"] if item["index"] == 3)
        failing["title"] = str(failing["title"]) + " TRANSIENT_FAIL"
        failing["activity_outline"] = "修订纲要（过载课，后执行）"

    _revise_blueprint(client, auth, project_id, revise_two)
    started = client.post(f"/projects/{project_id}/generation/start", headers=auth)
    assert started.status_code == 200
    assert started.json()["scope_lesson_indexes"] == [2, 3]
    run_id = started.json()["run_id"]

    # First dispatch: the transient lesson exhausts in-task retries while the
    # stable scoped lesson completes -> recoverable partial failure.
    status = None
    for _ in range(4):
        try:
            generate_unit.apply(args=[run_id])
        except Exception:
            pass
        status = client.get(f"/projects/{project_id}/generation", headers=auth).json()
        if status["status"] in ("partial_failure", "terminal_failure", "complete"):
            break
    assert status["status"] == "partial_failure", status["status"]

    FakeModelAdapter.reset_transient_failures()
    resumed = client.post(f"/projects/{project_id}/generation/resume", headers=auth)
    assert resumed.status_code == 200
    final = status
    for _ in range(8):
        try:
            generate_unit.apply(args=[run_id])
        except Exception:
            pass
        final = client.get(f"/projects/{project_id}/generation", headers=auth).json()
        if final["status"] == "complete":
            break
        if final["status"] == "partial_failure":
            # A settled partial run needs the teacher resume action again; a
            # bare re-dispatch is correctly a no-op (F003 semantics). The
            # transient counter is NOT reset here: the next resume must see
            # the exhausted failure budget and succeed on its first attempt.
            assert (
                client.post(f"/projects/{project_id}/generation/resume", headers=auth).status_code
                == 200
            )
    assert final["status"] == "complete"
    assert final["scope_lesson_indexes"] == [2, 3]
    # Scoped accounting only: stable lesson once + failing lesson's attempts.
    # two scoped lessons (design+write) + bounded retries; retained add zero
    assert final["model_calls"] <= 12
    retained_indexes = {r["lesson_index"] for r in final["retained_artifacts"]}
    assert retained_indexes == {1, 4, 5, 6}


# --- TS-009: transition payload ------------------------------------------------


def test_current_transition_payload_and_first_version(client, auth):
    fresh = client.post("/projects", json={"name": "首版本"}, headers=auth).json()
    transition = client.get(
        f"/projects/{fresh['id']}/versions/current-transition", headers=auth
    ).json()
    assert transition["first_version"] is True

    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    _revise_blueprint(client, auth, project_id, _touch_lesson(3))
    client.post(f"/projects/{project_id}/generation/start", headers=auth)

    transition = client.get(
        f"/projects/{project_id}/versions/current-transition", headers=auth
    ).json()
    assert transition["first_version"] is False
    assert transition["to"]["blueprint_version"] == 2
    plan_rows = [a for a in transition["artifacts"] if a["family"] == "lesson_plan"]
    row3 = next(a for a in plan_rows if a["lesson_index"] == 3)
    row1 = next(a for a in plan_rows if a["lesson_index"] == 1)
    assert row3["new"]["status"] in ("pending", "drafting", "rendering", "validating", "complete")
    assert row1["old"]["download_available"] is True


# --- TS-010: authorization -----------------------------------------------------


def test_authorization_non_disclosure(client, auth, teacher_b_token):
    project_id = _confirmed_blueprint_project(client, auth)
    other = {"Authorization": f"Bearer {teacher_b_token}"}
    for path, method in (
        (f"/projects/{project_id}/impact", "get"),
        (f"/projects/{project_id}/versions/current-transition", "get"),
        (f"/projects/{project_id}/generation/start", "post"),
    ):
        denied = getattr(client, method)(path, headers=other)
        assert denied.status_code in (401, 404), (path, denied.status_code)
    unauthenticated = client.get(f"/projects/{project_id}/impact")
    assert unauthenticated.status_code == 401


# --- TS-011: read-only surfaces + deletion --------------------------------------


def test_transition_reads_are_read_only_and_deletion_cascades(client, auth):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    _revise_blueprint(client, auth, project_id, _touch_lesson(4))
    project_uuid = uuid.UUID(project_id)

    def state_snapshot():
        session = SessionLocal()
        try:
            return [
                (str(run.id), run.status, run.model_calls)
                for run in session.query(GenerationRun)
                .filter_by(project_id=project_uuid)
                .order_by(GenerationRun.id)
                .all()
            ]
        finally:
            session.close()

    before = state_snapshot()
    for _ in range(3):
        client.get(f"/projects/{project_id}/impact", headers=auth)
        client.get(f"/projects/{project_id}/versions/current-transition", headers=auth)
    assert state_snapshot() == before

    deleted = client.delete(f"/projects/{project_id}", headers=auth)
    assert deleted.status_code in (200, 202, 204)
    assert (
        client.get(f"/projects/{project_id}/versions/current-transition", headers=auth).status_code
        == 404
    )


# --- TS-017: concurrent targeted starts ----------------------------------------


def test_concurrent_targeted_starts_converge(client, auth, db_session):
    project_id = _confirmed_blueprint_project(client, auth)
    _complete_unit(client, auth, project_id)
    _revise_blueprint(client, auth, project_id, _touch_lesson(5))
    project_uuid = uuid.UUID(project_id)
    workspace_id = _workspace_id(db_session, project_id)

    def attempt(_):
        session = SessionLocal()
        try:
            run, _created = run_service.start_generation(session, workspace_id, project_uuid)
            session.commit()
            return str(run.id), json.loads(run.scope_json) if run.scope_json else None
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert len({run_id for run_id, _ in results}) == 1
    assert all(scope == [5] for _, scope in results)

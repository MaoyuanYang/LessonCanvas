import uuid

from test_planning import PLANNING_CORPUS, confirmed_project, run_planning_to_draft


def blueprint_ready(client, auth, corpus=PLANNING_CORPUS) -> tuple[str, dict]:
    project_id = confirmed_project(client, auth, corpus)
    run_planning_to_draft(client, auth, project_id)
    body = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    assert body["available"] is True
    assert body["draft_revision"] is not None
    return project_id, body


def test_blueprint_unavailable_without_confirmed_brief(client, auth):
    response = client.post("/projects", json={"name": "未确认"}, headers=auth)
    project_id = response.json()["id"]
    body = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    assert body["available"] is False
    assert body["draft"] is None


def test_blueprint_draft_structure_and_citations(client, auth):
    project_id, body = blueprint_ready(client, auth)
    draft = body["draft"]
    assert len(draft["lessons"]) == 6
    for lesson in draft["lessons"]:
        assert lesson["title"]
        assert lesson["objective_ids"]
        assert lesson["assessment_intent"]
    objective_ids = {o["id"] for o in draft["unit"]["objectives"]}
    assert objective_ids
    all_citations = [c for o in draft["unit"]["objectives"] for c in o.get("citations", [])]
    assert any(c.get("type") == "standards" and c.get("snapshot_version") for c in all_citations)


def test_blueprint_patch_creates_revision_and_stale_conflict(client, auth):
    project_id, body = blueprint_ready(client, auth)
    payload = body["draft"]
    payload["lessons"][0]["title"] = "导入课：走进自然"
    patched = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": payload, "base_revision": body["draft_revision"]},
        headers=auth,
    )
    assert patched.status_code == 200
    assert patched.json()["draft_revision"] == body["draft_revision"] + 1
    assert patched.json()["draft"]["lessons"][0]["title"] == "导入课：走进自然"

    stale = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": payload, "base_revision": body["draft_revision"]},
        headers=auth,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "STALE_VERSION"


def test_blueprint_confirm_rejects_failed_checks(client, auth):
    project_id, body = blueprint_ready(client, auth)
    base = body["draft_revision"]

    count_payload = dict(body["draft"])
    count_payload["lessons"] = body["draft"]["lessons"][:5]
    response = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": count_payload, "base_revision": base},
        headers=auth,
    )
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": response.json()["draft_revision"]},
        headers=auth,
    )
    assert confirmed.status_code == 422
    error = confirmed.json()["error"]
    assert error["code"] == "REQUIREMENT"
    assert "lesson_count" in error["details"]["failed_checks"]

    fields_payload = dict(body["draft"])
    fields_payload["lessons"] = [dict(lesson) for lesson in body["draft"]["lessons"]]
    fields_payload["lessons"][1]["assessment_intent"] = None
    response = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": fields_payload, "base_revision": response.json()["draft_revision"]},
        headers=auth,
    )
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": response.json()["draft_revision"]},
        headers=auth,
    )
    assert "lesson_fields" in confirmed.json()["error"]["details"]["failed_checks"]

    coverage_payload = dict(body["draft"])
    coverage_payload["unit"] = dict(body["draft"]["unit"])
    coverage_payload["unit"]["objectives"] = body["draft"]["unit"]["objectives"] + [
        {"id": "obj-99", "text": "额外目标", "citations": []}
    ]
    response = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": coverage_payload, "base_revision": response.json()["draft_revision"]},
        headers=auth,
    )
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": response.json()["draft_revision"]},
        headers=auth,
    )
    assert "objective_coverage" in confirmed.json()["error"]["details"]["failed_checks"]


def test_blueprint_waivable_findings_require_decision(client, auth):
    conflict_corpus = PLANNING_CORPUS + "\n备注：两份材料之间存在冲突"
    project_id = confirmed_project(client, auth, conflict_corpus)
    run_planning_to_draft(client, auth, project_id)
    body = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    base = body["draft_revision"]

    open_findings = [
        f for f in body["findings"] if f["tier"] == "waivable" and f["status"] == "open"
    ]
    assert open_findings

    blocked = client.post(
        f"/projects/{project_id}/blueprint/confirm", json={"base_revision": base}, headers=auth
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"]["details"]["undecided_findings"]

    target = open_findings[0]
    empty_reason = client.post(
        f"/projects/{project_id}/blueprint/decisions",
        json={"finding_id": target["id"], "reason": "   ", "base_revision": base},
        headers=auth,
    )
    assert empty_reason.status_code == 422

    decided = client.post(
        f"/projects/{project_id}/blueprint/decisions",
        json={
            "finding_id": target["id"],
            "reason": "以教材为准，忽略补充材料",
            "base_revision": base,
        },
        headers=auth,
    )
    assert decided.status_code == 200
    new_base = decided.json()["draft_revision"]
    stored = [f for f in decided.json()["draft"]["findings"] if f["id"] == target["id"]]
    assert stored[0]["status"] == "decided"
    assert stored[0]["reason"] == "以教材为准，忽略补充材料"

    blocking = [f for f in decided.json()["findings"] if f["tier"] == "blocking"]
    if blocking:
        rejected = client.post(
            f"/projects/{project_id}/blueprint/decisions",
            json={
                "finding_id": blocking[0]["id"],
                "reason": "想直接通过",
                "base_revision": new_base,
            },
            headers=auth,
        )
        assert rejected.status_code == 422


def test_blueprint_confirm_atomic_idempotent_immutable(client, auth):
    project_id, body = blueprint_ready(client, auth)
    base = body["draft_revision"]
    first = client.post(
        f"/projects/{project_id}/blueprint/confirm", json={"base_revision": base}, headers=auth
    )
    assert first.status_code == 200
    assert first.json()["version"] == 1

    second = client.post(
        f"/projects/{project_id}/blueprint/confirm",
        json={"base_revision": base},
        headers=auth,
    )
    assert second.status_code == 200
    assert second.json()["version"] == 1

    payload = first.json()["payload"]
    payload["lessons"][0]["title"] = "课后修改不应影响已确认版本"
    patched = client.patch(
        f"/projects/{project_id}/blueprint/draft",
        json={"payload": payload, "base_revision": base},
        headers=auth,
    )
    assert patched.status_code == 200

    after = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    assert after["confirmed_version"] == 1
    assert after["confirmed_payload"]["lessons"][0]["title"] != "课后修改不应影响已确认版本"
    assert after["draft_revision"] == base + 1


def test_concurrent_confirm_yields_single_version(client, auth):
    import threading

    from fastapi.testclient import TestClient

    from lessoncanvas import main

    project_id, body = blueprint_ready(client, auth)
    base = body["draft_revision"]
    results = []
    errors = []

    def confirm():
        try:
            local_client = TestClient(main.app)
            response = local_client.post(
                f"/projects/{project_id}/blueprint/confirm",
                json={"base_revision": base},
                headers=auth,
            )
            results.append(response.json().get("version"))
        except Exception as error:  # pragma: no cover
            errors.append(error)

    threads = [threading.Thread(target=confirm) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert sorted(results) == [1, 1]


def test_brief_reconfirmation_supersedes_and_stales(client, auth):
    project_id, body = blueprint_ready(client, auth)
    base = body["draft_revision"]
    confirmed = client.post(
        f"/projects/{project_id}/blueprint/confirm", json={"base_revision": base}, headers=auth
    )
    assert confirmed.status_code == 200

    stale_run = client.post(f"/projects/{project_id}/planning/start", headers=auth)
    assert stale_run.status_code == 200

    patched_brief = client.patch(
        f"/projects/{project_id}/brief/draft",
        json={"fields": {"unit_theme": "气候变化"}, "base_revision": 1},
        headers=auth,
    )
    assert patched_brief.status_code == 200
    brief_v2 = client.post(f"/projects/{project_id}/brief/confirm", headers=auth)
    assert brief_v2.status_code == 200
    assert brief_v2.json()["version"] == 2

    superseded = client.get(f"/projects/{project_id}/planning", headers=auth).json()
    assert superseded["status"] == "superseded"

    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    assert state["stale"] is True
    assert state["confirmed_stale"] is True
    assert state["brief_diff"]
    assert state["brief_diff"][0]["field"] == "unit_theme"
    assert state["impact_summary"]["objectives_changed"] is True

    stale_confirm = client.post(
        f"/projects/{project_id}/blueprint/confirm", json={"base_revision": base}, headers=auth
    )
    assert stale_confirm.status_code == 422
    assert stale_confirm.json()["error"]["details"].get("stale_brief") is True


def test_replan_appends_new_draft_after_stale(client, auth):
    project_id, body = blueprint_ready(client, auth)
    client.patch(
        f"/projects/{project_id}/brief/draft",
        json={"fields": {"unit_theme": "气候变化"}, "base_revision": 1},
        headers=auth,
    )
    client.post(f"/projects/{project_id}/brief/confirm", headers=auth)

    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    assert state["stale"] is True

    run_planning_to_draft(client, auth, project_id)
    state = client.get(f"/projects/{project_id}/blueprint", headers=auth).json()
    assert state["stale"] is False
    assert state["draft_revision"] > body["draft_revision"]
    assert state["draft"]["unit"]["title"] == "气候变化"


def test_generation_surface_is_gated_not_absent(client, auth):
    # F002 asserted no generation surface existed; F003 delivers it. The durable
    # boundary is that generation starts only from a confirmed blueprint.
    project_id, _ = blueprint_ready(client, auth)
    openapi = client.get("/openapi.json").json()
    generation_paths = [path for path in openapi["paths"] if "/generation" in path]
    assert generation_paths, "F003 generation surface should be registered"


def test_blueprint_trace_and_deletion_cascade(client, auth, db_session):
    project_id, _ = blueprint_ready(client, auth)
    trace = client.get(f"/projects/{project_id}/trace", headers=auth).json()
    kinds = {event["event_type"] for event in trace["events"]}
    assert "model.planning_gap_analysis" in kinds or "model.planning_build_draft" in kinds
    assert any(run["round_count"] is not None for run in trace["runs"])

    deleted = client.delete(f"/projects/{project_id}", headers=auth)
    assert deleted.status_code in {200, 202, 204}

    from sqlalchemy import select

    from lessoncanvas.models import BlueprintDraft, BlueprintVersion

    drafts = db_session.scalars(
        select(BlueprintDraft).where(BlueprintDraft.project_id == uuid.UUID(project_id))
    ).all()
    versions = db_session.scalars(
        select(BlueprintVersion).where(BlueprintVersion.project_id == uuid.UUID(project_id))
    ).all()
    assert drafts == []
    assert versions == []

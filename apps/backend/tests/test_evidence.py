"""F006 Layered Run Evidence: inventory, summary, paginated technical events,
explanation narration, authorization, read-only invariance, and legacy-gap
honesty over the five run kinds."""

import json
import time
import uuid

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import BriefVersion, GenerationRun, Project, QuotaCounter, TraceEvent
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.run_orchestration import evidence
from lessoncanvas.modules.run_orchestration import service as run_service

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
    response = client.post("/projects", json={"name": "证据测试"}, headers=auth)
    project_id = response.json()["id"]
    upload = client.post(
        f"/projects/{project_id}/sources",
        files={"file": ("notes.txt", CORPUS.encode(), "text/plain")},
        data={"rights_acknowledged": "true"},
        headers=auth,
    )
    assert upload.status_code == 201, upload.text
    assert client.post(f"/projects/{project_id}/discovery/start", headers=auth).status_code == 200
    assert (
        client.post(f"/projects/{project_id}/brief/confirm", headers=auth).status_code == 200
    )
    assert client.post(f"/projects/{project_id}/planning/start", headers=auth).status_code == 200
    blueprint = client.get(f"/projects/{project_id}/blueprint", headers=auth)
    state = blueprint.json()
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


def _full_run_project(client, auth) -> str:
    """Project with discovery + planning + complete lesson-plan + deck +
    exercise runs (eager worker, fake adapter)."""

    project_id = _confirmed_blueprint_project(client, auth)
    started = client.post(f"/projects/{project_id}/generation/start", headers=auth)
    assert started.status_code == 200, started.text
    decks = client.post(f"/projects/{project_id}/decks/generation/start", headers=auth)
    assert decks.status_code == 200, decks.text
    exercises = client.post(
        f"/projects/{project_id}/exercises/generation/start",
        json={"difficulty": "foundation"},
        headers=auth,
    )
    assert exercises.status_code == 200, exercises.text
    return project_id


def _run_ids(client, auth, project_id) -> dict[str, str]:
    inventory = client.get(f"/projects/{project_id}/evidence", headers=auth).json()
    return {run["kind"]: run["run_id"] for run in inventory["runs"]}


# --- TS-005: estimated cost derives from the price table ---------------


def test_cost_estimation_math_and_record_trace_persistence(client, auth, db_session):
    from lessoncanvas.settings import get_settings

    settings = get_settings()
    expected = round(
        120 / 1_000_000 * settings.model_price_prompt_per_mtok
        + 340 / 1_000_000 * settings.model_price_completion_per_mtok,
        6,
    )
    assert evidence.estimated_cost_usd(120, 340) == expected

    project = client.post("/projects", json={"name": "成本"}, headers=auth).json()
    project_row = db_session.get(Project, uuid.UUID(project["id"]))
    brief = BriefVersion(
        project_id=project_row.id,
        workspace_id=project_row.workspace_id,
        version=1,
        source_revision=1,
        fields_json="{}",
    )
    db_session.add(brief)
    db_session.flush()
    from lessoncanvas.models import BlueprintVersion

    blueprint = BlueprintVersion(
        project_id=project_row.id,
        workspace_id=project_row.workspace_id,
        brief_version_id=brief.id,
        version=1,
        source_revision=1,
        payload_json=json.dumps({"lessons": []}),
    )
    db_session.add(blueprint)
    db_session.flush()
    run = GenerationRun(
        project_id=project_row.id,
        workspace_id=project_row.workspace_id,
        brief_version_id=brief.id,
        blueprint_version_id=blueprint.id,
        artifact_kind="lesson_plan",
        status="complete",
        model_call_cap=10,
    )
    db_session.add(run)
    db_session.commit()

    class _Usage:
        prompt_tokens = 120
        completion_tokens = 340

    record_trace(
        db_session, str(run.id), "model.generation_write_lesson", {"prompt": {}, "response": {}},
        55, usage=_Usage(),
    )
    record_trace(
        db_session, str(run.id), "tool.render_lesson_plan_docx", {"size_bytes": 10}, 5
    )
    db_session.commit()

    events = db_session.query(TraceEvent).order_by(TraceEvent.created_at).all()
    model_event, tool_event = events
    assert model_event.prompt_tokens == 120 and model_event.completion_tokens == 340
    assert model_event.cost_usd == expected
    assert model_event.model is not None and ":" in model_event.model
    assert tool_event.prompt_tokens is None and tool_event.cost_usd is None
    assert tool_event.model is None


# --- TS-001: inventory across five kinds --------------------------------


def test_inventory_covers_all_five_kinds_with_metrics(client, auth):
    project_id = _full_run_project(client, auth)
    inventory = client.get(f"/projects/{project_id}/evidence", headers=auth)
    assert inventory.status_code == 200
    kinds = {run["kind"] for run in inventory.json()["runs"]}
    assert kinds == {"discovery", "planning", "lesson_plan", "slide_deck", "exercise"}
    for run in inventory.json()["runs"]:
        assert run["status"]
        assert run["cursor"] and "|" in run["cursor"]
        assert "cost_usd_estimated" in run and "model_calls" in run
    generation = next(r for r in inventory.json()["runs"] if r["kind"] == "lesson_plan")
    assert generation["model_call_cap"] is not None
    assert generation["total_count"] == 6 and generation["complete_count"] == 6
    assert generation["brief_version"] == 1 and generation["blueprint_version"] == 1


def test_inventory_empty_project_returns_empty_list(client, auth):
    project = client.post("/projects", json={"name": "空"}, headers=auth).json()
    inventory = client.get(f"/projects/{project['id']}/evidence", headers=auth)
    assert inventory.status_code == 200
    assert inventory.json() == {"runs": [], "next_cursor": None}


# --- TS-002: layer-1 summary --------------------------------------------


def test_summary_generation_run_is_version_bound_and_teacher_readable(client, auth):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    summary = client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}", headers=auth
    )
    assert summary.status_code == 200
    data = summary.json()
    assert data["kind"] == "lesson_plan" and data["status"] == "complete"
    assert data["brief_version"] == 1 and data["blueprint_version"] == 1
    assert data["model_calls"] >= 1 and data["model_call_cap"] >= data["model_calls"]
    assert data["complete_count"] == 6 and data["total_count"] == 6
    assert len(data["artifacts"]) == 6
    assert all(
        "status" in artifact and "failure_reason" in artifact
        for artifact in data["artifacts"]
    )
    assert data["recovery_view"] is None  # complete run needs no recovery pointer
    assert data["model_latency_ms_total"] >= 0
    assert data["evidence_kinds"]


def test_summary_partial_failure_and_recovery_pointer(client, auth, db_session):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    run = db_session.get(GenerationRun, uuid.UUID(run_ids["lesson_plan"]))
    run.status = "partial_failure"
    artifact = run_service.artifacts_of(db_session, run.id)[0]
    artifact.status = "failed"
    artifact.failure_reason = "provider unavailable"
    db_session.commit()

    summary = client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}", headers=auth
    ).json()
    assert summary["status"] == "partial_failure"
    failed = [a for a in summary["artifacts"] if a["status"] == "failed"]
    assert failed and failed[0]["failure_reason"] == "provider unavailable"
    assert summary["recovery_view"] == "generation"


def test_summary_superseded_run_names_newer_version(client, auth, db_session):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    project = db_session.get(Project, uuid.UUID(project_id))

    current = run_service.current_brief_version(db_session, uuid.UUID(project_id))
    newer = BriefVersion(
        project_id=project.id,
        workspace_id=project.workspace_id,
        version=current.version + 1,
        source_revision=current.source_revision + 1,
        fields_json=current.fields_json,
    )
    db_session.add(newer)
    run = db_session.get(GenerationRun, uuid.UUID(run_ids["lesson_plan"]))
    run.status = "superseded"
    db_session.commit()

    summary = client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}", headers=auth
    ).json()
    assert summary["status"] == "superseded"
    assert summary["superseded_by"]["brief_version"] == newer.version


def test_summary_discovery_and_planning_cover_interviews(client, auth):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    for kind in ("discovery", "planning"):
        summary = client.get(
            f"/projects/{project_id}/evidence/{run_ids[kind]}", headers=auth
        )
        assert summary.status_code == 200
        data = summary.json()
        assert data["kind"] == kind
        assert data["interview_message_count"] is not None
        assert data["model_call_cap"] is None


# --- TS-003: events pagination, merge, filter, stability ----------------


def test_events_pagination_no_gaps_or_duplicates_with_concurrent_append(
    client, auth, db_session
):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events"

    seen: list[str] = []
    after = None
    while True:
        query = f"{url}?limit=3" + (f"&after={after}" if after else "")
        page = client.get(query, headers=auth)
        assert page.status_code == 200, page.text
        body = page.json()
        seen.extend(event["cursor"] for event in body["events"])
        if body["next_cursor"] is None:
            break
        after = body["next_cursor"]

    assert len(seen) == len(set(seen)), "duplicate cursors across pages"
    assert len(seen) >= 6 * 4, "expected model+tool+lesson events for six lessons"

    # Concurrent append: a new event lands on the next page exactly once.
    first = client.get(f"{url}?limit=3", headers=auth).json()
    record_trace(db_session, run_ids["lesson_plan"], "model.late_event", {"prompt": {}}, 9)
    db_session.commit()
    second = client.get(
        f"{url}?limit=200&after={first['events'][-1]['cursor']}", headers=auth
    ).json()
    late = [event for event in second["events"] if event["event_type"] == "model.late_event"]
    assert len(late) == 1
    assert second["next_cursor"] is None or len(second["events"]) == 200


def test_events_kind_filter_and_merged_sources(client, auth):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events"

    filtered = client.get(f"{url}?kind=model.generation_write_lesson", headers=auth).json()
    assert filtered["events"]
    assert all(
        event["event_type"] == "model.generation_write_lesson" for event in filtered["events"]
    )
    sources = {event["source"] for event in client.get(url, headers=auth).json()["events"]}
    assert sources == {"trace", "run_event"}

    # Narration targets the project's latest interview run (planning here, per
    # the established F002-era selection); its messages must surface as interview
    # rounds in the same evidence structure.
    planning_url = f"/projects/{project_id}/evidence/{run_ids['planning']}/events"
    narrated = client.post(
        f"/projects/{project_id}/discovery/narrate",
        json={"text": "证据访谈叙述。"},
        headers=auth,
    )
    assert narrated.status_code == 202
    planning_events = []
    for _ in range(50):
        planning_events = client.get(planning_url, headers=auth).json()["events"]
        if any(event["source"] == "interview" for event in planning_events):
            break
        time.sleep(0.1)
    planning_sources = {event["source"] for event in planning_events}
    assert "interview" in planning_sources
    interview = [
        event for event in planning_events if event["source"] == "interview"
    ]
    assert interview and interview[0]["payload"]["role"]


def test_events_row_metrics_and_payloads(client, auth):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events"
    events = client.get(url, headers=auth).json()["events"]
    model_rows = [
        event for event in events if event["event_type"].startswith("model.")
    ]
    assert model_rows
    for row in model_rows:
        assert row["model"].startswith("fake:")
        assert row["prompt_tokens"] is not None
        assert row["cost_usd"] is not None  # estimate recorded for post-F006 events
        assert row["latency_ms"] is not None
        assert "payload" in row and "prompt" in row["payload"]
    lesson_rows = [event for event in events if event["event_type"] == "lesson"]
    assert lesson_rows and lesson_rows[0]["lesson_index"] is not None


# --- TS-004: legacy gaps stay explicit -----------------------------------


def test_legacy_events_show_explicit_gaps_without_status_distortion(
    client, auth, db_session
):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    # Wipe token data to simulate pre-F006 rows, keep a stale stored cost.
    db_session.query(TraceEvent).filter(
        TraceEvent.run_id == uuid.UUID(run_ids["lesson_plan"])
    ).update(
        {"prompt_tokens": None, "completion_tokens": None, "model": None, "cost_usd": 0.0}
    )
    db_session.commit()

    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}"
    events = client.get(f"{url}/events", headers=auth).json()["events"]
    model_rows = [event for event in events if event["event_type"].startswith("model.")]
    assert model_rows
    for row in model_rows:
        assert row["prompt_tokens"] is None
        assert row["cost_usd"] is None  # never zero-masked
    summary = client.get(url, headers=auth).json()
    assert "token_usage_not_recorded" in summary["telemetry_gaps"]
    assert "model_not_recorded" in summary["telemetry_gaps"]
    assert summary["status"] == "complete"  # authoritative status unchanged


# --- TS-006: authorization -----------------------------------------------


def test_authorization_non_disclosing_on_every_surface(
    client, auth, teacher_b_token
):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    run_id = run_ids["lesson_plan"]
    other = {"Authorization": f"Bearer {teacher_b_token}"}

    for path, method in (
        (f"/projects/{project_id}/evidence", "get"),
        (f"/projects/{project_id}/evidence/{run_id}", "get"),
        (f"/projects/{project_id}/evidence/{run_id}/events", "get"),
        (f"/projects/{project_id}/evidence/{run_id}/narrate", "post"),
        (f"/projects/{project_id}/evidence/{run_id}/narrate/stream", "get"),
    ):
        denied = getattr(client, method)(path, headers=other)
        assert denied.status_code in (401, 404), (path, denied.status_code)
    unauthenticated = client.get(f"/projects/{project_id}/evidence")
    assert unauthenticated.status_code == 401
    foreign = client.get(
        f"/projects/{project_id}/evidence/{uuid.uuid4()}", headers=auth
    )
    assert foreign.status_code == 404
    assert "prompt" not in foreign.text


# --- TS-007: read-only invariance ----------------------------------------


def test_evidence_interactions_change_no_business_state(client, auth, db_session):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    project_uuid = uuid.UUID(project_id)

    def state_snapshot():
        session = SessionLocal()
        try:
            run = (
                session.query(GenerationRun)
                .filter_by(project_id=project_uuid, artifact_kind="lesson_plan")
                .one()
            )
            return (
                run.status,
                run.model_calls,
                tuple(
                    (a.lesson_index, a.status, a.retry_count)
                    for a in run_service.artifacts_of(session, run.id)
                ),
                session.query(BriefVersion).filter_by(project_id=project_uuid).count(),
            )
        finally:
            session.close()

    before = state_snapshot()
    client.get(f"/projects/{project_id}/evidence", headers=auth)
    client.get(f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}", headers=auth)
    client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events?limit=2",
        headers=auth,
    )
    client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events"
        "?kind=model.generation_write_lesson",
        headers=auth,
    )
    narrate = client.post(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/narrate", headers=auth
    )
    assert narrate.status_code == 202
    stop = client.post(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/narrate/stop",
        headers=auth,
    )
    assert stop.status_code == 200
    after = state_snapshot()
    assert before == after


# --- TS-009: narration lifecycle ------------------------------------------


class _SlowStreamAdapter:
    """Deterministic narration timing: enough tokens, slow enough that stop and
    duplicate-start land while the narration is still active."""

    def stream(self, system, user):
        for index in range(60):
            time.sleep(0.02)
            yield f"片段{index}。"

    def complete(self, system, user):
        raise AssertionError("evidence narration never calls complete()")


def _install_slow_narration(monkeypatch):
    import lessoncanvas.adapters.model as model_module

    monkeypatch.setattr(model_module, "get_model_adapter", lambda: _SlowStreamAdapter())


def _wait_for_narration_recorded(db_session, run_id, timeout_s: float = 10.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rows = db_session.query(TraceEvent).filter_by(
            run_id=uuid.UUID(run_id), event_type="model.evidence_narration"
        ).all()
        if rows:
            return rows[0]
        time.sleep(0.1)
    return None


def test_narration_streams_records_and_enforces_workspace_quota(
    client, auth, db_session, monkeypatch
):
    _install_slow_narration(monkeypatch)
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    run_id = run_ids["lesson_plan"]
    url = f"/projects/{project_id}/evidence/{run_id}"

    started = client.post(f"{url}/narrate", headers=auth)
    assert started.status_code == 202
    duplicate = client.post(f"{url}/narrate", headers=auth)
    assert duplicate.status_code == 202  # idempotent while active

    counter = db_session.query(QuotaCounter).filter_by(
        key="evidence_narration"
    ).one_or_none()
    assert counter is not None and counter.used == 1  # duplicate start did not double-reserve

    stream = client.get(f"{url}/narrate/stream", headers=auth)
    assert stream.status_code == 200
    assert "event: token" in stream.text and "event: complete" in stream.text

    recorded = _wait_for_narration_recorded(db_session, run_id)
    assert recorded is not None
    assert json.loads(recorded.payload_json)["response"]
    run = db_session.get(GenerationRun, uuid.UUID(run_id))
    assert run.status == "complete"  # narration changed nothing

    db_session.refresh(counter)
    counter.used = counter.limit
    db_session.commit()
    exhausted = client.post(f"{url}/narrate", headers=auth)
    assert exhausted.status_code == 429
    assert exhausted.json()["error"]["code"] == "QUOTA_EXCEEDED"
    # Recorded evidence stays readable at quota exhaustion.
    still = client.get(f"{url}/events", headers=auth)
    assert still.status_code == 200


def test_narration_stop_returns_stopped_event(client, auth, monkeypatch):
    _install_slow_narration(monkeypatch)
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}"
    assert client.post(f"{url}/narrate", headers=auth).status_code == 202
    stopped = client.post(f"{url}/narrate/stop", headers=auth)
    assert stopped.status_code == 200 and stopped.json()["stopped"] is True
    stream = client.get(f"{url}/narrate/stream", headers=auth)
    assert "event: stopped" in stream.text


def test_narration_stream_falls_back_to_last_recorded_text(client, auth):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}"
    assert client.post(f"{url}/narrate", headers=auth).status_code == 202
    for _ in range(50):
        if evidence.get_evidence_narration(run_ids["lesson_plan"]) is None:
            break
        time.sleep(0.1)
    stream = client.get(f"{url}/narrate/stream", headers=auth)
    assert "event: complete" in stream.text


# --- TS-012: query validation --------------------------------------------


def test_events_reject_malformed_cursor_and_unknown_kind(client, auth):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    url = f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events"

    bad_cursor = client.get(f"{url}?after=not-a-cursor", headers=auth)
    assert bad_cursor.status_code == 422
    assert bad_cursor.json()["error"]["code"] == "REQUIREMENT"

    unknown_kind = client.get(f"{url}?kind=does.not_exist", headers=auth)
    assert unknown_kind.status_code == 422

    bounded = client.get(f"{url}?limit=1", headers=auth)
    assert bounded.status_code == 200 and len(bounded.json()["events"]) == 1


# --- TS-023: SSE keepalive during idle gaps (F003 early-drop root cause) ----


def test_generation_stream_emits_keepalive_during_idle_gaps(client, auth, db_session):
    """A queued run with no events appended must still produce wire traffic:
    an SSE comment keepalive every STREAM_KEEPALIVE_SECONDS so idle-timeout
    intermediaries cannot drop the stream mid-run."""

    import time as time_module

    from lessoncanvas.api.generation import STREAM_KEEPALIVE_SECONDS

    project_id = _confirmed_blueprint_project(client, auth)
    project_uuid = uuid.UUID(project_id)
    workspace_id = db_session.get(Project, project_uuid).workspace_id
    run, _ = run_service.start_generation(db_session, workspace_id, project_uuid)
    db_session.commit()  # created directly: no dispatch, so the run stays idle

    received = ""
    deadline = time_module.monotonic() + STREAM_KEEPALIVE_SECONDS + 6.0
    with client.stream(
        "GET", f"/projects/{project_id}/generation/events", headers=auth
    ) as response:
        for chunk in response.iter_text():
            received += chunk
            if ": keepalive" in received:
                break
            if time_module.monotonic() > deadline:
                break
    assert ": keepalive" in received
    # Keepalives are comment frames: they never carry id/data payloads.
    keepalive_frames = [f for f in received.split("\n\n") if ": keepalive" in f]
    assert keepalive_frames
    assert all("data:" not in frame for frame in keepalive_frames)


# --- TS-013: legacy endpoint removed -------------------------------------


def test_legacy_trace_endpoint_is_removed(client, auth):
    project = client.post("/projects", json={"name": "旧端点"}, headers=auth).json()
    gone = client.get(f"/projects/{project['id']}/trace", headers=auth)
    assert gone.status_code == 404
    assert gone.json().get("detail") is not None  # route miss, not our error body


# --- TS-015: payloads stay inert data -------------------------------------


def test_injection_payloads_ride_as_inert_json(client, auth, db_session):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    marker = "<script>alert('grant tool access')</script>"
    record_trace(
        db_session,
        run_ids["lesson_plan"],
        "model.injection_probe",
        {"prompt": {"injected": marker}, "response": {"echo": marker}},
        10,
    )
    db_session.commit()

    events = client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events",
        headers=auth,
    ).json()["events"]
    probe = next(event for event in events if event["event_type"] == "model.injection_probe")
    assert probe["payload"]["prompt"]["injected"] == marker  # inert JSON string value
    bad = client.get(
        f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}/events?after=<<<",
        headers=auth,
    )
    assert bad.status_code == 422 and marker not in bad.text


# --- TS-008: deletion removes evidence surfaces ---------------------------


def test_project_deletion_removes_evidence_surfaces(client, auth, db_session):
    project_id = _full_run_project(client, auth)
    run_ids = _run_ids(client, auth, project_id)
    deleted = client.delete(f"/projects/{project_id}", headers=auth)
    assert deleted.status_code in (200, 204)
    assert (
        client.get(f"/projects/{project_id}/evidence", headers=auth).status_code == 404
    )
    assert (
        client.get(
            f"/projects/{project_id}/evidence/{run_ids['lesson_plan']}", headers=auth
        ).status_code
        == 404
    )
    remaining = db_session.query(TraceEvent).filter_by(
        run_id=uuid.UUID(run_ids["lesson_plan"])
    ).count()
    assert remaining == 0

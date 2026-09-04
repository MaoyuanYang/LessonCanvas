"""F015 TS-009/TS-010/TS-011: planning drafting bound to the bounded tool loop."""

import json

from lessoncanvas.settings import get_settings
from test_planning import PLANNING_CORPUS, confirmed_project, run_planning_to_draft


def _planning_events(client, auth, project_id) -> list[dict]:
    inventory = client.get(f"/projects/{project_id}/evidence", headers=auth).json()
    planning_run = next(run for run in inventory["runs"] if run["kind"] == "planning")
    events = client.get(
        f"/projects/{project_id}/evidence/{planning_run['run_id']}/events", headers=auth
    ).json()
    return events["events"]


def _draft_model_events(events) -> list[dict]:
    return [event for event in events if event["event_type"] == "model.planning_build_draft"]


def test_ts010_model_driven_loop_self_requests_standards_and_keeps_contract(client, auth):
    assert get_settings().tool_loop_mode == "model_driven"
    project_id = confirmed_project(client, auth)
    status = run_planning_to_draft(client, auth, project_id)

    # Final blueprint contract unchanged (AC-001)
    draft = status["draft"]
    assert set(draft.keys()) == {"unit", "lessons", "findings"}
    assert draft["unit"]["objectives"] and draft["lessons"]

    events = _planning_events(client, auth, project_id)
    requests = [event for event in events if event["event_type"] == "tool.request"]
    results = [event for event in events if event["event_type"] == "tool.result"]
    assert requests, "the specialist must have self-requested a tool round"
    first_request = json.loads(json.dumps(requests[0]["payload"]))
    assert first_request["tool_calls"][0]["name"] == "search_curriculum_standards"
    assert first_request["round"] == 0
    assert results and json.loads(json.dumps(results[0]["payload"]))["outcome"] == "dispatched"

    # Standards enter the conversation only via the model's own rounds: the
    # drafting payload never carries a pre-injected standards key.
    model_event = _draft_model_events(events)[0]
    prompt = model_event["payload"]["prompt"]
    assert "standards" not in prompt
    assert model_event["payload"]["tool_rounds"], "final event must attribute its rounds"

    # Standards citations still exist (tool results merge into grounding)
    first_objective = draft["unit"]["objectives"][0]
    assert any(
        citation.get("type") == "standards"
        for citation in first_objective.get("citations", [])
    )


def test_ts009_direct_answer_without_tool_use_is_honest(client, auth, db_session):
    corpus = PLANNING_CORPUS.replace("人与自然", "TOOL_DIRECT 人与自然")
    project_id = confirmed_project(client, auth, corpus)
    status = run_planning_to_draft(client, auth, project_id)

    assert status["status"] == "draft_ready"
    assert set(status["draft"].keys()) == {"unit", "lessons", "findings"}

    events = _planning_events(client, auth, project_id)
    assert not [event for event in events if event["event_type"].startswith("tool.request")]
    assert not [event for event in events if event["event_type"] == "tool.result"]
    assert _draft_model_events(events)


def test_ts010_fallback_completes_with_disclosure_when_loop_never_finalizes(client, auth):
    corpus = PLANNING_CORPUS.replace("人与自然", "TOOL_LOOP_FOREVER 人与自然")
    project_id = confirmed_project(client, auth, corpus)
    status = run_planning_to_draft(client, auth, project_id)

    # Deterministic fallback completed the stage: never worse than baseline
    assert status["status"] == "draft_ready"
    assert set(status["draft"].keys()) == {"unit", "lessons", "findings"}

    events = _planning_events(client, auth, project_id)
    event_types = {event["event_type"] for event in events}
    assert "tool.fallback" in event_types
    assert "tool.standards_search" in event_types  # orchestration-issued search ran
    fallback = next(event for event in events if event["event_type"] == "tool.fallback")
    assert fallback["payload"]["reason"] == "round_cap_exhausted"
    # Exactly the capped rounds + one fallback call; nothing past the cap
    requests = [event for event in events if event["event_type"] == "tool.request"]
    assert len(requests) == get_settings().tool_loop_max_rounds


def test_ts011_orchestration_mode_reproduces_pre_f015_behavior(client, auth, monkeypatch):
    monkeypatch.setenv("LESSONCANVAS_TOOL_LOOP_MODE", "orchestration")
    get_settings.cache_clear()
    try:
        project_id = confirmed_project(client, auth)
        status = run_planning_to_draft(client, auth, project_id)
    finally:
        monkeypatch.delenv("LESSONCANVAS_TOOL_LOOP_MODE")
        get_settings.cache_clear()

    assert set(status["draft"].keys()) == {"unit", "lessons", "findings"}
    events = _planning_events(client, auth, project_id)
    event_types = {event["event_type"] for event in events}
    assert "tool.standards_search" in event_types
    assert not any(event_type.startswith("tool.request") for event_type in event_types)
    assert "tool.fallback" not in event_types

    # Pre-F015 payload shape: standards pre-injected, single drafting call
    model_event = _draft_model_events(events)[0]
    assert "standards" in model_event["payload"]["prompt"]
    assert "tool_rounds" not in model_event["payload"]

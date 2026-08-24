import threading

from sqlalchemy import func, select

from lessoncanvas.models import InteractionMessage, TraceEvent


def create_project(client, auth) -> str:
    response = client.post("/projects", json={"name": "流式测试"}, headers=auth)
    assert response.status_code == 201
    return response.json()["id"]


def start_run(client, auth, project_id) -> None:
    response = client.post(f"/projects/{project_id}/discovery/start", headers=auth)
    assert response.status_code == 200


def read_sse(client, url, headers, max_events=500):
    events = []
    with client.stream("GET", url, headers=headers) as response:
        current_event = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                current_event = line[len("event: ") :]
            elif line.startswith("data: "):
                events.append((current_event, line[len("data: ") :]))
                if len(events) >= max_events or current_event in ("complete", "stopped"):
                    break
    return events


def test_narration_streams_to_completion_with_trace(client, auth):
    project_id = create_project(client, auth)
    start_run(client, auth, project_id)
    narrated = client.post(
        f"/projects/{project_id}/discovery/narrate",
        json={"text": "接下来请补充教学目标与学情信息。"},
        headers=auth,
    )
    assert narrated.status_code == 202

    events = read_sse(client, f"/projects/{project_id}/discovery/stream", auth)
    kinds = [kind for kind, _ in events]
    assert kinds[-1] == "complete"
    token_text = "".join(
        __import__("json").loads(data)["t"] for kind, data in events if kind == "token"
    )
    assert token_text == "接下来请补充教学目标与学情信息。"

    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    run_id = narrated.json()["run_id"]
    trace_count = session.scalar(
        select(func.count(TraceEvent.id)).where(
            TraceEvent.run_id == run_id, TraceEvent.event_type == "model.narration"
        )
    )
    message_count = session.scalar(
        select(func.count(InteractionMessage.id)).where(
            InteractionMessage.run_id == run_id, InteractionMessage.role == "agent"
        )
    )
    session.close()
    assert trace_count == 1
    assert message_count >= 1


def test_stop_does_not_cancel_and_reconnect_replays(client, auth, monkeypatch):
    from lessoncanvas.modules.discovery_planning import narration as narration_module

    release = threading.Event()

    class BlockingFake:
        def stream(self, system, user):
            yield "第一部分。"
            release.wait(5)
            yield "第二部分完整结束。"

    monkeypatch.setattr(narration_module, "get_model_adapter", lambda: BlockingFake())

    project_id = create_project(client, auth)
    start_run(client, auth, project_id)
    narrated = client.post(
        f"/projects/{project_id}/discovery/narrate", json={"text": "x"}, headers=auth
    )
    assert narrated.status_code == 202
    run_id = narrated.json()["run_id"]

    stopped = client.post(f"/projects/{project_id}/discovery/stop-narration", headers=auth)
    assert stopped.status_code == 200
    assert stopped.json()["stopped"] is True

    release.set()

    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    trace = None
    for _ in range(50):
        trace = session.scalar(
            select(TraceEvent).where(
                TraceEvent.run_id == run_id, TraceEvent.event_type == "model.narration"
            )
        )
        if trace is not None:
            break
        import time

        time.sleep(0.1)
    session.close()
    assert trace is not None, "model call must complete despite stop"
    assert "第二部分完整结束。" in trace.payload_json

    events = read_sse(client, f"/projects/{project_id}/discovery/stream", auth)
    kinds = [kind for kind, _ in events]
    assert "token" in kinds
    assert kinds[-1] == "stopped"


def test_reconnect_without_live_state_replays_persisted_text(client, auth):
    project_id = create_project(client, auth)
    start_run(client, auth, project_id)
    narrated = client.post(
        f"/projects/{project_id}/discovery/narrate", json={"text": "重连测试文本。"}, headers=auth
    )
    run_id = narrated.json()["run_id"]

    import time

    for _ in range(50):
        events = read_sse(client, f"/projects/{project_id}/discovery/stream", auth)
        if [k for k, _ in events][-1:] == ["complete"]:
            break
        time.sleep(0.1)

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import DiscoveryRun

    session = SessionLocal()
    calls_before = session.get(DiscoveryRun, run_id).model_calls
    session.close()

    narration_module_state = __import__(
        "lessoncanvas.modules.discovery_planning.narration", fromlist=["x"]
    )
    narration_module_state._narrations.clear()

    events = read_sse(client, f"/projects/{project_id}/discovery/stream?offset=0", auth)
    kinds = [kind for kind, _ in events]
    assert kinds[-1] == "complete"

    session = SessionLocal()
    calls_after = session.get(DiscoveryRun, run_id).model_calls
    session.close()
    assert calls_after == calls_before


def test_reask_counts_new_model_call(client, auth):
    project_id = create_project(client, auth)
    start_run(client, auth, project_id)
    narrated = client.post(
        f"/projects/{project_id}/discovery/narrate", json={"text": "a"}, headers=auth
    )
    run_id = narrated.json()["run_id"]

    import time

    time.sleep(0.3)
    reasked = client.post(
        f"/projects/{project_id}/discovery/reask", json={"text": "b"}, headers=auth
    )
    assert reasked.status_code == 202

    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import DiscoveryRun

    session = SessionLocal()
    run = session.get(DiscoveryRun, run_id)
    calls = run.model_calls
    session.close()
    assert calls >= 2

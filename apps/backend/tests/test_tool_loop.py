"""F015 TS-003..TS-008/TS-018: bounded tool-loop primitive behavior."""

import json
import uuid

from sqlalchemy import select

from lessoncanvas.adapters.model import ModelResponse, ToolCall
from lessoncanvas.models import DiscoveryRun, Project, TraceEvent, Workspace
from lessoncanvas.modules.discovery_planning.graph import record_trace
from lessoncanvas.modules.discovery_planning.tool_loop import run_tool_loop
from lessoncanvas.modules.sources_grounding.standards import STANDARDS_TOOL_DEFINITION

SECTIONS = [
    {"section_id": "sec-1", "title": "阅读素养", "text": "发展阅读策略……", "snapshot_version": "v1"}
]


def _make_run(db_session) -> DiscoveryRun:
    workspace = Workspace(subject=f"loop-{uuid.uuid4().hex}")
    db_session.add(workspace)
    db_session.flush()
    project = Project(workspace_id=workspace.id, name="循环测试")
    db_session.add(project)
    db_session.flush()
    run = DiscoveryRun(project_id=project.id, workspace_id=workspace.id, kind="planning")
    db_session.add(run)
    db_session.commit()
    return run


def _events(db_session, run) -> list[TraceEvent]:
    return list(
        db_session.scalars(
            select(TraceEvent).where(TraceEvent.run_id == run.id).order_by(TraceEvent.created_at)
        )
    )


class StubDispatch:
    """Records every dispatch attempt; refuses to run anything unvalidated."""

    def __init__(self, fail_names: set[str] | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.fail_names = fail_names or set()

    def __call__(self, name: str, arguments: dict):
        self.calls.append((name, dict(arguments)))
        if name in self.fail_names:
            raise RuntimeError("tool exploded")
        return [dict(section) for section in SECTIONS]


def _run_loop(db_session, run, theme: str, dispatch, **payload_extra):
    user = json.dumps(
        {
            "kind": "planning_build_draft",
            "brief": {"unit_theme": theme, "lesson_count": "2", "teaching_objectives": "阅读"},
            "known": {},
            **payload_extra,
        },
        ensure_ascii=False,
    )
    db_session.refresh(run)
    return run_tool_loop(
        session=db_session,
        run=run,
        system="planning specialist",
        user=user,
        tools=[STANDARDS_TOOL_DEFINITION],
        dispatch=dispatch,
        record_trace_fn=record_trace,
        run_id=str(run.id),
    )


def test_ts003_happy_path_rounds_traced_and_billed_once_each(db_session):
    run = _make_run(db_session)
    dispatch = StubDispatch()

    result = _run_loop(db_session, run, "文化遗产", dispatch)

    assert result.data is not None and "blueprint" in result.data
    assert result.fallback_reason is None
    assert run.model_calls == 2  # one tool round + one final answer
    names = [call[0] for call in dispatch.calls]
    assert names == ["search_curriculum_standards"]

    events = _events(db_session, run)
    by_type: dict[str, list[TraceEvent]] = {}
    for event in events:
        by_type.setdefault(event.event_type, []).append(event)
    # One request round; the final direct answer traces no tool event
    assert len(by_type["tool.request"]) == 1
    assert len(by_type["tool.result"]) == 1
    result_event = by_type["tool.result"][0]
    payload = json.loads(result_event.payload_json)
    assert payload["outcome"] == "dispatched" and payload["result_count"] == 1
    assert payload["round"] == 0
    request_event = by_type["tool.request"][0]
    request_payload = json.loads(request_event.payload_json)
    assert request_payload["tool_calls"][0]["name"] == "search_curriculum_standards"
    # Round model calls carry usage so per-round cost is visible (TS-014 basis)
    assert request_event.prompt_tokens and request_event.prompt_tokens > 0
    assert request_event.completion_tokens and request_event.completion_tokens > 0
    assert request_event.cost_usd is not None


def test_ts004_unknown_tool_refused_then_model_corrects(db_session):
    run = _make_run(db_session)
    dispatch = StubDispatch()

    result = _run_loop(db_session, run, "TOOL_UNKNOWN 单元", dispatch)

    assert result.data is not None
    refused = [
        event for event in _events(db_session, run) if event.event_type == "tool.refused"
    ]
    assert len(refused) == 1
    payload = json.loads(refused[0].payload_json)
    assert payload["name"] == "render_lesson_plan_docx"
    assert "whitelist" in payload["reason"]
    # The unbound name never reached dispatch; the corrected round did
    assert all(name == "search_curriculum_standards" for name, _ in dispatch.calls)
    assert len(dispatch.calls) == 1


def test_ts005_malformed_arguments_refused_per_class(db_session):
    for mode, expected_reason in (
        ("missing_query", "missing required argument: query"),
        ("wrong_type", "argument query must be a string"),
        ("non_object", "arguments must be a JSON object"),
    ):
        run = _make_run(db_session)
        dispatch = StubDispatch()

        result = _run_loop(db_session, run, "TOOL_BAD_ARGS 单元", dispatch, tool_args_mode=mode)

        assert result.data is not None, mode
        refused = [
            event for event in _events(db_session, run) if event.event_type == "tool.refused"
        ]
        assert len(refused) == 1, mode
        assert json.loads(refused[0].payload_json)["reason"] == expected_reason, mode
        # The malformed round never reached dispatch; after the corrective
        # observation the model re-requested with valid arguments (D2).
        assert len(dispatch.calls) == 1, mode
        name, arguments = dispatch.calls[0]
        assert name == "search_curriculum_standards" and isinstance(arguments.get("query"), str)


def test_ts006_mid_loop_tool_failure_traced_and_loop_bounded(db_session):
    run = _make_run(db_session)
    dispatch = StubDispatch(fail_names={"search_curriculum_standards"})

    result = _run_loop(db_session, run, "文化遗产", dispatch)

    # Failure observations are not sections, so the scripted model keeps
    # requesting; the cap bounds the loop and the caller must fall back.
    assert result.data is None
    assert result.fallback_reason == "round_cap_exhausted"
    events = _events(db_session, run)
    failed = [
        json.loads(event.payload_json)
        for event in events
        if event.event_type == "tool.result"
    ]
    assert failed and all(item["outcome"] == "failed" for item in failed)
    assert failed[0]["error"] == "RuntimeError"
    assert len(dispatch.calls) == 5


def test_ts007_round_cap_exhaustion_never_rebills(db_session):
    run = _make_run(db_session)
    dispatch = StubDispatch()

    result = _run_loop(db_session, run, "TOOL_LOOP_FOREVER 单元", dispatch)

    assert result.data is None
    assert result.fallback_reason == "round_cap_exhausted"
    assert run.model_calls == 5
    assert len(dispatch.calls) == 5
    requests = [
        event for event in _events(db_session, run) if event.event_type == "tool.request"
    ]
    assert len(requests) == 5
    assert [json.loads(event.payload_json)["round"] for event in requests] == [0, 1, 2, 3, 4]


def test_ts008_final_json_wins_over_pending_requests(db_session, monkeypatch):
    run = _make_run(db_session)
    dispatch = StubDispatch()

    class BothAtOnceAdapter:
        def complete(self, system, user, tools=None, history=None):
            return ModelResponse(
                text=json.dumps({"blueprint": {"unit": {"title": "x"}, "lessons": []}}),
                prompt_tokens=5,
                completion_tokens=5,
                tool_calls=[
                    ToolCall(
                        id="call-1", name="search_curriculum_standards", arguments={"query": "q"}
                    )
                ],
            )

    import lessoncanvas.adapters.model as model_module

    monkeypatch.setattr(model_module, "get_model_adapter", lambda: BothAtOnceAdapter())

    user = json.dumps(
        {
            "kind": "planning_build_draft",
            "brief": {"unit_theme": "文化遗产", "lesson_count": "1"},
            "known": {},
        },
        ensure_ascii=False,
    )
    result = run_tool_loop(
        session=db_session,
        run=run,
        system="s",
        user=user,
        tools=[STANDARDS_TOOL_DEFINITION],
        dispatch=dispatch,
        record_trace_fn=record_trace,
        run_id=str(run.id),
    )

    assert result.data is not None
    assert dispatch.calls == []  # pending request dropped, never dispatched
    # One billed call, one ledger event: the dropped request rides the result
    # (disclosed by the caller's final model event), never a second event.
    assert _events(db_session, run) == []
    assert result.dropped_tool_calls == [
        {"id": "call-1", "name": "search_curriculum_standards", "arguments": {"query": "q"}}
    ]


def test_ts018_run_model_call_cap_stops_loop_before_overflow(db_session):
    run = _make_run(db_session)
    run.model_calls = 19  # one round of headroom under max_model_calls_per_run=20
    db_session.commit()
    dispatch = StubDispatch()

    result = _run_loop(db_session, run, "TOOL_LOOP_FOREVER 单元", dispatch)

    assert result.data is None
    assert result.fallback_reason == "run_model_call_cap"
    assert run.model_calls == 20  # exactly at the cap, never past it
    assert len(dispatch.calls) == 1

    exhausted = _make_run(db_session)
    exhausted.model_calls = 20
    db_session.commit()
    immediate = _run_loop(db_session, exhausted, "文化遗产", StubDispatch())
    assert immediate.fallback_reason == "run_model_call_cap"
    assert exhausted.model_calls == 20

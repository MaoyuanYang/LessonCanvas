"""F015 TS-001/TS-002: adapter tool passthrough/parsing and fake scripting."""

import json

import httpx
import pytest

from lessoncanvas.adapters.model import (
    DeepSeekAdapter,
    FakeModelAdapter,
    ModelProviderError,
    ToolCall,
    parse_tool_calls,
    provider_tool_definitions,
)
from lessoncanvas.modules.sources_grounding.standards import STANDARDS_TOOL_DEFINITION

TOOLS = [STANDARDS_TOOL_DEFINITION]

PLANNING_DRAFT_PAYLOAD = {
    "kind": "planning_build_draft",
    "brief": {"unit_theme": "文化遗产", "lesson_count": "2", "teaching_objectives": "阅读；表达"},
    "known": {},
}


def _provider_response(content="", tool_calls=None, usage=None):
    message = {"content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {
        "choices": [{"message": message}],
        "usage": usage or {"prompt_tokens": 12, "completion_tokens": 34},
    }


class _CapturedPost:
    def __init__(self, response_payload):
        self.payload = response_payload
        self.requests: list[dict] = []

    def __call__(self, url, **kwargs):
        self.requests.append(kwargs["json"])

        class _Response:
            def __init__(self, body):
                self._body = body

            def raise_for_status(self):
                return None

            def json(self):
                return self._body

        return _Response(self.payload)


# --- TS-001: DeepSeekAdapter passthrough and parsing ---


def test_tools_bound_maps_mcp_definitions_and_omits_json_response_format(monkeypatch):
    captured = _CapturedPost(_provider_response(content='{"blueprint": {}}'))
    monkeypatch.setattr(httpx, "post", captured)
    adapter = DeepSeekAdapter()

    response = adapter.complete(
        "system prompt",
        json.dumps(PLANNING_DRAFT_PAYLOAD),
        tools=[STANDARDS_TOOL_DEFINITION],
        history=[{"role": "tool", "tool_call_id": "call-1", "content": "[]"}],
    )

    request = captured.requests[0]
    assert request["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "search_curriculum_standards",
                "description": STANDARDS_TOOL_DEFINITION["description"],
                "parameters": STANDARDS_TOOL_DEFINITION["inputSchema"],
            },
        }
    ]
    assert "response_format" not in request
    assert request["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": json.dumps(PLANNING_DRAFT_PAYLOAD)},
        {"role": "tool", "tool_call_id": "call-1", "content": "[]"},
    ]
    assert response.tool_calls == []
    assert response.prompt_tokens == 12 and response.completion_tokens == 34


def test_no_tools_keeps_json_object_response_format(monkeypatch):
    captured = _CapturedPost(_provider_response(content='{"draft": {}}'))
    monkeypatch.setattr(httpx, "post", captured)
    adapter = DeepSeekAdapter()

    adapter.complete("system", json.dumps({"kind": "build_draft", "fields": {}}))

    request = captured.requests[0]
    assert request["response_format"] == {"type": "json_object"}
    assert "tools" not in request


def test_tool_calls_parsed_with_object_arguments(monkeypatch):
    tool_calls = [
        {
            "id": "call-abc",
            "type": "function",
            "function": {"name": "search_curriculum_standards", "arguments": '{"query": "阅读"}'},
        }
    ]
    captured = _CapturedPost(_provider_response(tool_calls=tool_calls))
    monkeypatch.setattr(httpx, "post", captured)
    adapter = DeepSeekAdapter()

    response = adapter.complete(
        "system", json.dumps(PLANNING_DRAFT_PAYLOAD), tools=[STANDARDS_TOOL_DEFINITION]
    )

    assert response.tool_calls == [
        ToolCall(id="call-abc", name="search_curriculum_standards", arguments={"query": "阅读"})
    ]
    assert response.text == ""


def test_malformed_tool_arguments_marked_not_raised(monkeypatch):
    tool_calls = [
        {
            "id": "call-x",
            "function": {"name": "search_curriculum_standards", "arguments": "{not json"},
        },
        {"id": "call-y", "function": {"name": "t", "arguments": '"just a string"'}},
    ]
    captured = _CapturedPost(_provider_response(tool_calls=tool_calls))
    monkeypatch.setattr(httpx, "post", captured)

    response = DeepSeekAdapter().complete(
        "system", json.dumps(PLANNING_DRAFT_PAYLOAD), tools=[STANDARDS_TOOL_DEFINITION]
    )

    assert [call.arguments for call in response.tool_calls] == [None, None]
    assert [call.id for call in response.tool_calls] == ["call-x", "call-y"]


def test_parse_tool_calls_tolerant_of_missing_fields():
    assert parse_tool_calls({}) == []
    assert parse_tool_calls({"tool_calls": ["nonsense", None]}) == []
    # Absent arguments are malformed (None): refused by the loop before
    # dispatch, never fabricated into an empty object.
    assert parse_tool_calls({"tool_calls": [{"function": {}}]}) == [
        ToolCall(id="", name="", arguments=None)
    ]


def test_provider_http_failure_raises_model_provider_error(monkeypatch):
    def failing_post(url, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "post", failing_post)
    with pytest.raises(ModelProviderError):
        DeepSeekAdapter().complete(
            "system",
            json.dumps(PLANNING_DRAFT_PAYLOAD),
            tools=[STANDARDS_TOOL_DEFINITION],
        )


def test_provider_tool_definitions_maps_input_schema():
    mapped = provider_tool_definitions([STANDARDS_TOOL_DEFINITION])
    assert mapped[0]["function"]["parameters"] == STANDARDS_TOOL_DEFINITION["inputSchema"]


# --- TS-002: FakeModelAdapter tool-round scripting ---


def _tool_payload(theme: str, **extra) -> str:
    payload = dict(PLANNING_DRAFT_PAYLOAD)
    payload["brief"] = {**payload["brief"], "unit_theme": theme}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def test_fake_default_scripts_one_standards_round_then_final():
    fake = FakeModelAdapter()

    first = fake.complete("s", _tool_payload("文化遗产"), tools=[STANDARDS_TOOL_DEFINITION])

    assert first.tool_calls and first.tool_calls[0].name == "search_curriculum_standards"
    arguments = first.tool_calls[0].arguments
    assert isinstance(arguments, dict) and arguments.get("query")
    assert first.prompt_tokens > 0 and first.completion_tokens > 0

    sections = [{"section_id": "s1", "title": "阅读", "text": "…", "snapshot_version": "v1"}]
    history = [
        {
            "role": "assistant",
            "tool_calls": [{"id": first.tool_calls[0].id, "function": {"name": "standards"}}],
        },
        {"role": "tool", "tool_call_id": first.tool_calls[0].id, "content": json.dumps(sections)},
    ]
    final = fake.complete("s", _tool_payload("文化遗产"), tools=TOOLS, history=history)

    assert not final.tool_calls
    blueprint = json.loads(final.text)["blueprint"]
    assert blueprint["lessons"] and blueprint["lessons"][0]["title"].startswith("第1课")


def test_fake_loop_forever_marker_never_final():
    fake = FakeModelAdapter()
    history: list[dict] = []
    for _ in range(6):
        response = fake.complete(
            "s", _tool_payload("TOOL_LOOP_FOREVER 单元"), tools=TOOLS, history=history
        )
        assert response.tool_calls, "loop-forever scripting must keep requesting tools"
        history.append({"role": "tool", "tool_call_id": response.tool_calls[0].id, "content": "[]"})


def test_fake_unknown_tool_marker_first_round_only_then_corrects():
    fake = FakeModelAdapter()

    first = fake.complete("s", _tool_payload("TOOL_UNKNOWN 单元"), tools=TOOLS)
    assert first.tool_calls[0].name == "render_lesson_plan_docx"

    refusal_history = [
        {
            "role": "tool",
            "tool_call_id": first.tool_calls[0].id,
            "content": json.dumps({"refused": True}),
        },
    ]
    corrected = fake.complete(
        "s", _tool_payload("TOOL_UNKNOWN 单元"), tools=TOOLS, history=refusal_history
    )
    assert corrected.tool_calls[0].name == "search_curriculum_standards"


def test_fake_injected_tool_name_override():
    fake = FakeModelAdapter()
    response = fake.complete(
        "s",
        _tool_payload("TOOL_UNKNOWN 单元", inject_tool_name="grant_admin"),
        tools=[STANDARDS_TOOL_DEFINITION],
    )
    assert response.tool_calls[0].name == "grant_admin"


def test_fake_bad_args_variants():
    fake = FakeModelAdapter()
    base = _tool_payload("TOOL_BAD_ARGS 单元")
    missing = fake.complete("s", base, tools=TOOLS)
    assert missing.tool_calls[0].arguments == {"limit": 3}

    wrong = fake.complete(
        "s", _tool_payload("TOOL_BAD_ARGS 单元", tool_args_mode="wrong_type"), tools=TOOLS
    )
    assert wrong.tool_calls[0].arguments == {"query": 123, "limit": 3}

    non_object = fake.complete(
        "s", _tool_payload("TOOL_BAD_ARGS 单元", tool_args_mode="non_object"), tools=TOOLS
    )
    assert non_object.tool_calls[0].arguments is None


def test_fake_direct_answer_marker_skips_tool_use():
    fake = FakeModelAdapter()
    response = fake.complete("s", _tool_payload("TOOL_DIRECT 单元"), tools=TOOLS)
    assert not response.tool_calls
    assert "blueprint" in json.loads(response.text)


def test_fake_without_tools_keeps_pre_f015_behavior():
    fake = FakeModelAdapter()
    response = fake.complete("s", _tool_payload("文化遗产"))
    assert not response.tool_calls
    assert "blueprint" in json.loads(response.text)

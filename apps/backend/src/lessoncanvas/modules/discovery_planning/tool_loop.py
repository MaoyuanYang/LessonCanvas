"""F015 bounded, traced, whitelist-governed tool loop for workflow specialists.

Spec contract (specs/F015-governed-model-tool-calling/spec.md):
- the model may request tools; orchestration validates every request against
  the bound whitelist and the tool's inputSchema before dispatch (D2);
- refusals and mid-loop tool failures are recorded and fed back to the model
  as data-only `tool`-role observations so it can correct within the cap (D2);
- the loop is bounded by `tool_loop_max_rounds` and stops starting rounds at
  the per-run model-call cap; every loop model call counts 1:1 toward
  `run.model_calls` (D5);
- tool results re-enter the conversation as data only (D3): never in the
  system prompt, never trusted;
- when the loop ends without a valid final JSON the caller must run the
  deterministic pre-F015 path and disclose the fallback (D2/AC-006).
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from lessoncanvas.adapters.model import ModelResponse, parse_model_json
from lessoncanvas.settings import get_settings


@dataclass
class ToolLoopResult:
    data: dict | None
    response: ModelResponse | None = None
    fallback_reason: str | None = None
    rounds: list[dict] = field(default_factory=list)
    refused_count: int = 0
    # Accumulated results per dispatched tool name; callers merge them into
    # their grounding/citation inputs exactly like orchestration-issued
    # results (the final contract stays unchanged, F015 AC-001).
    tool_results: dict[str, list] = field(default_factory=dict)
    # Tool requests that arrived alongside the winning final JSON: traced and
    # dropped, never dispatched (Spec edge case). Carried here so the final
    # model event can disclose them — one billed call, one ledger event.
    dropped_tool_calls: list[dict] = field(default_factory=list)


def _validate_arguments(schema: dict, arguments: Any) -> str | None:
    """Validate model-issued arguments against the registry's inputSchema
    subset (type/properties/required). Returns a refusal reason or None.

    Anything that is not an object, misses a required field, or carries a
    wrongly-typed value is refused before dispatch; unknown extra keys are
    tolerated exactly like JSON Schema's default behavior."""

    if not isinstance(arguments, dict):
        return "arguments must be a JSON object"
    properties = schema.get("properties") or {}
    for required in schema.get("required") or []:
        if required not in arguments:
            return f"missing required argument: {required}"
    for key, value in arguments.items():
        spec = properties.get(key)
        if not isinstance(spec, dict):
            continue
        expected = spec.get("type")
        if expected == "string" and not isinstance(value, str):
            return f"argument {key} must be a string"
        if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            return f"argument {key} must be an integer"
        if expected == "number" and not isinstance(value, (int, float)):
            return f"argument {key} must be a number"
        if expected == "boolean" and not isinstance(value, bool):
            return f"argument {key} must be a boolean"
    return None


def _provider_assistant_message(response: ModelResponse) -> dict:
    """Assistant turn in provider shape; tool results ride only `tool`-role
    messages tied to their call ids (D3 — data-only framing)."""

    message: dict[str, Any] = {"role": "assistant"}
    if response.text:
        message["content"] = response.text
    message["tool_calls"] = [
        {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": json.dumps(call.arguments or {})},
        }
        for call in response.tool_calls
    ]
    return message


def run_tool_loop(
    *,
    session,
    run,
    system: str,
    user: str,
    tools: list[dict],
    dispatch: Callable[[str, dict], Any],
    record_trace_fn: Callable,
    run_id: str,
) -> ToolLoopResult:
    """Run one bounded specialist tool loop. `run` is the owning DiscoveryRun;
    every loop model call increments and commits `run.model_calls` before the
    next provider call so an interruption leaves a truthful partial trace."""

    from lessoncanvas.adapters.model import get_model_adapter

    settings = get_settings()
    adapter = get_model_adapter()
    bound = {tool["name"]: tool.get("inputSchema") or {} for tool in tools}
    history: list[dict] = []
    result = ToolLoopResult(data=None)

    for round_index in range(settings.tool_loop_max_rounds):
        if run.model_calls >= settings.max_model_calls_per_run:
            result.fallback_reason = "run_model_call_cap"
            return result

        started = time.monotonic()
        response = adapter.complete(system, user, tools=tools, history=history)
        latency = int((time.monotonic() - started) * 1000)
        run.model_calls += 1

        try:
            data = parse_model_json(response.text)
        except ValueError:
            data = None

        if data is not None:
            # Final JSON wins over any pending tool requests (Spec edge case):
            # pending requests are carried on the result (the caller's single
            # model event discloses them), never dispatched, and never
            # double-traced. A direct answer with no requests leaves no
            # tool-round event — absence stays honest (no fabricated rounds).
            result.dropped_tool_calls = [
                {"id": call.id, "name": call.name, "arguments": call.arguments}
                for call in response.tool_calls
            ]
            session.commit()
            result.data = data
            result.response = response
            return result

        record_trace_fn(
            session,
            run_id,
            "tool.request",
            {
                "round": round_index,
                "tool_calls": [
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in response.tool_calls
                ],
                "outcome": "pending" if response.tool_calls else "no_progress",
            },
            latency,
            usage=response,
        )

        if not response.tool_calls:
            # No valid final JSON and no requests: keep the turn visible and
            # let the cap bound the loop; the caller falls back at exit.
            history.append({"role": "assistant", "content": response.text or ""})
            result.rounds.append({"round": round_index, "outcome": "no_progress"})
            session.commit()
            continue

        history.append(_provider_assistant_message(response))
        for call in response.tool_calls:
            schema = bound.get(call.name)
            if schema is None:
                reason = f"tool not in bound whitelist: {call.name}"
            else:
                reason = _validate_arguments(schema, call.arguments)
            if reason is not None:
                result.refused_count += 1
                record_trace_fn(
                    session,
                    run_id,
                    "tool.refused",
                    {
                        "round": round_index,
                        "name": call.name,
                        "arguments": call.arguments,
                        "reason": reason,
                    },
                    0,
                )
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"refused": True, "reason": reason}, ensure_ascii=False
                        ),
                    }
                )
                result.rounds.append(
                    {"round": round_index, "name": call.name, "outcome": "refused"}
                )
                continue

            dispatch_started = time.monotonic()
            try:
                dispatch_result = dispatch(call.name, call.arguments)
                dispatch_latency = int((time.monotonic() - dispatch_started) * 1000)
            except Exception as error:  # noqa: BLE001 - the loop must survive tool failure
                record_trace_fn(
                    session,
                    run_id,
                    "tool.result",
                    {
                        "round": round_index,
                        "name": call.name,
                        "arguments": call.arguments,
                        "outcome": "failed",
                        "error": type(error).__name__,
                    },
                    int((time.monotonic() - dispatch_started) * 1000),
                )
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {"failed": True, "error": type(error).__name__},
                            ensure_ascii=False,
                        ),
                    }
                )
                result.rounds.append({"round": round_index, "name": call.name, "outcome": "failed"})
                continue

            summary = dispatch_result if isinstance(dispatch_result, list) else []
            record_trace_fn(
                session,
                run_id,
                "tool.result",
                {
                    "round": round_index,
                    "name": call.name,
                    "arguments": call.arguments,
                    "outcome": "dispatched",
                    "result_count": len(summary),
                    "results": summary,
                },
                dispatch_latency,
            )
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(dispatch_result, ensure_ascii=False),
                }
            )
            result.tool_results.setdefault(call.name, []).extend(summary)
            result.rounds.append(
                {"round": round_index, "name": call.name, "outcome": "dispatched"}
            )
        session.commit()

    result.fallback_reason = "round_cap_exhausted"
    return result

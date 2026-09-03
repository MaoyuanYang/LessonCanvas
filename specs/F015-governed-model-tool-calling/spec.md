# F015: Governed Model Tool Calling

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P1`
- Owner: `YMY / Project Owner`
- Decision Authority: `YMY / Project Owner`
- Dependencies: None hard (Phase 1 complete); consumes the existing MCP-compatible tool registry and whitelist dispatch delivered with F001/F003–F005
- Last Updated: 2026-09-03 (initial draft, Phase-2 planning)

## Goal

Let workflow specialists invoke whitelisted MCP-compatible tools themselves within a bounded, traced loop — tool use becomes model-driven under orchestration control, instead of every tool call being issued deterministically by workflow code.

## Business Value

The project's tool registry (ADR-0004) currently describes tools the model can never choose to use. Real governed tool calling makes the specialists genuinely tool-using agents while keeping dispatch whitelisted, bounded, fully traced, and inside the orchestrated-workflow authority.

## User Story

As the project owner, I want the planning specialist to decide for itself when the confirmed curriculum standards need searching and to perform that search under a whitelist and round cap, so that tool use is real Agent behavior with auditable rounds — not a hardcoded call.

## Background

Baseline observed on `main` (capability audit, 2026-09-03):

- `adapters/model.py` `DeepSeekAdapter.complete` sends only `model/messages/temperature/response_format(json_object)`; there is no `tools` parameter and no `tool_calls` parsing anywhere in the repository. The model never selects or calls a tool.
- Tools exist as MCP-compatible JSON-schema definitions (`search_curriculum_standards` in `sources_grounding/standards.py`; render/validate pairs for DOCX/PPTX/exercise in `artifact_production/`), dispatched through a strict name whitelist (`execute_tool`; unknown names raise), with adversarial tests proving hostile metadata cannot widen the set.
- All current tool calls are issued by workflow code at fixed points (e.g. standards search during planning grounding); renderers/validators run as deterministic post-steps.
- DeepSeek exposes OpenAI-compatible function calling; reliability when combined with `response_format: json_object` is an open question (D6).
- Governing constraints: ADR-0004 (MCP-compatible definitions, no public MCP server in Phase 1) and AGENTS.md ("Agents are explicit specialists inside an orchestrated workflow" — a bounded tool loop is in-authority; free-form autonomy is not).

## User Flow

1. A workflow stage (leading candidates: discovery analysis and planning grounding, per D1) binds its specialist with a subset of the tool registry.
2. The specialist may request tool calls; orchestration validates each request against the whitelist and the tool's input schema.
3. Valid requests execute through the existing `execute_tool` dispatch; results return to the model in the framing decided by D3, keeping results untrusted input.
4. The loop ends when the specialist produces its final structured JSON, or at the round cap (settings-driven, default per D5) — whichever comes first; every round is traced.
5. Teachers/technical reviewers see each tool round (request, result summary, latency, tokens, cost) in the existing layered evidence stream.

## Requirements

- Adapter: optional `tools`/`tool_choice` passthrough and `tool_calls` parsing in `DeepSeekAdapter`; the fake adapter gains scripted tool-round behavior for deterministic tests and fault injection.
- Bounded loop: at most N rounds per specialist invocation (settings-driven); termination at cap is deterministic and honest (final state names the cap).
- Whitelist refusal: a model-requested tool outside the bound set is recorded and never executed; continuation policy per D2 (skip-and-continue vs fail).
- Input validation: tool arguments are schema-validated before dispatch; malformed arguments follow the same refusal policy.
- Untrusted discipline: tool results re-enter the conversation as data (framing per D3); system prompts remain fixed and free of retrieved/tool content.
- Trace: one request/result event pair per round with latency, tokens, and estimated cost; rounds attribute to the calling specialist's stage.
- Render/validate document tools remain orchestration-called deterministic post-steps in this Feature (D4 confirms or changes this).
- Cost/caps: tool-loop model calls count toward the existing per-run model-call cap (F003 D3 contract; values revisited per D5).
- F009: new fault scenarios (cap exceeded, unknown tool requested, malformed arguments, tool failure mid-loop) and a `tool mode` field in the pass-comparability signature.

## Edge Cases

- Model requests an unregistered tool name (including names injected via source/memory content): refused, traced, never dispatched; adversarial suite extends to tool-loop requests.
- Model emits malformed tool arguments: refused with the recorded reason; loop continues per D2.
- Round cap reached without final JSON: deterministic terminal state per D2 (bounded retry exists at the Celery level; the loop itself never re-bills past the cap).
- Provider returns final JSON alongside pending tool requests: JSON wins; pending requests are traced and dropped.
- `json_object` response format incompatible with tool rounds (D6): the loop may use plain function-calling mode with server-side JSON re-validation of the final answer.

## API / Data Changes

- No new public endpoints and no schema migration expected; trace event payloads gain tool-round fields (`tool.request` / `tool.result` types on the existing TraceEvent stream).

## Acceptance Criteria

- [ ] AC-001 In a live run, the planning specialist completes its task having self-requested at least one real `search_curriculum_standards` round, with the final structured contract unchanged.
- [ ] AC-002 An out-of-whitelist tool request is never executed, is traced with the refused name, and the run continues or fails exactly per the D2 policy.
- [ ] AC-003 The round cap terminates the loop deterministically with an honest terminal state and no re-billing past the cap.
- [ ] AC-004 Adversarial tests prove injected tool names/metadata (via sources, memory, or tool output) cannot reach dispatch.
- [ ] AC-005 Every round is visible in the evidence stream with latency, tokens, and estimated cost; F009 deterministic fault scenarios cover cap/refusal/malformed/failure paths, and the comparability signature includes tool mode.

## Incremental Development Roadmap

### Step 1: Adapter tool support

- **Goal:** `DeepSeekAdapter` (and fake) can carry tool definitions and parse tool calls.
- **Scope:** `adapters/model.py`, fake adapter scripting, unit tests.
- **Tests:** adapter contract tests incl. tool_calls parsing and malformed cases.
- **Verification:** suite green with tools exercised only in tests.

### Step 2: Bounded loop primitive

- **Goal:** a reusable, traced, capped tool-loop runner inside the orchestrated graph nodes.
- **Scope:** discovery/planning shared helper, trace events, settings.
- **Tests:** cap, refusal, malformed-args, happy path with fake adapter.
- **Verification:** deterministic tests cover every terminal state.

### Step 3: Bind to first graphs (per D1)

- **Goal:** discovery analysis and/or planning grounding specialists run with `search_curriculum_standards` bound.
- **Scope:** graph node wiring, payload framing per D3.
- **Tests:** graph-level integration tests; untrusted-discipline assertions.
- **Verification:** fault-stack run shows traced tool rounds in evidence.

### Step 4: Evaluation + docs

- **Goal:** F009 scenarios/signature, guardrail re-verification, documentation sync.
- **Scope:** technical_evaluation harness/criteria, TESTING/API/ARCHITECTURE notes.
- **Tests:** new fault scenarios green deterministically.
- **Verification:** owner-authorized live evidence of a real tool round; docs match behavior.

## Test Plan

Deterministic backend tests (adapter, loop primitive, refusal/adversarial paths, cap accounting); F009 deterministic scenarios extended; one owner-authorized live pass at delivery evidencing a real self-requested tool round. Commands: `uv run pytest`, `uv run ruff check src tests migrations`; web suites only if evidence rendering changes.

## Open Questions

- D1 Which graphs get the loop first: discovery analysis + planning grounding (leading) vs also artifact writers.
- D2 Refusal policy for unknown tools / malformed args / cap exhaustion: skip-and-continue vs bounded retry vs run failure.
- D3 Framing of tool results: native `tool` role messages vs labeled user-payload injection (mapping the untrusted-input discipline onto function-calling mechanics).
- D4 Whether render/validate document tools stay orchestration-called (leading: yes; model-driven rendering is out of scope).
- D5 Round-cap default and how tool-loop model calls count against the per-run model-call cap.
- D6 Provider behavior of `response_format: json_object` combined with tools; fallback mode decision.
- D7 Interaction with streaming narration paths (leading: tool loops run on non-streaming completion calls only).

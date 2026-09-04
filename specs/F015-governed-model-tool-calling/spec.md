# F015: Governed Model Tool Calling

- Spec Status: `DONE`
- Roadmap Status: `DONE`
- Priority: `P1`
- Owner: `YMY / Project Owner`
- Decision Authority: `YMY / Project Owner`
- Dependencies: None hard (Phase 1 complete); consumes the existing MCP-compatible tool registry and whitelist dispatch delivered with F001/F003–F005
- Work item: [GitHub Issue #30](https://github.com/MaoyuanYang/LessonCanvas/issues/30) — bound 2026-09-03 (authorized); work-status authority
- Last Updated: 2026-09-04 (DONE: PR #31 merged as 8de343b; main re-verified)

## Gate Record: DONE

- Status: `PASS`
- Validation time: 2026-09-04
- Delivery: full remaining flow authorized by `YMY / Project Owner` on 2026-09-04 ("收尾所有剩余步骤" — push/PR/merge/main re-verification/Issue close/DONE records). PR [#31](https://github.com/MaoyuanYang/LessonCanvas/pull/31) merged as `8de343b` (feature commit `50dffa3`); Issue #30 closed with the projected checklist complete.
- Main re-verification after merge: backend 581 passed + 4 skipped + ruff clean; web 114/114 + tsc clean + eslint 0 errors (3 pre-existing warnings).
- DONE evidence manifest (working tree @ gate time): spec (this file, incl. REVIEW + DONE Gate Records), `ux-ui-f015-r1`, `test-design-f015-r1` + execution snapshot (TS-001..TS-020, TS-022 GREEN; TS-021 GREEN live), `plan-f015-r1` (T0–T8 complete), `review-f015-r1` (SF-1..SF-4 dispositioned; M-1 resolved by live evidence; M-2 owner-visible), `live-evidence.json` + `live-runner.py` (real self-requested standards round, 4 dispatches / 3 model calls / no fallback; D6 probe: provider rejects tools+json_object with HTTP 400).
- All acceptance criteria AC-001..AC-006 satisfied with traceable evidence (see the review AC→evidence table, the Test Design execution snapshot, and `live-evidence.json`).

## Gate Record: REVIEW

- Status: `PASS` (implementation and deterministic evidence under review; live evidence + delivery pending authorization)
- Validation time: 2026-09-03
- Implementation (plan `plan-f015-r1`, T0–T6 + T8): adapter tool support (`ToolCall`/`ModelResponse.tool_calls`, `provider_tool_definitions` mapping, tolerant `parse_tool_calls`, D6 plain function-calling mode on tool rounds, fake marker scripting incl. the `TOOL_INJECT_NAME` adversarial hook); bounded loop primitive (`discovery_planning/tool_loop.py`: whitelist + inputSchema-subset validation, record-and-continue refusals as corrective data observations, mid-loop failure survival, `tool_loop_max_rounds=5` and per-round run-cap headroom, per-round trace commits with usage, dropped-pending carried on the result for a single-event ledger); planning binding (`model_driven` drafting with no payload pre-injection, standards citations rebuilt from tool results, deterministic fallback with `tool.fallback` disclosure, `orchestration` mode preserving pre-F015 behavior); untrusted discipline (fixed system prompts, tool results only as data-only `tool`-role messages, hostile output inert); F009 integration (`tool_mode` signature, `fault:tool_loop` harness scenario with four variants, blocking `C-TOOL-1`, C-TRACE-1 ledger includes `tool.request`); web surfaces (four label-table entries + collapsed-row chips following the F014 precedent).
- Verification: backend 581 passed + 4 skipped + ruff clean (baseline 548+4 → +33 F015 tests; two full green runs); web 114/114 + tsc clean + eslint 0 errors (3 pre-existing warnings); E2E TS-020 green behind `E2E_TOOL_LOOP=1` on the deterministic stack (35.7s, keyboard + 420px included). Review `review-f015-r1`: SF-1 (dropped-pending ledger double-count) and SF-2 (fake empty-result scripting defect) found and fixed with tests; SF-3 (eval fault scope) fixed during T4; SF-4 test-contract updates recorded; residuals M-1 (live provider behavior until TS-021) and M-2 (single bound tool) owner-visible; no Critical/unfixed-High.
- Documentation synced 2026-09-03: README (model tool calling row), ARCHITECTURE (Discovery-and-Planning dependency note, Artifact-Production tool note, hosted-model boundary row), API (F015 event-type record), UX (tool-use honesty principle), TESTING (F015 suites + E2E recipe + environment note). AGENTS unchanged (no command or module-ownership change).
- Pending delivery-time steps (each under separate owner authorization): ~~T7 live probe (D6 mode) + TS-021 live evidence~~ EXECUTED and PASS 2026-09-04 (owner-authorized): `live-evidence.json` records a real self-requested `search_curriculum_standards` round with the unchanged contract (4 dispatched rounds, 3 model calls, no fallback) and the D6 probe result (provider rejects `tools + json_object` with HTTP 400 — plain function-calling mode is the required path); commit/push/PR; main re-verification; Issue #30 status sync.

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-03
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-03 (question-form answers selecting D1 "仅规划起草专家", D2 "记录后继续，回退保底", D5 "5 轮，计入现有上限"; D3/D4/D7 recorded as maintainer judgment; D6 evidence-resolved with a pre-specified fallback; explicit SPEC READY approval; Issue #30 creation separately authorized), scope: F015 Spec @ `7f6f230aae81`
- Checklist: 11/11 YES (Goal/Scope incl. explicit Out-of-Scope with routed-forward items, Flows incl. refusal-correctable and fallback paths, Rules/States incl. cap/refusal/fallback/direct-answer states, Data/API incl. new trace event types + `tool_loop_max_rounds`/`tool_loop_mode` settings with no new endpoints or migrations, Errors/Security incl. untrusted-input discipline on tool results and adversarial AC-004, Idempotency/Concurrency incl. per-invocation loop bounds and 1:1 `model_calls` accounting with no re-billing past the cap, Dependencies/Migration/Non-functional incl. no-migration impact and existing per-call timeout, unique observable ACs AC-001..AC-006, OBSERVED baseline inventory retained in Background and re-verified on `main`, no unresolved conflicts, no Critical Open Question OPEN/DEFERRED — D6 resolves by live evidence at implementation; UI presentation details routed to the UI READY gate)
- Related artifacts: work item [Issue #30](https://github.com/MaoyuanYang/LessonCanvas/issues/30)

## Goal

Let the workflow specialist invoke whitelisted MCP-compatible tools itself within a bounded, traced loop — tool use becomes model-driven under orchestration control, instead of every tool call being issued deterministically by workflow code.

## Business Value

The project's tool registry (ADR-0004) currently describes tools the model can never choose to use. Real governed tool calling makes the specialists genuinely tool-using agents while keeping dispatch whitelisted, bounded, fully traced, and inside the orchestrated-workflow authority.

## User Story

As the project owner, I want the planning specialist to decide for itself when the confirmed curriculum standards need searching and to perform that search under a whitelist and round cap, so that tool use is real Agent behavior with auditable rounds — not a hardcoded call.

## Background

Baseline observed on `main` (capability audit 2026-09-03; re-verified at `feature-dev` start same day):

- `adapters/model.py` `DeepSeekAdapter.complete` sends only `model/messages/temperature/response_format(json_object)`; there is no `tools` parameter and no `tool_calls` parsing anywhere in the repository. The model never selects or calls a tool.
- Tools exist as MCP-compatible JSON-schema definitions (`search_curriculum_standards` in `sources_grounding/standards.py` with `inputSchema`; render/validate pairs for DOCX/PPTX/exercise in `artifact_production/`), dispatched through a strict name whitelist (`execute_tool` raises `KeyError` for unknown names), with adversarial tests proving hostile metadata cannot widen the set.
- The only orchestration-issued grounding tool call today is `execute_tool("search_curriculum_standards", …)` in `discovery_planning/planning.py build_grounding` (query derived from the confirmed brief; results injected into the `planning_build_draft` payload and traced as `tool.standards_search`). Renderers/validators run as deterministic post-steps.
- Per-run cost governance: `run.model_calls` with `max_model_calls_per_run = 20` (settings); `record_trace` carries tokens/cost via `usage`; F009 `model_config_snapshot()` already pins `retrieval_mode` (F014) as the pass-comparability precedent `tool_mode` will join.
- DeepSeek exposes OpenAI-compatible function calling (`tools` / `message.tool_calls` / `role:"tool"` follow-ups); reliability combined with `response_format: json_object` is resolved by live evidence (D6).
- Governing constraints: ADR-0004 (MCP-compatible definitions, no public MCP server in Phase 1) and AGENTS.md ("Agents are explicit specialists inside an orchestrated workflow" — a bounded tool loop is in-authority; free-form autonomy is not).

## Scope

In scope: adapter tool passthrough/parsing (real + fake), one reusable bounded tool-loop runner with whitelist/schema refusal handling and deterministic fallback, binding of the planning drafting specialist to `search_curriculum_standards`, per-round trace events and evidence visibility, cap/`model_calls` accounting, `tool_loop_mode` configuration, F009 fault scenarios and `tool_mode` comparability signature, documentation sync.

Out of scope (routed forward, not silently dropped):

- Discovery-analysis and artifact-writer tool binding (D1; discovery and the three generation families keep orchestration-issued grounding unchanged).
- Model-driven render/validate document tools (D4; deterministic post-steps).
- Streaming tool loops (D7) and any Agent-to-Agent or multi-specialist tool chaining (AGENTS.md authority; F016 owns specialist division of labor).
- Semantic retrieval (F014) as a model-callable tool — it stays orchestration-issued; revisited with F016 if needed.
- Any new public MCP server, tool-registry expansion, or provider change beyond the existing single hosted model (ADR-0004 and the Phase-1 model constraint hold).

## User Flow

1. The planning drafting stage (`planning_build_draft`) binds its specialist with a subset of the tool registry: `search_curriculum_standards` only (D1).
2. The specialist may request tool calls; orchestration validates each request against the bound whitelist and the tool's `inputSchema` before dispatch.
3. Valid requests execute through the existing `execute_tool` dispatch; results return to the model as data-only `tool`-role messages (D3), keeping results untrusted input.
4. The loop ends when the specialist produces its final structured JSON (validated server-side exactly as today), at the round cap (5, D5), or in a refusal-correctable state — whichever comes first; every round is traced.
5. If the loop terminates without a valid final blueprint (cap exhaustion or persistent refusals), the stage falls back to the pre-F015 deterministic orchestration path and completes with disclosure (D2); the run never ends in a worse state than the no-tool behavior.
6. Teachers/technical reviewers see each tool round (request, result or refusal reason, latency, tokens, estimated cost) in the existing layered evidence stream.

## Requirements

- Adapter: optional `tools`/`tool_choice` passthrough and `tool_calls` parsing in `DeepSeekAdapter`; the fake adapter gains scripted tool-round behavior (title-marker conventions) for deterministic tests and fault injection.
- Bounded loop: at most 5 rounds per specialist invocation (`tool_loop_max_rounds`, settings-driven, D5); termination at cap is deterministic and honest (the terminal trace names the cap).
- Whitelist refusal: a model-requested tool outside the bound set is recorded and never executed; the refusal is returned to the model as a data observation so it can correct within the cap, and the loop continues (D2).
- Input validation: tool arguments are validated against the tool's `inputSchema` before dispatch; malformed arguments follow the same record-and-continue refusal policy (D2).
- Deterministic fallback (D2): when the loop ends without a valid final blueprint, the stage executes the pre-F015 behavior — orchestration-issued standards search plus a direct no-tools completion — and the trace discloses the fallback and its cause. The Roadmap no-tool-path guarantee stays true at run time, not only in configuration.
- Untrusted discipline (D3): tool results re-enter the conversation as data-only `tool`-role messages tied to their tool-call ids; system prompts remain fixed and free of retrieved/tool content; the final answer is server-side JSON-parsed and contract-validated as today, never trusting model framing.
- Trace: one request/result event pair per round with round index, tool name, arguments, outcome (dispatched / refused with reason), latency, tokens, and estimated cost; rounds attribute to the planning stage of the owning run.
- Render/validate document tools remain orchestration-called deterministic post-steps in this Feature (D4); model-driven rendering is out of scope.
- Cost/caps: every tool-loop model call increments `run.model_calls` and counts toward the existing `max_model_calls_per_run` cap (D5); no separate tool-loop budget; the loop never re-bills past the round cap.
- Configuration: `tool_loop_mode` setting (`model_driven` default | `orchestration`) selects whether the planning drafting stage runs the tool loop or the pre-F015 orchestration path; the F009 signature pins the configured value.
- F009: new deterministic fault scenarios (cap exhaustion, unknown tool requested, malformed arguments, tool failure mid-loop) and a `tool_mode` field in the pass-comparability signature; the duplicate-billing criterion's expected-call accounting includes tool-loop calls.
- Streaming: tool loops run on non-streaming completion calls only; streaming narration paths are unchanged (D7).

## Edge Cases

- Model requests an unregistered tool name (including names injected via source/memory content): refused, traced, never dispatched; the adversarial suite extends to tool-loop requests.
- Model emits malformed tool arguments (non-object, missing `query`, wrong types): refused with the recorded reason; the refusal observation lets the model retry correctly within the cap.
- Round cap reached without final JSON: deterministic fallback executes (D2); the loop itself never re-bills past the cap.
- Provider returns final JSON alongside pending tool requests: JSON wins; pending requests are traced and dropped.
- Tool execution itself fails mid-loop (dispatch raises): the failure is traced as a round outcome and treated as a refusal-class observation (record-and-continue, D2); the cap still bounds the loop.
- `json_object` response format incompatible with tool rounds (D6): the loop uses plain function-calling mode with server-side JSON re-validation of the final answer via the existing `parse_model_json` + contract validation; the chosen mode is recorded in the trace/settings.
- Live model never requests the tool and answers directly: acceptable; the answer is validated as today (the tool is optional to the specialist, not forced), and the run records zero tool rounds.

## API / Data Changes

- No new public endpoints and no schema migration expected; trace event payloads gain tool-round event types on the existing TraceEvent stream — `tool.request` (model-issued request; carries round index, name, arguments), `tool.result` (dispatch outcome with result summary), `tool.refused` (whitelist/schema refusal with reason), and `tool.fallback` (deterministic fallback disclosure with cause) — alongside the existing orchestration-issued `tool.standards_search` event retained for the fallback path.

## Acceptance Criteria

- [ ] AC-001 In a live run, the planning drafting specialist completes its task having self-requested at least one real `search_curriculum_standards` round, with the final structured blueprint contract unchanged.
- [ ] AC-002 An out-of-whitelist or malformed tool request is never executed, is traced with the refused name/reason, and the loop continues per D2 (corrective observation) — deterministically tested for every refusal class.
- [ ] AC-003 The round cap (5, counted 1:1 toward the existing per-run model-call cap) terminates the loop deterministically with an honest terminal trace and no model call past the cap.
- [ ] AC-004 Adversarial tests prove injected tool names/metadata (via sources, memory, or tool output) cannot reach dispatch.
- [ ] AC-005 Every round is visible in the evidence stream with latency, tokens, and estimated cost; F009 deterministic fault scenarios cover cap/refusal/malformed/mid-loop-failure paths, and the comparability signature includes `tool_mode`.
- [ ] AC-006 When the loop terminates without a valid final blueprint, the deterministic fallback completes the stage with disclosure and a correct blueprint — the run never degrades below pre-F015 behavior.

## Decision Log

| ID | Decision | Status | Date |
| --- | --- | --- | --- |
| D1 | First binding scope: planning drafting specialist only (`planning_build_draft` + `search_curriculum_standards`); discovery and artifact writers out of scope | Owner-selected (recommended option) | 2026-09-03 |
| D2 | Refusal policy: record-and-continue (refusal fed back as data so the model can correct within the cap); deterministic pre-F015 fallback with disclosure at cap exhaustion or loop failure | Owner-selected (recommended option) | 2026-09-03 |
| D3 | Tool-result framing: native OpenAI-compatible `tool`-role messages tied to tool-call ids; untrusted-input discipline maps to data-only placement (never system role; final answer server-validated) | Maintainer judgment (drafted leading position adopted) | 2026-09-03 |
| D4 | Render/validate document tools stay orchestration-called deterministic post-steps; model-driven rendering out of scope | Maintainer judgment (drafted leading position adopted) | 2026-09-03 |
| D5 | Round cap default 5 (`tool_loop_max_rounds`); every tool-loop model call counts 1:1 toward the existing `max_model_calls_per_run` (20); no separate budget | Owner-selected | 2026-09-03 |
| D6 | `json_object`+`tools` compatibility resolved by live-provider probe at implementation; specified fallback = plain function-calling mode + server-side JSON re-validation; chosen mode recorded | **Resolved by evidence 2026-09-04**: the live probe (`live-evidence.json`) shows the provider rejects the combination with HTTP 400; tool rounds therefore run in plain function-calling mode (implemented default, `response_format` omitted when tools are bound) with server-side `parse_model_json` re-validation — the pre-specified fallback is the required path | 2026-09-03 (pre-specified) → 2026-09-04 (evidence-resolved) |
| D7 | Tool loops run on non-streaming completion calls only; streaming narration unchanged | Maintainer judgment (drafted leading position adopted) | 2026-09-03 |

All D1–D7 resolutions are subject to owner `SPEC READY` approval of this revision.

## Incremental Development Roadmap

### Step 1: Adapter tool support

- **Goal:** `DeepSeekAdapter` (and fake) can carry tool definitions and parse tool calls.
- **Scope:** `adapters/model.py`, fake adapter round scripting, unit tests.
- **Tests:** adapter contract tests incl. `tool_calls` parsing, malformed cases, and both response-format modes (D6).
- **Verification:** suite green with tools exercised only in tests.

### Step 2: Bounded loop primitive with refusal and fallback

- **Goal:** a reusable, traced, capped tool-loop runner (whitelist + schema validation + record-and-continue refusals + deterministic fallback).
- **Scope:** shared loop helper (discovery_planning), trace events, settings (`tool_loop_max_rounds`, `tool_loop_mode`).
- **Tests:** cap, each refusal class, mid-loop tool failure, happy path, fallback execution, cap/`model_calls` accounting — fake adapter only.
- **Verification:** deterministic tests cover every terminal state of the loop.

### Step 3: Bind the planning drafting specialist

- **Goal:** `planning_build_draft` runs the tool loop with `search_curriculum_standards` bound in `model_driven` mode; `orchestration` mode preserves pre-F015 behavior.
- **Scope:** planning graph wiring, payload framing (standards enter via tool rounds, not pre-injection), fake scripting markers (unknown tool / bad args / cap exhaustion / never-final).
- **Tests:** graph-level integration tests; untrusted-discipline assertions (system prompt purity, payload-citation invariants).
- **Verification:** fault-stack run shows traced tool rounds in evidence; existing planning suites stay green in `orchestration` mode.

### Step 4: Evaluation, guardrails, docs

- **Goal:** F009 fault scenarios + `tool_mode` signature, evidence-panel round visibility, documentation sync.
- **Scope:** technical_evaluation harness/criteria/signature, evidence labels/detail, TESTING/API/ARCHITECTURE notes.
- **Tests:** new F009 scenarios green deterministically; duplicate-billing accounting covers tool-loop calls.
- **Verification:** owner-authorized live evidence of a real self-requested tool round; docs match behavior.

## Test Plan

Deterministic backend tests (adapter, loop primitive, every refusal class, cap and `model_calls` accounting, fallback, adversarial injection); F009 deterministic scenarios extended; one owner-authorized live pass at delivery evidencing a real self-requested tool round. Commands: `uv run pytest`, `uv run ruff check src tests migrations`; web suites where evidence rendering changes.

## Open Questions

None blocking `SPEC READY`; D6 resolves by live evidence at implementation under its pre-specified fallback.

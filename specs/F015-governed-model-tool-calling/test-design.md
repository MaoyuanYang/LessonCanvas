# Feature Test Design: F015 Governed Model Tool Calling

## Metadata

- Spec/Issue: `specs/F015-governed-model-tool-calling/spec.md` / [GitHub Issue #30](https://github.com/MaoyuanYang/LessonCanvas/issues/30)
- Validated inputs: Spec (SPEC READY PASS 2026-09-03 @ `7f6f230aae81`), UX/UI @ `ux-ui-f015-r1` / `c9df861b2b7e` (`UI READY`, 2026-09-03)
- Test Design revision: `test-design-f015-r1`
- Coverage scope: recommended risk-based scope (mirrors the owner-confirmed F013/F014 scope class): functional happy/alternative/boundary/error-recovery, injection defense, cap/cost accounting, F009 evaluation integration, observability/trace contract, UI label/chip interaction, deterministic E2E, one owner-authorized live pass at delivery. Excluded with reasons: live provider function-calling variance in CI `N/A - deterministic fake adapter scripts tool rounds in CI; live behavior evidenced once in TS-021`; loop load/stress `N/A - bounded by 5 rounds and the existing per-run cap; no perf infrastructure`; fuzz/property-based `N/A - refusal classes and terminal states enumerated deterministically`; visual regression `N/A - no infrastructure; component + E2E cover UI acceptance`; cross-browser `N/A - repo convention chromium`; i18n `N/A - zh-Hans inline copy per repo convention`; deployment/rollback `N/A - no migration or topology change; settings-driven with a safe code default`.
- Environments: (a) deterministic developer stack (compose infra + process app + fake model adapter with scripted tool rounds + eager tasks, existing `conftest.py` pattern) for backend; (b) deterministic browser stack for E2E; (c) live stack (real DeepSeek function calling) only for TS-021 and the D6 implementation probe, under separate owner authorization.
- `TEST DESIGN READY` Status: `PASS` (see Gate Record)

## Gate Record: TEST DESIGN READY

- Status: `PASS`
- Validation time: 2026-09-03
- Decision Authority: `YMY / Project Owner` — approved together with `plan-f015-r1` via interactive session on 2026-09-03 (explicit TEST DESIGN READY + Plan approval)
- Checklist: every AC mapped to ≥1 scenario; every Spec decision D1–D7 traced; every refusal class and terminal state covered; untrusted-input discipline covered; F009 comparability and duplicate-billing accounting covered; risk register complete; deterministic/live separation explicit; environments realistic; no Critical coverage gap

## Risk Register and Scenario Selection

| Risk / behavior | Impact | Scenario(s) |
| --- | --- | --- |
| Adapter mishandles `tools` passthrough or `tool_calls` parsing (incl. D6 modes) | Loop cannot run or silently drops requests | TS-001 |
| Fake adapter scripting unusable for deterministic rounds/faults | Deterministic coverage impossible | TS-002 |
| Loop unbounded, or re-bills past the round cap / run cap | Cost-honesty contract broken (AC-003) | TS-003, TS-007, TS-017, TS-018 |
| Unknown tool name reaches dispatch (incl. injected names) | Whitelist/authorization breach (AC-004) | TS-004, TS-013 |
| Malformed arguments reach `execute_tool` | Uncontrolled tool behavior | TS-005 |
| Tool failure mid-loop crashes or silently ends the run | Dishonest terminal state | TS-006 |
| Fallback missing, dishonest, or worse than pre-F015 behavior | Degradation below baseline (AC-006) | TS-007, TS-011 |
| Final JSON discarded when tool requests were pending | Valid answer lost / double billing | TS-008 |
| Direct answer treated as failure, or fabricated tool indicators | Honest optional-tool semantics broken | TS-009 |
| Model-driven binding changes the blueprint contract or drops grounding honesty | Regression of confirmed behavior (AC-001) | TS-010 |
| `orchestration` mode no longer reproduces pre-F015 behavior | Completed features broken | TS-011 |
| Tool results escape the data-only boundary (system-prompt purity, framing) | Injection discipline breach (AC-004) | TS-012 |
| Hostile metadata in sources/memory/tool output widens tool use | Authorization/injection breach (AC-004) | TS-013 |
| Trace/evidence contract drift (missing rounds, missing usage) | Evidence honesty broken (AC-005) | TS-014 |
| F009 passes compare across tool modes, or duplicate-billing check blind to loop calls | Evaluation honesty broken (AC-005) | TS-015, TS-016, TS-017 |
| UI hides refusals/fallback or mislabels rounds | Teacher/reviewer-visible honesty broken | TS-019, TS-020 |
| Live self-requested round unproven with real provider | Core claim unverified (AC-001) | TS-021 |
| Existing suites regress | Completed features broken | TS-022 |

Happy Path: TS-001/TS-003/TS-010; Alternative/boundary: TS-008/TS-009/TS-018; Error/security: TS-004/TS-005/TS-006/TS-012/TS-013; Recovery: TS-007/TS-011; Observability: TS-014/TS-019/TS-020; Evaluation: TS-015/TS-016/TS-017; Live: TS-021; Regression: TS-022.

## Acceptance Traceability

| AC / Decision | Scenario(s) |
| --- | --- |
| AC-001 (live self-requested round, contract unchanged) | TS-010, TS-021 |
| AC-002 (refusal never dispatched, traced, continue per D2) | TS-004, TS-005, TS-006 |
| AC-003 (5-round cap, 1:1 run-cap accounting, no re-billing) | TS-003, TS-007, TS-017, TS-018 |
| AC-004 (adversarial injection cannot reach dispatch) | TS-013, TS-012 |
| AC-005 (round visibility, F009 scenarios + `tool_mode`) | TS-014, TS-015, TS-016, TS-019, TS-020 |
| AC-006 (deterministic fallback, never worse than baseline) | TS-007, TS-011 |
| D1 (planning-only binding) | TS-010, TS-011, TS-022 |
| D2 (record-and-continue + fallback) | TS-004..TS-007 |
| D3 (tool-role data-only framing) | TS-012 |
| D5 (cap values) | TS-003, TS-018 |
| D6 (response-format modes) | TS-001, TS-021 |
| D7 (non-streaming only) | TS-022 (streaming suites unchanged) |
| Regression of completed features | TS-022 |

## Scenarios

### TS-001: Adapter tool passthrough and parsing contract

- Protects: AC-001, D6
- Risk/type: Functional / Happy path + boundary
- Steps: with `tools` bound, `DeepSeekAdapter` maps the MCP-style definition (`name`/`description`/`inputSchema`) to the provider's function-calling parameters in the request; a response carrying `message.tool_calls` is parsed into structured requests (id, name, arguments) with the final-answer path unchanged; responses with absent/malformed `tool_calls` fields degrade to no-request; both response-format modes (json_object combined with tools, plain function-calling mode) are exercised against the recorded request/response shapes.
- Expected: exact request payloads (tools array, message history including prior assistant tool_calls and `tool`-role results), parsed structured output, no crash on malformed shapes; unit-level with a mocked provider transport; no live calls.

### TS-002: Fake adapter tool-round scripting

- Protects: deterministic coverage of every loop state
- Risk/type: Test infrastructure / contract
- Steps: the fake adapter, when the planning-draft payload arrives with tools bound, scripts a tool round (request `search_curriculum_standards` with derived query), then produces the blueprint once tool results are present in history; title/payload markers script `TOOL_UNKNOWN` (request an unregistered name), `TOOL_BAD_ARGS` (malformed arguments), `TOOL_LOOP_FOREVER` (never produce final JSON), and the no-tool direct answer.
- Expected: every loop terminal state is scriptable deterministically; scripting never affects payloads without tools bound; existing marker contracts (TRANSIENT_FAIL etc.) unchanged.

### TS-003: Bounded loop happy path with accounting

- Protects: AC-003, D5
- Risk/type: Functional / Happy path + boundary
- Steps: run the planning drafting loop with the scripted round (request → validate → dispatch → result → final JSON); assert round count ≤ 5, every model call increments `run.model_calls` exactly once, per-round trace events exist (`tool.request` + `tool.result` with round index/name/arguments/outcome/usage), and the final `model.planning_build_draft` event is recorded once.
- Expected: loop completes at round 1–2; accounting exact; no un-traced provider call.

### TS-004: Whitelist refusal — unknown tool name

- Protects: AC-002, AC-004
- Risk/type: Security / error path
- Steps: script `TOOL_UNKNOWN` requesting an unregistered name (including a name injected via source content and memory records); assert `execute_tool` is never invoked for it, a `tool.refused` event records the name, a corrective data observation returns to the model, and the loop continues to a valid final blueprint or the cap.
- Expected: never dispatched; refusal traced; continuation per D2; the run does not fail solely due to the refusal.

### TS-005: Schema refusal — malformed arguments

- Protects: AC-002
- Risk/type: Functional / error path
- Steps: script `TOOL_BAD_ARGS` variants (non-object arguments, missing required `query`, wrong `limit` type); assert refusal with machine-readable reason before any dispatch, corrective observation, continuation.
- Expected: `execute_tool` never receives unvalidated arguments; each refusal class traced distinctly.

### TS-006: Tool failure mid-loop

- Protects: AC-002, D2
- Risk/type: Functional / error-recovery
- Steps: force the standards tool itself to raise during a dispatched round; assert the failure is traced as a round outcome (refusal-class observation), the loop continues or falls back per policy, and the run reaches a valid terminal state.
- Expected: no unhandled exception escapes the loop; no silent swallowing (trace records the failure).

### TS-007: Round-cap exhaustion and deterministic fallback

- Protects: AC-003, AC-006, D2
- Risk/type: Functional / error-recovery
- Steps: script `TOOL_LOOP_FOREVER`; assert the loop stops exactly at the round cap with a terminal trace naming the cap, no further model call bills the loop, the fallback executes the pre-F015 path (orchestration-issued `search_curriculum_standards` + direct no-tools completion traced as `tool.standards_search` + `model.planning_build_draft`), a `tool.fallback` event records the cause, and the resulting blueprint passes the unchanged contract.
- Expected: total model calls = cap + 1 fallback call (and honest accounting); the stage never ends in a worse state than pre-F015 behavior.

### TS-008: Final JSON alongside pending tool requests

- Protects: AC-002 edge case
- Risk/type: Functional / boundary
- Steps: script a response containing both valid final JSON and a pending tool request; assert the JSON wins, the pending request is traced and dropped, no extra round bills.
- Expected: exactly one final answer consumed; pending request visible in trace.

### TS-009: Direct answer without tool use

- Protects: honest optional-tool semantics
- Risk/type: Functional / alternative path
- Steps: script the no-tool direct answer; assert the blueprint validates, zero tool-round events exist, no fabricated tool indicator appears in trace or UI payloads.
- Expected: honest absence; no forced tool use; no failure state.

### TS-010: Planning graph integration in `model_driven` mode

- Protects: AC-001, D1
- Risk/type: Functional / integration
- Steps: run the full planning graph on the deterministic stack with `tool_loop_mode=model_driven`; assert standards sections enter the conversation only via the specialist's own tool rounds (no pre-injection in the initial payload), the final blueprint passes `normalize_blueprint` unchanged (structure, findings logic, citations), tool rounds attribute to the planning run's evidence stream, and the existing planning suites (interview rounds, quota, supersession) stay green.
- Expected: behavior parity except the grounding acquisition path; all prior planning acceptance intact.

### TS-011: `orchestration` mode reproduces pre-F015 behavior

- Protects: AC-006, D1
- Risk/type: Regression / compatibility
- Steps: run the same planning journeys with `tool_loop_mode=orchestration`; assert event sequences, payload shape (standards pre-injected), and `model_calls` counts match the pre-F015 baseline captured on `main`.
- Expected: byte-comparable behavior; the configuration fallback is real, not nominal.

### TS-012: Untrusted-input discipline in the loop (D3)

- Protects: AC-004, D3
- Risk/type: Security / injection
- Steps: with injection markers in tool results and retrieved text (hostile instructions attempting to widen tools, alter policy, or escape the data boundary), assert the system prompt stays fixed, tool results ride only `tool`-role data messages tied to their call ids, the final answer is server-side parsed/validated as today, and the injection text remains inert in outputs.
- Expected: no system-role content ever contains tool/source text; no instruction in untrusted content is honored.

### TS-013: Adversarial dispatch reachability

- Protects: AC-004
- Risk/type: Security / adversarial
- Steps: extend the adversarial suite so hostile tool names/arguments embedded in source documents, teacher-memory records, and tool outputs are requested by the scripted model; assert dispatch rejects every non-whitelisted name before execution and metadata can never widen the bound set.
- Expected: zero non-whitelisted dispatches across the corpus; all attempts visible as refusals.

### TS-014: Trace/evidence contract for tool rounds

- Protects: AC-005
- Risk/type: Observability / contract
- Steps: assert every round emits its event pair with round index, tool name, arguments, outcome, latency, tokens, and estimated cost (usage present where the adapter reports it; absent usage renders not-recorded per F006 convention); events flow through the existing evidence endpoints unchanged in shape.
- Expected: per-round visibility is complete; no round hidden; no cost fabricated when usage is missing.

### TS-015: F009 `tool_mode` comparability signature

- Protects: AC-005
- Risk/type: Evaluation / contract
- Steps: `model_config_snapshot()` includes `tool_mode`; evaluations created under different modes are marked not comparable (`superseded_configuration`) exactly as `retrieval_mode` behaves; existing legacy passes render marked, never silently mixed.
- Expected: signature change behaves identically to the F014 precedent.

### TS-016: F009 deterministic fault scenarios

- Protects: AC-005
- Risk/type: Evaluation / functional
- Steps: add harness fault scenarios — cap exceeded, unknown tool requested, malformed arguments, tool failure mid-loop — each judged by new criteria asserting the honest terminal state, refusal visibility, and fallback correctness.
- Expected: all new scenarios pass deterministically on the fake adapter; criteria pin observable behavior, not internals.

### TS-017: Duplicate-billing accounting with loop calls

- Protects: AC-003
- Risk/type: Evaluation / cost honesty
- Steps: the F009 duplicate/concurrency criterion's expected-call accounting includes tool-loop calls; run the duplicate-submission and stop/resume journeys on a tool-loop-enabled run; assert counts never double-count rounds, resume re-bills only incomplete work, and the cap blocks past-cap billing.
- Expected: model-call accounting stays exact under interruption and retries.

### TS-018: Round cap and run cap interplay

- Protects: AC-003, D5
- Risk/type: Functional / boundary
- Steps: construct a run near the per-run model-call cap; enter the loop; assert the loop respects both caps (never bills past either), mid-loop run-cap exhaustion produces the existing quota terminal state honestly (no silent continuation), and with headroom the loop + fallback complete within caps.
- Expected: no code path bills past either cap; quota behavior matches existing semantics.

### TS-019: Web evidence surfaces for tool rounds

- Protects: AC-005, U1/U2
- Risk/type: UI / contract
- Steps: component tests render the four new event types with zh-Hans labels and collapsed-row chips (第 N 轮 · 工具名 / 返回 M 条 / 拒绝：原因 / 回退：原因); expansion shows the raw payload; no-tool runs render nothing new; existing evidence-panel tests unchanged.
- Expected: label table + chip helper only; no structural change; web suite green.

### TS-020: Deterministic E2E planning journey with tool rounds

- Protects: AC-005, U1/U2 end-to-end
- Risk/type: E2E / integration
- Steps: deterministic browser journey: brief → planning (scripted self-requested standards round, including one refusal round) → confirm blueprint → open 运行证据 → assert tool-round rows with chips and expanded payloads; keyboard-operable rows; 420px canonical small-screen spot per repo convention.
- Expected: journey green on the deterministic stack; evidence honesty visible end-to-end.

### TS-021: Live self-requested tool round (owner-authorized at delivery)

- Protects: AC-001, D6
- Risk/type: Live evidence
- Steps: on the live stack (real DeepSeek), run the planning drafting stage for a representative unit; the specialist must self-request at least one real `search_curriculum_standards` round that executes and returns sections, and the final blueprint must pass the unchanged contract; the D6 probe result (json_object+tools compatibility) is recorded alongside; provider misbehavior, if any, is recorded honestly as it happens.
- Expected: real model-driven tool round evidenced with trace, usage, and cost; evidence file under `specs/F015-governed-model-tool-calling/`.

### TS-022: Full regression sweep

- Protects: completed features F001–F014
- Risk/type: Regression
- Steps: full backend suite + ruff, web suite + tsc + eslint, streaming narration suites explicitly unchanged (D7); both tool modes exercised across the planning suites.
- Expected: green at the same skip-count class as the F014 baseline (548 passed + 4 skipped + ruff clean; web 113/113).

## Execution Evidence Snapshot (2026-09-03)

| Scenario | Result | Evidence |
| --- | --- | --- |
| TS-001 | GREEN | `tests/test_tool_adapter.py` — passthrough/mapping, both response-format modes, tolerant parsing, provider failure mapping |
| TS-002 | GREEN | `tests/test_tool_adapter.py` — default round→final, LOOP_FOREVER, first-round-only UNKNOWN/BAD_ARGS with self-correction, TOOL_DIRECT, inject-name override, pre-F015 no-tools behavior |
| TS-003 | GREEN | `tests/test_tool_loop.py::test_ts003_*` — 2 billed calls, one request event with usage, one dispatched result, exact accounting |
| TS-004 | GREEN | `test_ts004_*` — refusal traced with whitelist reason, corrective continuation, unbound name never dispatched |
| TS-005 | GREEN | `test_ts005_*` — all three malformed-arg classes refused pre-dispatch with distinct reasons, corrected re-request |
| TS-006 | GREEN | `test_ts006_*` — failed rounds traced with error class, loop bounded to 5 attempts, fallback handed to caller |
| TS-007 | GREEN | `test_ts007_*` + `test_planning_tool_binding.py::test_ts010_fallback_*` — cap terminal, no re-billing, disclosed fallback completing the stage |
| TS-008 | GREEN (revised contract) | `test_ts008_*` — final JSON wins; dropped requests carried on the result and disclosed in the final model event; single ledger event per billed call (review SF-1) |
| TS-009 | GREEN | `test_planning_tool_binding.py::test_ts009_*` — direct answer, zero tool-round events, no fabricated indicators |
| TS-010 | GREEN | `test_ts010_model_driven_*` — self-requested round, no payload pre-injection, contract + standards citations unchanged |
| TS-011 | GREEN | `test_ts011_orchestration_*` — pre-F015 event vocabulary, pre-injected payload, single drafting call |
| TS-012 | GREEN | `tests/test_tool_discipline.py::test_ts012_*` — system purity across the journey, data-only tool-role framing, contract intact under injection |
| TS-013 | GREEN | `test_tool_discipline.py::test_ts013_*` — source-planted name refused end to end, hostile tool output inert, bound set caller-controlled |
| TS-014 | GREEN | `test_tool_discipline.py::test_ts012_trace_events_*` + TS-003 usage assertions — per-round events with latency/tokens/cost; missing usage renders not recorded |
| TS-015 | GREEN | `tests/test_technical_evaluation.py::test_ts015_*` — `tool_mode` pinned in the signature; cross-mode full-pipeline passes refused comparison with the configuration reason |
| TS-016 | GREEN | `test_ts016_*` — `fault:tool_loop` completed/pass; all four variants honest (cap/fallback/refusal/dispatch bounds, ledger invariant) |
| TS-017 | GREEN | `test_ts017_*` + C-TRACE-1/C-TOOL-1 ledger checks — loop calls fully in the trace ledger on real harness runs |
| TS-018 | GREEN | `tests/test_tool_loop.py::test_ts018_*` — one round of headroom bills exactly to the cap, never past; no-headroom returns the fallback signal immediately |
| TS-019 | GREEN | `apps/web/__tests__/evidence-panel.test.tsx` — four labels, round/refusal/result/fallback chips, payload expansion |
| TS-020 | GREEN | `E2E_TOOL_LOOP=1` journey (35.7s, serial worker, deterministic stack) — refusal→correction→blueprint, evidence chips, keyboard expansion, 420px spot |
| TS-021 | GREEN (live, owner-authorized 2026-09-04) | `live-evidence.json` — real DeepSeek self-requested `search_curriculum_standards` (4 dispatched rounds across 2 loop rounds — parallel requests validated and executed sequentially by design), final blueprint contract valid, 3 model calls, no fallback; D6 probe: provider rejects `tools + response_format json_object` with HTTP 400, so the implemented plain function-calling mode is the required path, not merely the fallback |
| TS-022 | GREEN | Full backend 581+4skip + ruff (two runs), web 114/114 + tsc + eslint 0 errors, streaming suites unchanged (D7), both tool modes exercised |

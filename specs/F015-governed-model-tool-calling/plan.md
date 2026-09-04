# F015 Implementation Plan — Governed Model Tool Calling

- Plan ID: `plan-f015-r1`
- Inputs (Gate-validated): Spec (SPEC READY PASS 2026-09-03 @ `7f6f230aae81`), UX/UI @ `ux-ui-f015-r1` / `c9df861b2b7e` (`UI READY`, 2026-09-03), Test Design @ `test-design-f015-r1` (TS-001..TS-022)
- This Plan answers only how to implement; requirements live in the Spec. It adds no rule, no Scope, and no contract change.

## Architecture fit

- Adapter extension (`adapters/model.py`): `complete` gains optional keyword-only `tools` (list of bound MCP-style definitions) and `history` (prior assistant `tool_calls` / `tool`-role data messages); the provider request maps `inputSchema` → function-calling `parameters` and parses `message.tool_calls`; `ModelResponse` gains optional structured `tool_requests`. Streaming paths (`stream`/`stream_with_usage`) are untouched (D7). Fake adapter scripts rounds off the existing `kind` dispatch + title-marker conventions.
- Loop runner (`modules/discovery_planning/tool_loop.py`, module-owned helper): binds a tool subset, validates requests against whitelist + `inputSchema`, executes through the existing `execute_tool` dispatch (Sources and Grounding boundary), returns refusals as corrective `tool`-role data observations (D2), enforces `tool_loop_max_rounds` and per-call run-cap headroom, emits `tool.request`/`tool.result`/`tool.refused`/`tool.fallback` via the existing `record_trace` (Run Orchestration boundary; no second authority), and returns either the final parsed JSON or a `fallback` signal.
- Planning wiring: in `model_driven` mode `build_grounding` keeps retrieval (orchestration-issued, F014) but stops pre-searching standards; `build_draft_node` runs the loop, then `normalize_blueprint` unchanged; on fallback the node executes the pre-F015 path inline (orchestration search + direct no-tools completion) with `tool.fallback` disclosure. `orchestration` mode short-circuits to today's code path exactly.
- F009: `model_config_snapshot()` gains `tool_mode` (mirrors `retrieval_mode`); new harness fault scenarios + criteria; expected-call accounting includes loop calls.
- Web: `EVIDENCE_EVENT_LABELS` entries + one collapsed-row chip helper following the `retrievalSummaryChips` precedent; no structural or shared-component change.

## Data and migration

- None. No schema change; `TraceEvent` payloads extend within the existing JSON column; no new tables or columns.

## Settings

- `tool_loop_max_rounds: int = 5` (D5), `tool_loop_mode: str = "model_driven"` (values `model_driven` | `orchestration`; the safe pre-F015 path remains one setting away in every environment). Both join `model_config_snapshot`'s `tool_mode` projection (`model_config_snapshot` pins `tool_loop_mode`).

## Tasks (vertical slices)

- **T0 — Branch, adapter, settings**: branch `feature/F015-governed-model-tool-calling`; `DeepSeekAdapter.complete` tools/history passthrough + `tool_calls` parsing (both response-format modes, D6-capable); `ModelResponse.tool_requests`; fake adapter round scripting + markers (`TOOL_UNKNOWN`, `TOOL_BAD_ARGS`, `TOOL_LOOP_FOREVER`, no-tool direct answer); settings keys; tests TS-001, TS-002. Proof: adapter contract suite green; full suite still green (no call site uses tools yet).
- **T1 — Loop primitive**: `tool_loop.py` with whitelist binding, `inputSchema` validation, record-and-continue refusals with corrective observations, mid-loop failure handling, round/run cap enforcement, per-round trace events with usage, fallback signal; tests TS-003..TS-008, TS-018. Proof: every terminal state covered deterministically at helper level.
- **T2 — Planning binding + fallback**: `model_driven` wiring in `planning.py` (grounding stops pre-injecting standards; `build_draft_node` runs the loop; inline deterministic fallback with `tool.fallback` disclosure); `orchestration` mode preserves the pre-F015 path; tests TS-009, TS-010, TS-011. Proof: planning journeys green in both modes; blueprint contract unchanged.
- **T3 — Untrusted discipline + adversarial**: system-prompt purity assertions, tool-result data-only framing checks, adversarial suite extension across sources/memory/tool-output hostile names (extends `test_guardrails_injection.py` / `test_standards.py` adversarial fixtures); tests TS-012, TS-013. Proof: zero non-whitelisted dispatch attempts reachable.
- **T4 — Trace contract + F009 integration**: event payload shape finalized (round index, name, arguments, outcome, usage); F009 `tool_mode` signature + incomparability; four new harness fault scenarios + criteria; duplicate-billing accounting extension; tests TS-014..TS-017. Proof: F009 deterministic scenarios green; comparability and accounting evidence recorded.
- **T5 — Web evidence surfaces**: label-table entries + round chips + fallback row in `evidence-panel.tsx` and `lib/api.ts`; tests TS-019. Proof: web suite green (`vitest` + `tsc` + `eslint`).
- **T6 — E2E journey**: deterministic browser planning journey with scripted tool rounds and one refusal, evidence assertions, keyboard + 420px spot; tests TS-020. Proof: journey green on the deterministic stack.
- **T7 — Live probe + live evidence (owner-authorized at execution)**: D6 probe against real DeepSeek decides the response-format mode (recorded); TS-021 live pass evidencing a real self-requested `search_curriculum_standards` round; evidence file `live-evidence.json` under the spec directory.
- **T8 — Regression, review, docs sync**: TS-022 full sweep (backend + ruff, web + tsc + eslint, streaming unchanged); Self Review (`review.md`); documentation sync — ARCHITECTURE (tool-loop boundary under orchestrated authority), API (new trace event types), TESTING (new suites, E2E, live evidence), UX (tool-round evidence states), README only where the tool-calling claim reads stale; ROADMAP + Issue #30 status. AGENTS only if commands change (they do not).

## Transaction / consistency notes

- The loop runs inside one LangGraph node on the planning thread; each round commits trace events and `model_calls` increments before the next provider call, so an interruption mid-loop leaves a truthful partial trace and the checkpoint resumes at node boundaries (same recovery semantics as today's multi-call nodes).
- No run may bill past either cap: the loop checks run-cap headroom per round; exhaustion mid-loop routes to the fallback only when headroom for exactly one more call exists, otherwise the existing quota terminal state applies.

## Verification cadence

- Per task: `uv run pytest` (targeted modules first, full suite before moving on) + `uv run ruff check src tests migrations`; web suites at T5/T6/T8 (`corepack pnpm web:test` / `web:typecheck` / `web:lint`); E2E at T6; live probe + TS-021 at T7 under separate owner authorization. Full re-run of both stateful suites (backend, web) before REVIEW.

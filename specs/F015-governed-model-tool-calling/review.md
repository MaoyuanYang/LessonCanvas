# F015 Self Review — Governed Model Tool Calling

- Review ID: `review-f015-r1`
- Scope: full working-tree diff on `feature/F015-governed-model-tool-calling` vs `main` (83ecd2c)
- Reviewed: 2026-09-03, implementation T0–T6 + T8 complete per `plan-f015-r1`; T7 (owner-authorized live probe + TS-021 live evidence) and delivery are delivery-time steps.

## Verification summary

- Backend: `uv run pytest` — 581 passed + 4 skipped (baseline 548+4 → +33 F015 tests across `test_tool_adapter.py`, `test_tool_loop.py`, `test_planning_tool_binding.py`, `test_tool_discipline.py`, and evaluation additions; run twice, both green); `uv run ruff check src tests migrations` clean.
- Web: `corepack pnpm web:test` 114/114 (baseline 113 → +1 F015 tool-round rendering test); `web:typecheck` clean; `web:lint` 0 errors (3 pre-existing warnings on main).
- E2E: `E2E_TOOL_LOOP=1` journey TS-020 green on the deterministic stack (fake model adapter, model_driven default, serial worker, 35.7s): upload→planning completes through refusal→correction→final→blueprint confirms with the unchanged contract→evidence tab renders 蓝图规划 tool rounds with 第 N 轮/拒绝/返回 chips→keyboard expansion→420px canonical spot. Degradation paths (cap/refusal/malformed/mid-loop failure) are backend-suite coverage by design (TS-004..TS-007/TS-016).
- Structural spot-checks in review: `orchestration` mode byte-comparable behavior (TS-011 asserted event vocabulary, payload shape, single drafting call); loop commits each round's trace + `model_calls` before the next provider call; C-TRACE-1/C-TOOL-1 ledger invariants hold on every loop run (TS-017); no tool round ever bills past either cap (TS-018); system-prompt purity across the whole journey (TS-012); source-planted tool names never reach dispatch end to end (TS-013).

## Findings

### SF-1 (defect found and fixed in review): dropped-pending path double-counted the trace ledger

When a response carried both a valid final JSON and pending tool requests, the loop recorded a `tool.request` event (with usage) for the same call for which the caller then recorded `model.planning_build_draft` — two ledger events for one billed model call, which would have made C-TRACE-1 (`model_calls != traced`) fail on any such run. Fixed by carrying the pending requests on `ToolLoopResult.dropped_tool_calls` (disclosed inside the final model event's payload) instead of a second event: one billed call, one ledger event. TS-008 updated to pin the corrected contract (no event, result-carried disclosure).

### SF-2 (fake-scripting defect found and fixed): dispatched-but-empty results looked like "no round yet"

The fake planning adapter detected "a standards round already happened" by the presence of collected sections, so a real empty search result (legitimate: no matching standards sections) looked identical to "no round yet" and the scripted model kept requesting until the cap — masking the honest direct-answer-after-empty-result behavior and making the loop-bound test (`test_ts013_loop_bound_set_is_caller_controlled`) fail. Fixed by separating "a dispatched round happened" (any `tool`-role message whose content parses to a JSON list, even empty) from "sections present". Refusal/failure feedback (dict content) still does not count as a dispatched round.

### SF-3 (eval fault-injection scope, fixed during T4): mid-loop tool failure must clear for the deterministic fallback

The first `fault:tool_loop` harness implementation raised on every standards search whose query carried the marker — including the fallback's orchestration-issued search, so the fault crashed the planning graph instead of exercising the D2 recovery path. The injection is now budget-bounded (fails only within `tool_loop_max_rounds` calls, then clears so the fallback completes), gated to fake-adapter eval environments exactly like `FakeModelAdapter.activate_eval_faults`, with an explicit harness-side reset. Production configurations can never arm it (both gates required).

### SF-4 (test-contract updates, recorded): pre-F015 assertions on planning wiring

- `test_planning_uses_standards_tool_with_snapshot_citations` asserted the orchestration-issued `tool.standards_search` event type; in model_driven mode the same guarantee (standards tool use visible in evidence + citations present) is delivered by the traced `tool.request`/`tool.result` vocabulary. The test now accepts either vocabulary while still requiring citations and the drafting event.
- Three test-local adapter stubs (`Failing`, `_SlowStreamAdapter`) gained the `tools`/`history` kwargs; `_SlowStreamAdapter.complete` now delegates non-narration drafting calls to the fake adapter while still failing narration attempts loudly (narration must stream — D7 unchanged).
- The F009 report test's blocking-evidence scenario list gained `fault:tool_loop` because C-TOOL-1 joined `ALL_BLOCKING_KEYS` (the set-level outcome honestly stays `missing_evidence` without it).
- C-TRACE-1's ledger count includes `tool.request` events (each is one billed, usage-carrying loop call) — the accounting change planned as TS-017, not a relaxation.

### M-1 (residual — RESOLVED by live evidence 2026-09-04): live provider function-calling behavior

TS-021 executed under owner authorization (`live-evidence.json`): real DeepSeek self-requested `search_curriculum_standards` on the first attempt (4 dispatched rounds across 2 loop rounds — the provider issues parallel calls, which the loop validates and executes sequentially by design), produced a contract-valid blueprint in 3 model calls without fallback. The D6 probe resolved the response-format question decisively: `tools + response_format json_object` is rejected by the provider with HTTP 400, so the implemented plain function-calling mode on tool rounds is the required path. Residual note: one live pass on one unit; variance across units/queries remains bounded by the deterministic suites and the honest direct-answer/no-round state.

### M-2 (residual): loop bound set is one tool today

Only `search_curriculum_standards` is bound (D1). The loop primitive, schema validator subset (type/properties/required), and evidence vocabulary are registry-shaped and cover more tools, but multi-tool interaction (parallel calls in one round are executed sequentially; a second bound tool is untested) is out of scope and unpromised.

### L-1 (environment note): shared deployed-stack ports and E2E instance recipe

Local verification ran against `lessoncanvas_test`/`lessoncanvas_e2e` on the F012 deployed PostgreSQL/MinIO via env overrides (established machine pattern since F012). The E2E stack needed its own fake-API instance (:8010, CORS extended to the :3001 web origin) because :8000/:3000 are the deployed containers (real DeepSeek); the stale-port restart trap (uvicorn bind failure behind nohup) is recorded here for the next run. No repo state depends on this.

## AC → evidence

| AC | Evidence |
| --- | --- |
| AC-001 | TS-010 (contract unchanged, self-requested round, no pre-injection), TS-020 (E2E visibility); live proof TS-021 pending owner authorization (M-1) |
| AC-002 | TS-004/TS-005/TS-006 (every refusal class: never dispatched, traced, corrective continuation), TS-016 C-TOOL-1 |
| AC-003 | TS-003 (exact 1:1 accounting), TS-007 (cap exhaustion, no re-billing), TS-018 (run-cap interplay), TS-017 (ledger invariant) |
| AC-004 | TS-012 (system purity, data-only framing), TS-013 (source-planted names refused end to end; bound set caller-controlled) |
| AC-005 | TS-014 (per-round events with usage; folded into `test_tool_discipline.py` trace-contract test), TS-015 (`tool_mode` signature + refusal to compare across modes), TS-016 (four fault scenarios), TS-019/TS-020 (UI + E2E) |
| AC-006 | TS-007 (fallback completes with disclosure), TS-011 (orchestration mode reproduces pre-F015 behavior) |

## Commands

Backend: `uv run pytest`; `uv run ruff check src tests migrations`. Web: `corepack pnpm web:test` / `web:typecheck` / `web:lint`. E2E: fake-API instance + `next dev -p 3001` with `NEXT_PUBLIC_API_BASE_URL` pointing at it, then `E2E_TOOL_LOOP=1 E2E_BASE_URL=http://localhost:3001 E2E_API_BASE_URL=http://localhost:8010 corepack pnpm --filter web exec playwright test e2e/tool-loop-journey.spec.ts --workers=1`.

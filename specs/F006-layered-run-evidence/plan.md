# Implementation Plan: F006 Layered Run Evidence

## Inputs (validated revisions)

- Spec: `specs/F006-layered-run-evidence/spec.md` @ `b43922d2cc17` (`SPEC READY` PASS)
- UX/UI: `specs/F006-layered-run-evidence/ux-ui.md` @ `ux-ui-f006-r1` / `4bff46959bb0` (`UI READY` PASS)
- Test Design: `specs/F006-layered-run-evidence/test-design.md` @ `test-design-f006-r1` / `e2e261591bd8` (`TEST DESIGN READY` PASS)
- This Plan adds no requirement; any contract deviation returns to the Spec through Design Change.

## Module Mapping (per AGENTS Module Rules)

| Change | Owner module | Notes |
| --- | --- | --- |
| Evidence inventory/summary/events read service | Run Orchestration and Observability (`modules/run_orchestration/evidence.py`) | Derived projection over existing tables; no second truth |
| Trace write path (tokens/model/estimated cost) | `record_trace` extension (currently `discovery_planning/graph.py`, consumed by artifact graphs) | Signature gains usage metrics; cost helper in run_orchestration; no ownership change |
| Evidence narration | `modules/run_orchestration/narration.py` (sibling of the discovery/planning narration pattern) | Registry/thread/stop per established pattern; consolidation deferred (recorded in review) |
| Evidence API + legacy endpoint removal | `api/evidence.py`; delete `api/trace.py` | Router registration updated in `main.py` |
| Frontend | `lib/api.ts` (typed client + Zod), `components/evidence-panel.tsx`, workspace eighth tab | Reuses shared artifact-run, conversation-region, desktop-gate, ui foundations |
| Deletion | Existing cascade | Verified by test, not redesigned |

## Data / Settings Changes

- Migration (additive): `trace_events` gains `prompt_tokens INT NULL`, `completion_tokens INT NULL`, `model VARCHAR(64) NULL`; ORM `TraceEvent.run_id` drops the stale `ForeignKey("discovery_runs.id")` declaration to match the already-applied free-`run_id` migration (index retained). No data rewrite.
- Settings: `model_price_prompt_per_mtok: float`, `model_price_completion_per_mtok: float` (defaults set at implementation from the provider's published prices; estimates regardless), `evidence_events_page_default: int = 50`, `evidence_events_page_max: int = 200`, `evidence_inventory_page_default: int = 50`.
- Write path: `record_trace(..., usage=None, model=None)` persists tokens/model and computes `cost_usd` = prompt×price_p + completion×price_c; callers with a `ModelResponse` pass its usage; missing usage stays null (未记录), never zero.
- Stream usage: `DeepSeekAdapter.stream` requests `stream_options.include_usage` and surfaces the final usage chunk when present; absence degrades to an explicit gap.

## API Flow (target)

- `GET /projects/{id}/evidence` → inventory `{runs: [...], next_cursor}` (five kinds union; per-run kind/status/versions/usage/cost/scope counts).
- `GET /projects/{id}/evidence/{run_id}` → Layer-1 summary `{kind, status, bound versions, scope outcomes, failure reasons + recovery pointers, usage vs cap, aggregates (cost estimated, model latency), evidence availability flags, telemetry gap notices}`.
- `GET /projects/{id}/evidence/{run_id}/events?after=&limit=&kind=` → ordered merged stream (trace events + interview rounds for discovery/planning) with `{cursor, kind, lesson_index?, created_at, latency_ms, tokens, cost_usd (estimated), model, payload}`; end marker when exhausted.
- `POST /projects/{id}/evidence/{run_id}/narrate` → `{ok}` (workspace-quota guarded; one active narration per run).
- `POST /projects/{id}/evidence/{run_id}/narrate/stop` → `{ok}` (matches established stop pattern).
- `GET /projects/{id}/evidence/{run_id}/narrate/stream` → SSE token stream; complete text recorded as `model.evidence_narration` trace event.
- Removed: `GET /projects/{id}/trace` + `api/trace.py` + `tests/test_trace.py` (replaced by evidence suites).

Narration prompt composition is server-side from authoritative run facts (established F002 pattern); the stream is display-only.

## Tasks

### T0 — Contracts, settings, migration, trace write path
- Settings + price helper + `record_trace` extension; migration with up/down proof on a seeded legacy snapshot; ORM FK alignment.
- Tests: TS-005 (cost unit), TS-010 (write path), TS-014 (migration).
- Exit: `uv run pytest tests/test_evidence.py -k "cost or write or migration"` green; migration applies/reverts on dev DB.

### T1 — Evidence read service (inventory / summary / events)
- Aggregation queries + cursor pagination + gap flags + interview-round merge; no business mutation anywhere in the module.
- Tests: TS-001, TS-002, TS-003 (incl. concurrent append), TS-004, TS-011, TS-012.
- Exit: service-level suite green in `tests/test_evidence.py`.

### T2 — Evidence API + authorization + legacy removal
- Router with ownership enforcement (project → run containment), error taxonomy mapping, endpoint removal, main.py registration.
- Tests: TS-006, TS-007, TS-013; full backend suite rerun.
- Exit: `uv run pytest` fully green (evidence suites replace `test_trace.py`).

### T3 — Evidence narration (quota, idempotency, trace record, deletion check)
- `modules/run_orchestration/narration.py` sibling implementation; workspace-quota reservation via existing counters; stream usage enhancement; deletion cascade verification.
- Tests: TS-009, TS-008.
- Exit: narration suite green; cascade assertions green.

### T4 — Frontend client + evidence panel + eighth tab
- Zod schemas + typed client in `lib/api.ts`; `components/evidence-panel.tsx` (inventory, summary, technical disclosure with inert payload text + copy, cursor load-more, narration via conversation-region pattern); workspace eighth tab `运行证据`; desktop gate for depth below 1024px.
- Tests: TS-016, TS-017, TS-018, TS-019 (Vitest).
- Exit: `corepack pnpm web:test` green incl. unchanged existing suites; `web:lint` + `web:typecheck` clean.

### T5 — E2E journeys + accessibility (B-001)
- `apps/web/e2e/evidence-journeys.spec.ts` (fault-stack journey TS-020; live-stack journey TS-021 per TQ-002 profiles); scripted a11y checks; execute and record the B-001 manual keyboard/screen-reader pass (TS-022).
- Exit: journeys green (or owner-approved residual per the F004/F005 pattern); pass evidence recorded in the Test Design Execution Evidence Snapshot; B-001 closed in STAGE.

### T6 — Routed residual investigations (Bug branch)
- TS-023 SSE early-drop: reproduce under scripted disconnect profiles on the narration/generation stream; fix + regression test if reproducible, else record attempts, evidence, mitigation confirmation, residual risk.
- TS-024 StaleDataError teardown: re-run supersession journeys with the evidence view observing; fix + test if confirmed, else record non-reproduction evidence and explicit F011 re-route with owner confirmation.
- Exit: findings recorded in `review.md` with evidence; no silent deferral.

### T7 — Full verification, review, docs sync, delivery prep
- Full stack: `uv run pytest`, `uv run ruff check src tests migrations`, `corepack pnpm web:test / web:lint / web:typecheck / web:build`; `review.md` self-review with severity findings; documentation sync (`docs/API.md` evidence endpoints + removal note, `docs/DATABASE.md` trace columns, `docs/UX.md`/`UI.md`/`DESIGN_SYSTEM.md` usage notes incl. deferred promotion, `docs/TESTING.md` if strategy changed, README Current Stage fix); ROADMAP/STAGE/Issue projection sync; PR description preparation.
- Exit: all suites green; docs synced; delivery record ready for authorization.

## Verification Commands (per Task exit)

```text
Backend:  cd apps/backend && uv run pytest && uv run ruff check src tests migrations
Web:      corepack pnpm web:test && corepack pnpm web:lint && corepack pnpm web:typecheck && corepack pnpm web:build
E2E:      per TQ-002 profiles (fault stack: fake adapter + eager/real Worker; live stack: real DeepSeek + real Worker)
```

## Risks / Unknowns / Exit Conditions

- Live-stack E2E may hit the known Clerk dev-instance session class → owner-approved substitute coverage + recorded residual (established pattern).
- Narration on the live provider adds one model call per owner action; bounded by workspace quota, disclosed in UI.
- Price-table drift is accepted: costs are labeled estimates at write time; changing prices affects new events only.
- Any discovered need to change contracts returns to the Spec (Design Change); the Plan never redefines requirements.
- Branch: `feature/F006-layered-run-evidence` (created at CODING_TESTING start; commit/push/PR each separately authorized).

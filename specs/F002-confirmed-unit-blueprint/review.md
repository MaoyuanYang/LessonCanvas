# Review: F002 Confirmed Unit Blueprint

## Inputs and Verification Evidence

- Spec: `specs/F002-confirmed-unit-blueprint/spec.md` @ `108178994342` (`SPEC READY: PASS`)
- UX/UI: `specs/F002-confirmed-unit-blueprint/ux-ui.md` @ `a8cfd23189ac` (`UI READY: PASS`)
- Test Design: `specs/F002-confirmed-unit-blueprint/test-design.md` @ `9c997cfa2b6f` (`TEST DESIGN READY: PASS`)
- Plan: `specs/F002-confirmed-unit-blueprint/plan.md` (`plan-f002-r1`, T0–T8)
- Review date: 2026-08-28; reviewer: executing `feature-dev` session; Decision Authority: `YMY / Project Owner`

### Verification runs (2026-08-28, branch `feature/F002-confirmed-unit-blueprint`)

| Check | Command | Result |
| --- | --- | --- |
| Backend suite | `uv run pytest` | 73 passed |
| Backend lint | `uv run ruff check src tests migrations` | clean |
| Backend format | `uv run ruff format --check` | clean |
| Web unit tests | `corepack pnpm --filter web test` | 16 passed |
| Web lint | `corepack pnpm --filter web lint` | clean |
| Web typecheck | `corepack pnpm --filter web typecheck` | clean |
| Web build | `corepack pnpm --filter web build` | success |
| Public E2E | `corepack pnpm --filter web test:e2e` | 3 passed, 1 skipped (CLERK_E2E gate) |

### Acceptance coverage (AC -> TS -> evidence)

- AC-001: TS-001 (`test_planning.py` idempotent/bound/gate), TS-010 (duplicate start), TS-020 (quota) — PASS
- AC-002: TS-002/TS-003 (gap questions within 6x3; zero-gap direct draft) — PASS
- AC-003: TS-004 (round cap, unresolved marked as open `period_warning` finding; hand-edit via PATCH covered by TS-006) — PASS
- AC-004: TS-005 (six lessons, required fields, standards citations with snapshot version) — PASS
- AC-005: TS-006 (revision + 409 stale conflict) — PASS
- AC-006: TS-007 (all three failed-check variants named) — PASS
- AC-007: TS-008 (undecided blocks; reason recorded; blocking not decidable; empty reason rejected) — PASS
- AC-008: TS-009 (atomic, idempotent, immutable, new cycle), TS-010 (concurrent confirm singleton) — PASS
- AC-009: TS-011 (supersede run, stale draft+version, field diff, impact summary, stale confirm rejected) — PASS; E2E journey authored, gated run pending (B-001)
- AC-010: TS-012 (`tool.standards_search` trace + snapshot-version citations; injection corpus case) — PASS
- AC-011: TS-013 (cross-account 404 on planning/blueprint) — PASS
- AC-012: TS-014 (provider failure preserves state; retry resumes) — PASS
- AC-013: TS-015 (planning SSE narrate/stream/complete; stop/re-ask/reconnect semantics shared with the F001-proven narration machinery) — PASS
- AC-014: TS-021/TS-022 component layer (labels, aria-live, roles, desktop-required notices) — PASS; keyboard manual pass gated with E2E (M-2)
- AC-015: TS-017 (planning trace events; deletion cascade includes blueprint tables) — PASS
- AC-016: TS-018 (no generation surface in OpenAPI; stale confirm non-authorizing) — PASS

## Self-Review Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| M-1 | Medium | Authenticated E2E blueprint journey (TS-023/TS-024) is authored but not executed: Clerk device verification still blocks automated sign-in (F001 residual B-001) | Waived with follow-up: same residual class as F001; unblock condition recorded in STAGE B-001; component + API layers fully cover the behavior deterministically |
| M-2 | Medium | Blueprint keyboard-only accessibility pass (TS-022 manual) not executed this session; automated coverage limited to semantic assertions (labels, aria-live, roles, focus-visible styles) | Follow-up: execute with the gated E2E session after Clerk configuration changes; no Critical risk since all interactions use native controls and the shared Radix primitives |
| L-1 | Low | `max_planning_runs_per_workspace` default (50) chosen without cost evidence | Recorded as Test Design TQ-003; revisitable by configuration without behavior change |
| L-2 | Low | Findings embedded in draft payload (plan refinement) — cross-version finding queries would need aggregation if F006/F007 require them | Deferred with trigger in ux-ui.md reuse table; no current consumer needs it |

No Critical or High findings.

## Architecture and Boundary Review

- Module ownership respected: planning/blueprint live in `discovery_planning`; standards tool consumed through the existing `sources_grounding` boundary (ADR-0004); no new service, cache, queue, or cross-module dependency introduced.
- Implementation refinements recorded in the Plan (no Spec change): planning runs reuse `discovery_runs` with a `kind` discriminator instead of a new table (FK/narration/deletion reuse, single run concept); findings embedded in the draft payload with decisions recorded as new draft revisions (append-only lineage).
- Concurrency/idempotency at the database boundary: partial unique index for one active planning run per project; unique `(project, source_revision)` for idempotent confirmation; supersession executed in the brief-confirmation transaction.
- Security: ownership checks on every new endpoint; blueprint payloads normalized server-side (unknown fields dropped); citations injected from verified grounding context, never trusted from model output; blocking checks computed server-side.
- Deletion cascade extended to blueprint tables; audit rows for blueprint confirmation and finding decisions (non-content).

## Documentation Sync Performed

- `specs/F002-confirmed-unit-blueprint/plan.md`: task statuses T0–T8 and implementation-refinement notes
- `docs/DESIGN_SYSTEM.md`: shared conversation-region component recorded (D-CONVO promotion)
- `specs/ROADMAP.md` + `STAGE.md` + Issue #3: status projections to `REVIEW`
- No changes required to `docs/API.md` (no project-level convention change), `docs/DATABASE.md` (macro truth unchanged), `AGENTS.md` (no new commands), `README.md`

## Delivery Status

- Delivery state: `READY FOR PR` pending explicit commit/push/PR authorization from `YMY / Project Owner`
- Suggested PR title: `feat: add confirmed unit blueprint workflow (F002)`

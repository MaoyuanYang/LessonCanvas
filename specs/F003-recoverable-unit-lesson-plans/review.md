# Review: F003 Recoverable Unit Lesson Plans

## Metadata

- Spec: `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `193e90d10b68` (`SPEC READY` PASS)
- UX/UI: `ux-ui-f003-r1` / approved content `43f93abc6ed3` (`UI READY` PASS)
- Test Design: `test-design-f003-r2` / `880a6a4a418c` (`TEST DESIGN READY` PASS)
- Plan: `plan.md` @ `10b030e8f809` (T0–T5, T6, T8 complete; T7 partially complete — see findings)
- Review date: 2026-08-29
- Reviewer: ZCode feature-dev session; Decision Authority `YMY / Project Owner`

## Verification Evidence

| Check | Result |
| --- | --- |
| Backend full suite | **102 passed** (80 pre-F003 + 22 new generation tests), `ruff check src tests migrations` clean |
| Web suite | **22 passed** (16 pre-F003 + 6 new panel tests), ESLint clean, `tsc --noEmit` clean, `next build` success |
| Public E2E | 3 passed |
| Authenticated E2E (live stack) | **1 passed (1.3m)** — full journey incl. start generation → all lessons complete (real DeepSeek + real Celery Worker + MinIO) → DOCX download with filename assertion → brief v2 → stale banner |
| Migrations | `c2f7d94e1a6b` (3 tables) + `e7a2c50b9d31` (trace FK freed) applied to test DB (automatic) and dev DB (manual) |

### Scenario coverage snapshot (TS → evidence)

- TS-001/002/003/004/005/006/007/008/009/010/011/012/013/014/015/016/017/018/019: covered by `apps/backend/tests/test_generation.py` (22 tests, integration/API/concurrency levels, real renderer + MinIO)
- TS-020/021/022: `apps/web/__tests__/generation-panel.test.tsx` (6 tests)
- TS-023: authenticated E2E extended and passing (live model)
- TS-024/025/026/027/028/029: NOT YET RUN — see M-1

## Self Review Findings

| Severity | Finding | Disposition |
| --- | --- | --- |
| Critical | none | — |
| High | none | — |
| Medium M-1 | Five of the six designed E2E journeys (TS-025 blocked start, TS-026 fault-instance resume, TS-027 supersession, TS-028 cap, TS-029 SSE reconnect) and the manual keyboard pass (TS-024) are not yet executed. Their behaviors ARE covered at integration/component level (TS-005/006/009/010 etc.), and the primary journey (TS-023) passes end to end, but the Test Design promises full code-path E2E evidence (owner-directed r2 revision). | Blocks `DONE`; complete before DONE or with owner-approved waiver recording residual risk. The fault-instance E2E profile (fake-adapter backend + small cap) requires a second backend instance and is the remaining T7 work. |
| Medium M-2 | During live E2E, the SSE stream was observed delivering only the first events before ending early (root cause not fully isolated; suspected proxy/stream lifecycle timing). Mitigation shipped: authoritative snapshot polling fallback (3s while active) + client auto-reconnect with `Last-Event-ID`; UI convergence verified in live E2E. Spec D4 semantics (PostgreSQL authoritative, replay read-only) are unaffected. | Root-cause investigation deferred to F006 observability; residual risk is cosmetic (progress update latency ≤3s), not correctness. |
| Low L-1 | Dev database requires manual `alembic upgrade head` after pulling new migrations (surfaced when brief-confirm 500'd against unmigrated dev DB). | Documented in `docs/TESTING.md` Commands. |
| Low L-2 | Repeated E2E runs accumulate projects and exhaust the 5-project quota, blocking creation with a proper 429 UI. | Operational note: clean leftover E2E projects before authenticated runs (behavior itself correct per design). |

## Spec Compliance

- All 16 ACs implemented; AC-001..AC-014, AC-016 verified by automated suites and live E2E as listed above; AC-015 verified by the deletion-cascade test (rows + MinIO binaries).
- Architecture boundaries respected: two new modules (`run_orchestration`, `artifact_production`) per the documented module table; Redis/Celery remain transport only; PostgreSQL owns run state, checkpoints, event log; supersession hooks extend the existing brief/blueprint confirm transactions.
- Superseded guard test from F002 updated to the new contract (generation surface now exists and is gated), recorded in `tests/test_blueprint.py`.

## Documentation Sync

- `docs/API.md`: SSE open item RESOLVED (F003 D4).
- `docs/DATABASE.md`: trace polymorphism + F003 tables recorded.
- `docs/TESTING.md`: dev DB migration command added; E2E gate note updated.
- `specs/ROADMAP.md`, `STAGE.md`, Issue #6: synchronized at delivery.
- No AGENTS/ADR changes required (no new L3 decision; MCP-compatible tool definitions follow ADR-0004's existing pattern).

## Conclusion

Implementation complete and verified at every automated level including one full live-stack E2E. `Roadmap Status: REVIEW` with `READY FOR PR`; `DONE` remains blocked by M-1 (remaining E2E journeys + keyboard pass) per the Test Design's owner-directed full code-path E2E coverage.

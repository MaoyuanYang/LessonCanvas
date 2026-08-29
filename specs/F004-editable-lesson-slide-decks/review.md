# Review: F004 Editable Lesson Slide Decks

## Metadata

- Spec: `specs/F004-editable-lesson-slide-decks/spec.md` @ `b913da61ec40` (SPEC READY PASS)
- UX/UI: `specs/F004-editable-lesson-slide-decks/ux-ui.md` @ `ux-ui-f004-r1` / `05e5748c9a4d` (UI READY PASS)
- Test Design: `specs/F004-editable-lesson-slide-decks/test-design.md` @ `test-design-f004-r1` / `4afef155b09f` + Execution Evidence Snapshot (TEST DESIGN READY PASS)
- Plan: `specs/F004-editable-lesson-slide-decks/plan.md` (T0..T7 checked; T8 this review)
- Review performed by ZCode feature-dev session (YMY / Project Owner driving), 2026-08-30

## Verification Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Backend suite | PASS | 124 tests passed (102 pre-existing + 22 new deck tests), incl. prerequisite gate, idempotent/concurrent start, checkpoint resume with model-call accounting (9 calls asserted), cap, supersession, SSE `Last-Event-ID` replay, non-disclosing download, injection inertness, deletion cascade |
| Backend lint | PASS | `ruff check src tests migrations` clean |
| Web suite | PASS | 30 tests passed (22 pre-existing + 8 new deck-panel tests); F003 generation-panel tests unchanged and green (TS-023) |
| Web lint/type/build | PASS | eslint, `tsc --noEmit`, `next build` clean |
| Deck E2E (fault stack) | PASS 2/2 attempted stable | TS-024 (keyboard pass), TS-025 (prerequisite gate) |
| Deck E2E (live stack) | PASS 3/3 | TS-030 (full happy path, real DeepSeek + real Worker), TS-027 (deck supersession), TS-029 (reconnect/reload) |
| Manual Office smoke | PASS | PowerPoint 16.0 opens the rendered deck without repair; 8 slides, 15 non-empty editable text frames, speaker notes present (TS-031) |

## Self Review Findings

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| M-1 | Medium | Deck E2E journeys TS-026 (partial failure + scoped resume) and TS-028 (cap exhaustion) are environment-blocked: the shared blueprint decision-modal stage intermittently hangs under degraded Clerk dev-instance sessions (page-level auth alert; F003's unchanged TS-026/TS-028 journeys show the same hang tonight, so the cause is environmental, not F004 code). | Residual for delivery decision: substitute coverage is green and automated (backend integration: transient resume with call accounting + cap preservation; component: partial-failure reasons, scoped resume modal, capped banner, downloads). Resume condition: re-run the two journeys when Clerk dev-instance auth is stable (daytime), mirroring how F003's original journeys were executed. |
| M-2 | Low | During failed live E2E attempts, a `StaleDataError` on `slide_deck_artifacts` was observed when the test timeout's project deletion raced an in-flight lesson update; the task settled via bounded retry and finally `missing_run`. | No product defect for normal operation (deletion mid-run is an E2E teardown artifact; no ready artifact was ever recorded without a binary). Noted for F006/F011 run-teardown semantics. |
| M-3 | Low (resolved) | The first live-stack execution exposed a real defect: live-model decks failed structural validation because stage-slide titles carried the writer's natural headings, not the fixed grammar prefix (the fake adapter happened to comply). | Fixed: the renderer now owns the structural `教学过程·` prefix exactly as the DOCX renderer owns section headings; the fake adapter switched to natural headings to mirror live behavior. Verified by live probe + green TS-030. |
| L-1 | Low | E2E infrastructure notes for reproducibility: Windows Celery must run `--pool=solo`; the web target for E2E should be a production build (`next start`) — the dev server's hot reload destabilized journeys; quota orphans from timed-out journeys must be cleaned between runs. | Recorded here; no product change. |

## Spec Compliance

- AC-001..AC-018 implemented and verified: AC-001/002/003/004/005/006/007/008/009/010/011/012/013/014/015/016/017/018 all have automated evidence (see test-design.md Acceptance Traceability + Execution Evidence Snapshot); the primary user journey additionally proven live end to end (TS-030).
- Spec decisions honored: D1 grammar enforced by the renderer; D2 per-deck checkpoints (resume accounting test); D3 prerequisite gate (integration + E2E TS-025); D4 SSE replay (API test + live TS-029); D5 taxonomy (provider terminal/partial tests); D6 specialists (traces asserted); D7 structural validation incl. editability (negatives + PowerPoint smoke); D8 python-pptx behind MCP-compatible definitions in `pptx_tools.py`; D9 no browser preview, structure summary in UI (component tests).

## Architecture and Boundary Review

- `generation_runs` gained `artifact_kind` + `prerequisite_run_id` with the identity constraint extended (one migration, additive; existing F003 suites green unchanged).
- Deck workflow (`deck_graph.py`) mirrors the F003 graph; supersession hooks cover both kinds without change (verified by deck supersession tests + live TS-027).
- Trace, event log, storage, and deletion cascade reused; deck binaries under the same workspace/project/run-scoped keys with `.pptx` extension.
- Web: shared `artifact-run.tsx` components consumed by both panels (D-DECKDS promotion), F003 suite unchanged (TS-023).

## Documentation Sync

- `docs/DATABASE.md`: slide-deck artifact table and run-kind identity noted.
- `docs/API.md`: deck endpoints noted as F004 Feature contract (pattern-consistent with F003).
- `docs/TESTING.md`: deck suite names and dual-instance E2E profile updated.
- `docs/DESIGN_SYSTEM.md`: D-DECKDS promotion recorded (shared artifact progress list + run outcome banners).
- `specs/ROADMAP.md`, `STAGE.md`, Issue #8: status synchronized at review/delivery.
- No changes needed: `docs/ARCHITECTURE.md` (module boundaries unchanged), `docs/FRONTEND.md`/`docs/UX.md`/`docs/UI.md` (no new conventions beyond the recorded promotion), `README.md`/`AGENTS.md` (commands unchanged).

## Conclusion / Delivery Status

Implementation complete; verification green (124 backend + 30 web + lint/type/build + 5 deck E2E journeys across fault and live stacks + Office smoke). One medium residual (M-1: two deck E2E journeys environment-blocked with automated substitute coverage) is presented to the Decision Authority for the delivery decision: authorize PR with M-1 tracked as a resume-condition residual, or require the two journeys green first.

`Roadmap Status: REVIEW` — awaiting delivery authorization.

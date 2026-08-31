# Review: F005 Lesson Exercises and Answers

## Inputs

- Spec: `specs/F005-lesson-exercises-and-answers/spec.md` @ SPEC READY `41b391751a33`
- UX/UI: `ux-ui-f005-r1` / approved content `78923f6468b7`
- Test Design: `test-design-f005-r1` / `29b9ad5c42d2` + Execution Evidence Snapshot (2026-08-31)
- Plan: `specs/F005-lesson-exercises-and-answers/plan.md` (T0–T8 complete)
- Reviewer: ZCode feature-dev session (self review); Decision Authority `YMY / Project Owner`
- Date: 2026-08-31

## Verification Summary

| Check | Result |
| --- | --- |
| Backend suite | 150 passed (124 pre-existing unchanged + 26 exercise incl. regression for the live defect) |
| Backend lint | `ruff check src tests migrations` clean |
| Web suite | 39 passed (30 pre-existing unchanged + 9 exercise-panel) |
| Web lint / typecheck / build | eslint clean / `tsc --noEmit` clean / `next build` succeeded |
| Migration | `d5a9c1f3b7e4` applied to test DB (session fixture) and dev DB; additive only (nullable `difficulty` + `exercise_artifacts`) |
| E2E | 7/7 journeys green: fault TS-024/025/026, small-cap TS-028, live TS-027/029/030 (real DeepSeek + real Worker) |
| Office smoke | TS-031 Word 16.0 COM open over all 12 files of the TS-030 pairs — no repair, editable text, correct titles |

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| H-1 | High (fixed) | Live-model defect: multi-line writing-task reference answers broke the pairing validator's first-line-anchored numbered-entry regex (`(.*)$`), falsely reporting `missing answers: [N]` and failing TS-030 lessons deterministically for essay-style items | Fixed in `exercise_docx_tools.py`: the anchor requires only the leading `N.` and captures across newlines (DOTALL); renderer unchanged; regression test added; all captured live drafts replay green; full backend suite re-verified after the fix |
| M-1 | Medium (residual, environment) | TS-025 hit an intermittent Clerk dev-instance session hang at the blueprint stage (page-level auth alert) — the same class as F004's owner-accepted M-1 | Re-run passed (17.5 s); substitute automated coverage exists regardless (backend prerequisite-gate tests + panel component tests); watch condition unchanged: re-run under stable auth if it recurs |
| M-2 | Medium (recorded deviation) | Plan's Test Execution Plan table named a real-Worker fault profile; execution used the F003 recorded profile — fake adapter + **eager** tasks — because real-Worker Celery retries insert two 180 s default delays that exceed journey budgets (the exact trap behind F004's unresolved TS-026/TS-028 residuals) | Recorded in the Execution Evidence Snapshot; TQ-002 wording ("Reuse the F003 dual-instance pattern unchanged") is satisfied by the eager profile; no Spec or Test Design change |
| M-3 | Medium (recorded deviation) | Plan T2 listed fake-script markers `EXERCISE_MISSING_ANSWER`/`EXERCISE_ORPHAN_ANSWER`; the renderer owns numbering and derives answers from the same items, so those negatives are unreachable from the model path | Implemented model-reachable markers `EXERCISE_EMPTY_ANSWER` and `EXERCISE_TOO_FEW`; orphan/missing/non-contiguous/corrupt negatives are covered by validator-level fixtures (TS-012 asserts each reason string); coverage is equivalent, recorded here |
| L-1 | Low (environment hygiene) | Leftover E2E projects from earlier runs filled the workspace project quota (`POST /projects` 429) and blocked journeys mid-run | Cascade-deleted the synthetic leftovers before the passing runs; non-synthetic projects untouched; no code change |

No Critical findings. No High findings remain open (H-1 fixed and re-verified).

## Requirement Conformance

- AC-001..AC-020: all implemented with automated evidence (backend 26 tests, web 9 tests, 7 E2E journeys, Word smoke); per-scenario evidence in the Test Design Execution Evidence Snapshot.
- Spec D1–D9 respected: catalog grammar (AC-020 asserted), pair-as-checkpoint (TS-003/004), lesson-plan prerequisite without deck requirement (TS-001/TS-025), inherited SSE/event contract (TS-007/029), inherited failure taxonomy (TS-005/010/016), three-specialist split with lesson-plan + objectives + tier as primary input (TS-013), deterministic pairing validation with the live defect fixed (TS-002/012/031), python-docx behind MCP-compatible definitions (tool definitions + dispatcher), difficulty write-once binding (TS-001/015/019 and the duplicate-start UI/API tests).
- Untrusted-input, non-disclosure, and deletion obligations hold (TS-018/019/014).

## Documentation Sync Record

- `docs/DATABASE.md`: Open Items — exercise artifact kind/table + run difficulty recorded (F005 migration `d5a9c1f3b7e4`).
- `docs/TESTING.md`: E2E scope line extended to exercises.
- `docs/DESIGN_SYSTEM.md`: shared artifact-run row updated — F005 is the recorded third consumer.
- ROADMAP / STAGE / Issue #10 synchronized to `REVIEW`.
- UX.md / UI.md / FRONTEND.md / API.md / ARCHITECTURE.md: unchanged — no project-level convention changed; concrete endpoints and states live in the F005 Spec per the Feature Contract Rule.

## Delivery State

- `READY FOR PR` — awaiting separately authorized commit / push / PR / merge (per AGENTS.md each remote action needs explicit user authorization).

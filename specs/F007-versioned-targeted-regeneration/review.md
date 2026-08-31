# Review: F007 Versioned Targeted Regeneration

- Work item: [GitHub Issue #14](https://github.com/MaoyuanYang/LessonCanvas/issues/14)
- Reviewed branch: `feature/F007-versioned-targeted-regeneration` (working tree @ review time)
- Reviewed inputs: Spec @ `fb351456a2ee`, UX/UI @ `ux-ui-f007-r1` / `97597ad3c608`, Test Design @ `test-design-f007-r1` / `69c9d0532f7a`, Plan (T0–T6)
- Review date: 2026-08-31 · Reviewer: ZCode feature-dev session (YMY / Project Owner driving)

## Verification Summary

- Backend: full suite green (`uv run pytest`, exit 0) incl. 11-test `tests/test_regeneration.py` (matrix classes, preview API + stale conflict, scoped start/idempotency/concurrency with retention checksums, structural add/remove via the full brief-revision + re-planning path, coverage gate, scoped resume with scoped-only call accounting, transition payload, authorization, read-only + deletion, concurrent-start convergence); `ruff check src tests migrations` clean; migration `f007b4d8e6f2` additive (up/down proven on dev + test DBs).
- Web: 51/51 tests (4 new `regeneration-panels.test.tsx`; all pre-existing suites unchanged and green), `eslint` 0 errors (4 pre-existing F006 warnings), `tsc --noEmit` clean, `next build` clean.
- E2E (Playwright, production build): fault stack TS-014 (revise → embedded impact → confirm → scoped regeneration with 沿用 provenance → comparison verdicts) 21.7s and TS-016 (keyboard-only pass incl. tab focus, Enter navigation, scoped start) 23.2s; live stack TS-015 (real DeepSeek + real Worker: full unit → lesson-level revision → scoped regeneration completes for the affected lesson only with retained lessons untouched) 1.3m.

## Spec Compliance

- AC-001..AC-014 implemented and verified per `test-design.md` traceability and the Execution Evidence Snapshot below.
- Spec decisions honored: D1 field-level conservative matrix (verified per class incl. citations-as-non-intent and uncertainty widening); D2 teacher-triggered per family with generalized coverage (retained plans never cover plan-affected lessons — corrected during delivery, see M-1); D3 checkpoint supersession unchanged; D4 version-seeded revision drafts (existing draft machinery + seed action); D5 retention with original ownership, checksums, and downloads, never re-billed (model-call accounting asserted); D6 structured comparison (embedded transition impact + verdict table + old/new status); D7 stale-base conflicts.

## Findings

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| M-1 | Medium (fixed during delivery) | The first coverage-gate implementation accepted a retained prior plan for a lesson the matrix itself marked plan-affected — a stale-intent plan would have wrongly satisfied the deck/exercise prerequisite (caught by TS-008 before any delivery). | Fixed: retained plans only cover lessons outside the plan-family affected scope (`service._plan_coverage`); regression covered by `test_coverage_gate_for_targeted_decks`. |
| M-2 | Medium (design correction during delivery) | The comparison view initially fetched `GET /impact` on demand, but post-confirmation there is no pending draft, so the preview degraded to 未检测到实质变更 (first E2E run exposed it; an earlier assertion had passed against the verdict table for the wrong reason). | Fixed: the transition payload embeds its impact and the comparison view renders it directly; `GET /impact` remains the pre-confirmation preview at the blueprint stage (its intended surface per ux-ui.md D-IMPACT). |
| M-3 | Medium (behavioral gap found by E2E, fixed) | Family snapshot lookups returned the latest run of any version pair, so a settled old-pair run masked the new pair's start surface after a transition. | Fixed with the pair-aware current-run rule: the run bound to the current confirmed pair wins; an older-pair run is visible only while active or superseded (preserving the F003 superseded-banner contract); F003–F005 suites re-verified green unchanged. |
| L-1 | Low | Blueprint drafts do not carry `citations` (grounding metadata), so a naive field diff classified a seeded revision as full-scope. | Matrix ignores citations as non-intent provenance (documented in `impact.py`); unit-covered. |
| L-2 | Low (environment) | One TS-016 first run hit the known Clerk/session + stale-build class (web server not restarted after rebuild) and one re-opened waivable finding needed a decision before re-confirmation. | Journey hardened (decision loop in the revision flow; server restart discipline recorded); both journeys pass deterministically. The F004 M-2 fast-fail hardening remains routed to F011 (not F007 scope; re-confirmed). |
| L-3 | Low (hygiene) | The evidence narration token-capture (F006 L-1) and Zod-vs-interfaces convention (F006 M-3) residuals remain open under their recorded owners (F009 / F008+). | Unchanged; listed for continuity. |

No Critical findings; no High findings; all Medium findings fixed and re-verified within the branch.

## Architecture / Boundary Notes

- Impact computation is a pure function in `run_orchestration/impact.py`; transition/retention are read-time projections in `transition.py`; targeted scope is persisted once at run creation (`generation_runs.scope_json`); no new table, service, cache, or queue.
- Retention joins run inside snapshots only for scoped runs; settled older runs never mask new-pair surfaces (M-3 rule).
- The D-REVSEED button lives in the blueprint panel; in the current F002 panel a confirmed version retains an editable seeded draft, so the button appears only in the no-draft state and seeds from `confirmed_payload` — both paths converge on the ordinary draft machinery.

## Residuals

- L-2 environment class and F004 M-2 fast-fail (F011) unchanged.
- F006 L-1 (narration stream tokens) and M-3 (Zod convention) remain under F009/F008+ as recorded.

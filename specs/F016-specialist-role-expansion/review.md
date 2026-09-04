# F016 Self Review — Specialist Role Expansion

- Review ID: `review-f016-r1`
- Reviewed: working tree of `feature/F016-specialist-role-expansion` (plan `plan-f016-r1`, T0–T7 + T9 complete; T8 live evidence deferred to delivery under separate owner authorization)
- Inputs: Spec @ SPEC READY (`f37d7519f8f9`), ux-ui `519b499459a0`, test-design `7c71aa3aa167`, plan `57c8356599fc`

## AC → evidence table

| AC | Evidence |
| --- | --- |
| AC-001 analysis or honest failure, labeled consumption, deletion | `test_source_analysis.py` TS-001/002/004/005 (12+1 tests incl. TS-024 backfill); deletion sweep registered (`deletion.py` + cascade verified) |
| AC-002 plans design→write→review; decks/exercises write→review; per-stage trace | `test_designer_stage.py` (stage order + attribution + 18-call accounting), `test_review_stage.py` (three families), evidence chips in `specialist-stage-surfaces.test.tsx`, E2E TS-021 |
| AC-003 severity findings, ≤1 revise round, honest terminal states | `test_review_stage.py` TS-009/010/011 (clean/minor-only/revise-pass/failed-after-revise with stage-named reason and no render) |
| AC-004 deterministic validation unchanged and mandatory; intent untouched | `test_review_stage.py::test_review_pass_never_bypasses_structural_validation` (DECK_TOO_LONG passes review, structure fails it); version-binding assertions in the revise-pass test |
| AC-005 formula caps + source-analysis bound; per-stage cost visible | `test_specialist_stages.py` cap formula tests; `compute_model_call_cap` wired at all three run creations; mid-stage exhaustion keeps capped semantics (updated `test_cap_exhaustion_*`); evidence panel cost columns reused; analysis cost line on its own surface |
| AC-006 F009 signature + stage/revise scenarios | `test_technical_evaluation.py::test_ts016_*`/`test_ts017_*` + report-contract test now covering `fault:design_invalid`/`fault:review_fail` with blocking `C-STAGE-1`/`C-DESIGN-1`/`C-REVIEW-1` |

## Findings (found and fixed during review)

- **SF-1 (fixed with test)**: the three generation graphs each defined a private `CapExhaustedError`; the shared F016 review/design stages raised the plans-graph class, so a deck/exercise cap exhaustion mid-review escaped the caller's catch and surfaced as an unhandled LangGraph error instead of `capped_failure`. Fixed by defining one shared class in `run_orchestration/caps.py` and aliasing it in all three graphs; the updated deck/exercise cap tests (`model_call_cap = 2`) pin the behavior.
- **SF-2 (fixed with test)**: the fake reviewer always emitted dimension `objective_coverage`, which the decks/exercises dimension whitelist (`plan_coverage`) silently dropped — masking the revise path for those families. The fake now chooses the family-appropriate dimension; `test_deck_severe_findings_revise_path` would have caught it and now passes.
- **SF-3 (fixed)**: `evaluate_specialist_stages` read the lesson index only from top-level payload keys or `payload["lesson"]`, missing the `payload["prompt"]["lesson"]` nesting of model-stage events — the criterion failed every full-pipeline pass with `missing_*` violations. Fixed with a nesting-aware extractor.
- **SF-4 (fixed)**: the C-STAGE-1 stage-order check compared trace-event timestamps, which tie at microsecond granularity and scramble intra-lesson order; the check now uses the authoritative monotonic `RunEvent.seq` (`reviewing`/`revising` strictly before `rendering`).
- **SF-5 (fixed)**: `execute_worker_provider_failure` computed `expected_model_calls` with a pre-F016 `+1 per incomplete lesson`; resumed lessons now bill write+review (design reused without re-billing). The expectation is computed from the faulted-phase artifact state before the resume executes (an earlier placement re-read settled-complete rows and computed a wrong resume cost).
- **SF-6 (fixed with test)**: the multiaccount journey's bounded-spend assertion required every run's `model_call_cap` to stay at or below the flat `max_model_calls_per_run`; F016's formula caps legitimately exceed the flat value for units above the floor (6 lessons → 32 > 20), failing both full-suite runs deterministically. The assertion now checks calls ≤ cap and cap ≥ flat floor per the F016 D5 contract; the journey passes again (final full suite 622 passed + 4 skipped, exit 0).

## Maintainer judgments recorded

- The formula caps bound the approved stage set (plans 5/lesson, decks/exercises 4/lesson + slack 2, flat floor 20). Rare double-failure paths (a design corrective retry AND a draft-validation retry on the same lesson) can reach up to ~10 calls/lesson and may exhaust the cap — settling honestly as `capped_failure` with per-stage accounting intact, which is the same contract the pre-F016 flat cap had for its own retry paths (slack absorbs single retries).
- Review findings persist the LATEST round per artifact (spec wording); the revise round's triggering findings remain inspectable in the round-1 evidence event payload and its trace, and the round caption discloses which round the shown findings belong to.
- The E2E journey does not assert live narration lines: the eager deterministic backend settles a run before the SSE stream opens, so narration sentences are covered by exported-mapper component tests instead (`specialist-stage-surfaces.test.tsx`).

## Residuals (owner-visible)

- **M-1 (pre-existing, environment class)**: `tests/test_guardrails_multiaccount_journey.py::test_multiaccount_journey_isolation_limits_idempotency_and_bounded_spend` is intermittently flaky independent of F016 — reproduced failing on unmodified stashed `main` in a standalone run (symptom: extra `GenerationRun` rows from its concurrent-thread journeys; the deterministic full-suite failures were SF-6, now fixed, and the final full-suite run is green). The test has no truncation fixture of its own and asserts a global row count, making it order- and timing-sensitive. Recommend a follow-up giving the journey a `db_session`-based isolation fixture; not introduced by F016.
- **M-2 (environment, pre-existing)**: the local machine's 8000/3000 ports are the deployed F012 stack and `apps/backend/.env` credentials are stale against it; backend verification runs with `infra/deploy.env` overrides against the isolated `lessoncanvas_test` database, and the deterministic E2E stack runs on free ports (API 8010 / web 3100) with `LESSONCANVAS_CORS_ALLOWED_ORIGINS` extended to the dev web origin. An owner-side `.env` refresh removes the overrides.
- **M-3 (deferred to delivery)**: T8 live evidence (real-DeepSeek source-analysis/design/review journey + full F009 six-pass re-baseline under the new stage set) awaits separate owner authorization per the delivery flow; until then the live-quality claim stays unmade.

## Documentation sync

README (specialist division-of-labor capability row), ARCHITECTURE (Artifact Production collaboration note + hosted-model row), API (F016 open-item: analysis object, retry endpoint, artifact payload/status additions, seven trace event kinds, formula caps, signature + scenarios), DATABASE (F016 migration entry), UX (stage/review honesty principle), TESTING (F016 suites, E2E recipe, environment notes). AGENTS unchanged (no command or module-ownership change).

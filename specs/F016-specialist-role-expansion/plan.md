# F016 Implementation Plan — Specialist Role Expansion

- Plan ID: `plan-f016-r1`
- Inputs (Gate-validated): Spec (SPEC READY PASS 2026-09-04 @ `f37d7519f8f9`), UX/UI @ `ux-ui-f016-r1` / `519b499459a0` (`UI READY`, 2026-09-04), Test Design @ `test-design-f016-r1` (TS-001..TS-024)
- This Plan answers only how to implement; requirements live in the Spec. It adds no rule, no Scope, and no contract change.

## Architecture fit

- Source analysis lives in Sources and Grounding (`modules/sources_grounding/analysis.py`): prompt + server-side normalization + persistence to the new `source_analyses` table; a Celery task (`lessoncanvas.analyze_source`) enqueued at parse settlement (D1) and a source-scoped retry endpoint; latest-wins with a one-in-flight guard; deletion-sweep registration. Discovery/Planning consume a bounded labeled digest via a shared assembler (subordinate context; module rule respected — Sources and Grounding never owns intent).
- Designer and reviewer stages are new nodes inside the existing three generation graphs (`artifact_production/graph.py`, `deck_graph.py`, `exercise_graph.py`) following the established per-lesson loop: plans assemble → (design → write → review [→ revise → re-review]) → render → validate; decks/exercises keep their current inputs and gain (write → review [→ revise → re-review]) → render → validate. Every stage call reserves a run slot through `reserve_model_call` and commits its own trace event through the existing `record_trace`; per-lesson checkpoint semantics and failure taxonomy are unchanged.
- Formula caps are computed at run creation in `run_orchestration/service.py` from the lesson count (settings-driven multipliers/slack with the flat settings as floor). Memory injection reuses the F013 snapshot mechanism for designer and reviewer payloads (D6 owner decision).
- F009: `technical_evaluation/service.py:model_config_snapshot()` gains `stage_set`; the pass pins a source-analysis state snapshot; `criteria.py` gains the blocking stage criterion; `harness.py` gains `fault:design_invalid` / `fault:review_fail` executors and settles seeded-source analyses before passes.
- Web: label-registry entries, review-round chips, `reviewing` status, narration sentences, findings/design read-only regions, sources analysis region — composition only (UX U1–U5).
- Deploy: one additive migration + an idempotent analysis backfill step appended to `infra/scripts/deploy.sh` (F014 precedent).

## Data and migration

- One migration: `source_analyses` (id, project_id, source_id, status, payload_json, error, model, latency_ms, prompt_tokens, completion_tokens, cost_usd, updated_at) + `lesson_plan_artifacts.design_json` / `design_status` / design trace fields + review columns (`review_findings_json`, `review_rounds`, `review_outcome`) on all three artifact tables. No destructive change; existing runs/artifacts read with null review fields (pre-F016 states render unchanged).

## Settings

- `analysis_digest_budget_chars: int = 2000` (discovery/planning consumption budget); `design_activity_min/max`, `design_timing_min/max_minutes` bounds; `model_call_cap_plans_per_lesson: int = 5`, `model_call_cap_decks_per_lesson: int = 4`, `model_call_cap_exercises_per_lesson: int = 4`, `model_call_cap_slack: int = 2` (existing flat caps stay as floor, D5). All non-secret, env-overridable, safe defaults.

## Tasks (vertical slices)

- **T0 — Branch, settings, adapter kinds**: branch `feature/F016-specialist-role-expansion`; settings keys; fake-adapter scripting for `source_analysis`, `generation_design_lesson`, `generation_review_*`, `generation_revise_*` with fault markers (`ANALYSIS_FAIL`, `DESIGN_INVALID`, `REVIEW_SEVERE_TWICE`, `REVIEW_PARSE_FAIL`); cap-formula unit tests. Tests: TS-014 (formula part). Proof: full suite green with no call site using the new kinds yet.
- **T1 — Source-analysis slice**: migration, analysis module (prompt/normalization/persistence), Celery task + parse-settlement enqueue, retry endpoint + one-in-flight, telemetry honesty, deletion sweep, discovery/planning labeled consumption with budget + disclosure states. Tests: TS-001..TS-005, TS-015. Proof: an uploaded source shows an analysis (or honest failure) with its cost line and feeds planning payloads.
- **T2 — Designer slice (plans)**: design node before the writer, design validation (objective ids/timing/activity bounds) with one corrective retry, artifact-row storage, writer payload binding, memory injection. Tests: TS-006..TS-008. Proof: plans trace shows design and write stages separately; checkpoint semantics intact.
- **T3 — Reviewer slices (all three families)**: reviewer nodes after the writer draft, findings schema + severity normalization, severity-gated revise + re-review, `reviewing` status, failed-after-revise terminal naming, reviewer parse-failure retry path, no-bypass assertions, reviewer memory (D6), deck/exercise input-contract equivalence assertions. Tests: TS-009..TS-013. Proof: all review terminal states covered deterministically in the three families.
- **T4 — Caps wiring + F009 integration**: formula caps at run creation with floor; reserve calls on every new stage; `stage_set` signature + analysis-state snapshot; blocking stage criterion; `fault:design_invalid` / `fault:review_fail` harness scenarios; harness analysis-settle step. Tests: TS-014 (integration), TS-016, TS-017. Proof: F009 deterministic scenarios green; old passes visibly incomparable.
- **T5 — Web surfaces**: `EVIDENCE_EVENT_LABELS` + review-round chips; `ARTIFACT_STATUS_LABELS` `reviewing`; narration sentences in the three family mappers; findings/design read-only regions; sources analysis badge + expandable region + gated retry; `EVALUATION_CRITERION_LABELS` new criterion + `C-TOOL-1` fix. Tests: TS-018..TS-020. Proof: web suite green (`vitest` + `tsc` + `eslint`).
- **T6 — E2E journey**: deterministic browser plans journey with scripted design + severe-then-revised review; evidence/finding/design assertions; keyboard + 420px. Tests: TS-021. Proof: journey green on the deterministic stack.
- **T7 — Deploy backfill**: idempotent deploy-time analysis backfill step + script test path. Tests: TS-024. Proof: two consecutive backfill runs settle every ready source exactly once.
- **T8 — Live evidence (owner-authorized at execution)**: TS-022 real-DeepSeek journey + full F009 six-pass live re-baseline; evidence JSON under the spec directory.
- **T9 — Regression, review, docs sync**: TS-023 full sweep (twice for stateful suites); Self Review (`review.md`); documentation sync — ARCHITECTURE (specialist stage composition under orchestrated authority), API (new trace event kinds + payload/status additions + retry endpoint), DATABASE (`source_analyses` + artifact columns), UX (stage/review honesty principle), TESTING (new suites, E2E, live recipe, credential-override environment note), README only where the specialist claim reads stale; ROADMAP + Issue #32 status sync (remote action separately authorized). AGENTS only if commands change (they do not).

## Transaction / consistency notes

- Analysis latest-wins writes are single-row upserts; the one-in-flight guard is a conditional status update, so a crashed task leaves a visible `analyzing` state that the retry path can supersede honestly (retry allowed after a staleness bound).
- Review/revise rounds run inside the existing per-lesson processing step: every stage call commits its trace event and run-counter increment before the next call, so an interruption leaves a truthful partial trace and per-lesson recovery resumes exactly like today (completed lessons untouched).
- No run bills past its cap: every new stage reserves through `reserve_model_call`; exhaustion mid-stage routes to the existing capped-failure terminal with per-stage accounting preserved.

## Verification cadence

- Per task: the task's scenario tests + the smallest related existing suites (`uv run pytest tests/test_<area>.py`); full backend suite at T3, T4, T9; web suite at T5 and T9; E2E at T6; final sweep twice at T9.
- All deterministic runs use the recorded environment overrides (isolated `lessoncanvas_test` on the running Postgres with `infra/deploy.env` credentials) until the owner refreshes `apps/backend/.env`.

## Gate Record: PLAN APPROVED

- Status: `PASS`
- Validation time: 2026-09-04
- Decision Authority: `YMY / Project Owner` — approved together with `test-design-f016-r1` via interactive session on 2026-09-04 (explicit TEST DESIGN READY + Plan approval)
- Artifact hash: `plan-f016-r1` @ `57c8356599fc`

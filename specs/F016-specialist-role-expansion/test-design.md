# Feature Test Design: F016 Specialist Role Expansion

## Metadata

- Spec/Issue: `specs/F016-specialist-role-expansion/spec.md` / [GitHub Issue #32](https://github.com/MaoyuanYang/LessonCanvas/issues/32)
- Validated inputs: Spec (SPEC READY PASS 2026-09-04 @ `f37d7519f8f9`), UX/UI @ `ux-ui-f016-r1` / `519b499459a0` (`UI READY`, 2026-09-04)
- Test Design revision: `test-design-f016-r1`
- Coverage scope: recommended risk-based scope (owner-confirmed scope class of F013–F015): functional happy/alternative/boundary/error-recovery per new stage, injection defense, cap/cost accounting, F009 evaluation integration, observability/trace contract, UI label/chip/region interaction, deterministic E2E, owner-authorized live evidence at delivery. Excluded with reasons: live provider quality variance in CI `N/A - fake adapter scripts stage outcomes in CI; live quality evidenced once in TS-022`; load/stress `N/A - bounded by formula caps and one-analysis-per-source; no perf infrastructure`; fuzz/property-based `N/A - severity/round/terminal states enumerated deterministically`; visual regression `N/A - no infrastructure; component + E2E cover acceptance`; cross-browser `N/A - repo convention chromium`; i18n `N/A - zh-Hans inline copy per repo convention`; deployment/rollback `N/A - one additive migration + idempotent deploy backfill covered deterministically in TS-024`.
- Environments: (a) deterministic developer stack (fake adapter + eager tasks + isolated `lessoncanvas_test` on the running Postgres, credential overrides recorded in the SPEC READY baseline note); (b) deterministic browser stack for E2E; (c) live stack (real DeepSeek) only for TS-022 under separate owner authorization.
- `TEST DESIGN READY` Status: `PASS` (see Gate Record)

## Gate Record: TEST DESIGN READY

- Status: `PASS`
- Validation time: 2026-09-04
- Decision Authority: `YMY / Project Owner` — approved together with `plan-f016-r1` via interactive session on 2026-09-04 (explicit TEST DESIGN READY + Plan approval)
- Artifact hash: `test-design-f016-r1` @ `7c71aa3aa167`
- Checklist: every AC mapped to ≥1 scenario; every Spec decision D1–D7 traced; every severity/round/terminal state covered; untrusted-input discipline covered for analyses, design, and findings; F009 comparability + stage criterion + fault scenarios covered; cap/cost honesty covered for run stages and source analysis; risk register complete; deterministic/live separation explicit; environments realistic; no Critical coverage gap

## Risk Register and Scenario Selection

| Risk / behavior | Impact | Scenario(s) |
| --- | --- | --- |
| Analysis never triggers, or blocks the source pipeline | Grounding context missing silently (AC-001) | TS-001, TS-002, TS-024 |
| Analysis output trusted blindly (injection via source text → analysis → prompts) | Injection discipline breach | TS-003 |
| Analyses consumed without disclosure or budget | Dishonest subordinate context | TS-004 |
| Analyses survive workspace deletion | Privacy boundary breach (AC-001) | TS-005 |
| Design stage skipped, untraced, or not consumed by the writer | Division-of-labor claim false (AC-002) | TS-006 |
| Invalid design accepted or crashes the lesson | Wrong grounding vs objectives | TS-007 |
| Design/memory content escapes untrusted-input discipline | Injection breach | TS-003, TS-008 |
| Minor findings trigger revise, or severe findings pass | Severity-gate rule broken (AC-003, D3) | TS-009, TS-010, TS-011 |
| Revise loop unbounded or re-billed past cap | Cost-honesty breach | TS-010, TS-011, TS-014 |
| Deck/exercise input contracts drift when review is added | Silent divergence from F004/F005 | TS-012 |
| Reviewer output unparseable treated as pass; review bypasses structural validation | False validation status (AC-004) | TS-013 |
| Formula caps wrong, or exhaustion mid-stage dishonest | Cap contract broken (AC-005, D5) | TS-014 |
| Source-analysis calls unbilled or double-billed | Cost-honesty breach | TS-015 |
| F009 passes compare across stage sets; stage absence unjudged | Evaluation honesty broken (AC-006, D7) | TS-016, TS-017 |
| UI mislabels stages/findings or offers editing | Teacher-visible honesty / D4 breach | TS-018, TS-019, TS-020 |
| Whole-flow integration broken end to end | AC-002/AC-003 unproven in product | TS-021 |
| Live stage quality unproven with real provider | Core claim unverified | TS-022 |
| Existing suites regress | Completed features broken | TS-023 |

Happy Path: TS-001/TS-006/TS-009/TS-021; Alternative/boundary: TS-004/TS-010/TS-012/TS-014/TS-015; Error/security: TS-002/TS-003/TS-007/TS-011/TS-013; Recovery: TS-002/TS-007/TS-010/TS-024; Observability: TS-006/TS-018/TS-019/TS-020; Evaluation: TS-016/TS-017; Live: TS-022; Regression: TS-023.

## Acceptance Traceability

| AC / Decision | Scenario(s) |
| --- | --- |
| AC-001 (structured analysis or honest failure, consumed as labeled context, deleted with workspace) | TS-001, TS-002, TS-004, TS-005 |
| AC-002 (plans design→write→review; decks/exercises write→review, per-stage trace) | TS-006, TS-012, TS-018, TS-020, TS-021 |
| AC-003 (severity findings, ≤1 revise round, honest terminal states) | TS-009, TS-010, TS-011, TS-013 |
| AC-004 (deterministic validation unchanged and mandatory; intent untouched) | TS-013 |
| AC-005 (formula caps + source-analysis bound; per-stage cost visible) | TS-014, TS-015, TS-018 |
| AC-006 (F009 stage-set signature + stage/revise scenario coverage) | TS-016, TS-017, TS-022 |
| D1 (parse-settlement async, latest-wins, one in flight) | TS-001, TS-002, TS-004, TS-024 |
| D2 (reviewer in all families, unchanged writer inputs) | TS-012 |
| D3 (severity-gated revise) | TS-009, TS-010, TS-011 |
| D4 (design evidence-visible only) | TS-020 |
| D5 (formula caps; upload-processing classification) | TS-014, TS-015 |
| D6 (designer + reviewer memory; none for source analysis) | TS-008, TS-012 |
| D7 (signature, criterion, faults, re-baseline) | TS-016, TS-017, TS-022 |

## Scenarios

### TS-001 — Source-analysis happy-path contract

Deterministic (eager task + fake adapter). Upload a source with scripted analysis content → parse settles → analysis task runs once → `source_analyses` row `ready` with normalized payload (topics, language points, suitability flags, key passages referencing existing chunk positions), bounded field lengths, telemetry recorded (model label, latency, tokens, cost; missing tokens ⇒ cost not recorded). Source list/detail payloads expose status + digest + telemetry. No TraceEvent row is created (not run-owned).

### TS-002 — Analysis failure, retry, one-in-flight, latest-wins

Scripted provider failure → visible `failed` state with stored reason; the source stays `ready`/usable; retry endpoint re-enqueues → success overwrites the row (latest-wins, old attempt telemetry replaced); a second trigger while `analyzing` is rejected by the one-in-flight rule with an explicit error; retry in read-only context is permission-denied.

### TS-003 — Analysis untrusted-input discipline

Hostile analysis output (injected instructions, oversized fields, bogus chunk references) is normalized/bounded server-side; chunk references that do not resolve are dropped; downstream discovery/planning payloads carry analyses only as labeled JSON user content; system prompts stay byte-identical with and without analyses (purity assertion, F015 precedent).

### TS-004 — Discovery/planning consumption with disclosure

With analyses ready, discovery and planning model-event payloads contain the labeled `source_analyses` section within the char budget (long digests trimmed); with none/failed analyses the payload carries `source_analyses_state` `none`/`partial` with reasons; runs proceed unchanged either way; analysis content never overrides confirmed brief/blueprint fields (patch attempts in analysis text are inert).

### TS-005 — Deletion completeness

Workspace/project deletion removes all `source_analyses` rows (registered in the F011 sweep); residual scan reports zero; retained ledger behavior unchanged.

### TS-006 — Designer stage contract (plans)

A plans run executes per lesson design → write with `model.generation_design_lesson` then `model.generation_write_lesson` trace events, each with role label, latency, tokens, estimated cost; the validated design is stored on the lesson-plan artifact row and appears in artifact payloads; the writer payload demonstrably contains the design (labeled); evidence read model counts the new stage in model-call stats.

### TS-007 — Design validation failure path

Scripted invalid design (unknown objective id, out-of-bounds timing/activity count) → one corrective retry; retry success continues the lesson; retry failure settles an honest per-lesson stage failure under the existing taxonomy with completed lessons preserved (checkpoint semantics unchanged).

### TS-008 — Designer memory injection + discipline

With confirmed memory records, the designer payload carries the budgeted `memory_context` (existing priority order; reviewer parity per D6 for run stages); memory content rides user payload only; hostile memory text planted into the design output is inert downstream (TS-003 class assertion at the writer boundary).

### TS-009 — Review pass incl. minor-only

Clean draft → review-passed with zero findings; minor-only draft → review-passed with findings recorded and disclosed, no revise round; `review_rounds` = 1; artifact proceeds to render/validate.

### TS-010 — Revise-then-pass

Severe findings in round 1 → revise event traced (`model.generation_revise_*`) carrying the labeled findings to the writer → revised draft → round-2 review passes → review-passed (after revise) with rounds = 2; total model calls for the lesson = design+write+review+revise+re-review (accounting asserted).

### TS-011 — Failed-after-revise

Severe findings in both rounds → the draft settles failed-after-revise; the artifact failure state names the review stage; no third round under any condition; run settles with existing per-lesson failure semantics; findings of the latest round remain visible.

### TS-012 — Decks/exercises review + unchanged contracts

Deck and exercise runs gain write → review (and revise path when severe) with the same findings schema; their writer input payloads are byte-equivalent to pre-F016 apart from the review-stage additions (no design consumption — D2); reviewer receives the budgeted memory context in all three families (D6); plan-coverage dimension maps to the prerequisite plan.

### TS-013 — Reviewer output failure + no-bypass

Unparseable/non-normalizable reviewer output → bounded retryable stage failure (never a silent pass); after any review outcome, rendering still runs and deterministic structural validation still gates completion (a draft that passed review but fails structure fails); confirmed brief/blueprint versions are unchanged by any review/revise activity.

### TS-014 — Formula caps and mid-stage exhaustion

Run creation computes plans cap `5L+2` (floor 20) and decks/exercises `4L+2` (floor 20); each new stage call reserves one slot; scripted exhaustion mid-review/revise → existing capped-failure semantics with per-stage accounting intact; no call bills past the cap (counter assertions).

### TS-015 — Source-analysis cost bound by construction

Analysis calls never touch run counters or run caps; each trigger performs exactly one model call; manual retry re-bills with the new attempt's telemetry disclosed; upload-processing classification holds (no new rate class created; existing upload quota path untouched).

### TS-016 — F009 signature extension

`model_config_snapshot()` contains `stage_set` with the per-family composition; evaluations created before F016 report `comparison_unavailable` against new ones through the existing mechanism; the pass pins the seeded sources' analysis-state snapshot; divergent analysis availability marks passes incomparable.

### TS-017 — Stage criterion + fault scenarios

The new blocking criterion passes full-stage traces and fails traces missing design/review events, with revise rounds > 1, or with review after render; `fault:design_invalid` and `fault:review_fail` harness scenarios complete deterministically with the expected honest terminal states and criterion outcomes.

### TS-018 — Web evidence-panel surfaces

Vitest: new event labels render; review/revise rows show the round chips (第 N 轮, 严重 X · 轻微 Y, 触发修订 / 修订后通过 / 修订后仍未通过); per-stage cost/latency/tokens render through existing columns; no chip appears on non-review events.

### TS-019 — Web sources-panel surfaces

Vitest + interaction: analysis badge states (待分析/分析中/已分析/分析失败); expandable region shows digest with chunk references and the cost line (约 $X（估算）/ 未记录); failed state shows reason + 重试分析 with permission and in-flight gating; readOnly hides the action.

### TS-020 — Web artifact/panel surfaces

Vitest: `reviewing` status label; narration sentences for design/review/revise/failed-after-revise across the three family mappers; findings region renders severity/dimension/message with round caption; plans design region renders read-only with the 查看说明 and no edit affordances (D4); failed-after-revise reason names the review stage.

### TS-021 — Deterministic E2E journey

Browser (chromium): full plans journey on the deterministic stack with scripted design + severe-then-revised review; teacher views per-lesson stage progress, evidence stage rows with costs, findings region, and the design region; keyboard-operable expanders; 420px spot check.

### TS-022 — Live evidence at delivery (owner-authorized at execution)

Real DeepSeek: one live unit journey exercising source analysis, design, review, and (if provider behavior permits a comparable seeding) the revise path honestly recorded otherwise; plus the full F009 six-pass live re-baseline under the new stage set with per-pass criterion judgment; evidence JSON under the spec directory.

### TS-023 — Full regression sweep

Backend `uv run pytest` + `uv run ruff check src tests migrations`; web `web:test` + `web:typecheck` + `web:lint`; second backend run for stateful stability; deck/exercise and discovery/planning suites unchanged in behavior (TS-012 contract assertions double as regression pins).

### TS-024 — Deploy-time idempotent analysis backfill

Backfill over ready sources lacking analyses analyzes each once; a second run is a no-op (skips settled rows); sources with failed analyses are not silently re-analyzed (manual retry only); deploy step ordering (F014 precedent) verified in the deploy script test path.

## Execution Evidence Snapshot (2026-09-04, deterministic stack)

- TS-001..TS-005, TS-015, TS-024 GREEN — `tests/test_source_analysis.py` (13 passed).
- TS-006..TS-008 GREEN — `tests/test_designer_stage.py` (5 passed).
- TS-009..TS-013 GREEN — `tests/test_review_stage.py` (9 passed).
- TS-014 GREEN — `tests/test_specialist_stages.py` formula tests + the updated family cap-exhaustion tests; TS-016/TS-017 GREEN — `tests/test_technical_evaluation.py` (21 passed incl. the extended report-contract fault loop).
- TS-018..TS-020 GREEN — `apps/web/__tests__/specialist-stage-surfaces.test.tsx` (web suite 122/122, tsc clean, eslint 0 errors).
- TS-021 GREEN — `apps/web/e2e/specialist-stage-journey.spec.ts` behind `E2E_SPECIALIST_STAGES=1` on the deterministic stack (35.8s, keyboard + 420px included). Live narration lines are not assertable under eager tasks (run settles before the SSE opens); the narration contract is covered by the exported-mapper component tests.
- TS-022 GREEN (live, owner-authorized 2026-09-04) — `live-evidence.json`: real-DeepSeek specialist journey (design/write/review per lesson, real analyses with telemetry, no severe findings so no revise — honest) + F009 six-pass live re-baseline (5 pass, 1 honest C-ART-1 fail on travelling-around pass1; C-STAGE-1 pass on all six; `retrieval=fastembed` + `tool=model_driven` + `stage_set` pinned); isolated `lessoncanvas_test` truncated after.
- TS-023 GREEN — full backend suite exit-0 with `infra/deploy.env` credential overrides against the isolated `lessoncanvas_test` database, ruff clean, web suite green; known flake exception recorded in review.md M-1 (reproduced on unmodified main).

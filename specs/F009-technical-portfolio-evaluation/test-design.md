# Test Design: F009 Technical Portfolio Evaluation

## Inputs and Environment

- Spec: `specs/F009-technical-portfolio-evaluation/spec.md` @ `15803bdc1837` (`SPEC READY` PASS)
- UX/UI: `specs/F009-technical-portfolio-evaluation/ux-ui.md` @ `ux-ui-f009-r1` / `d3860c7a8c05` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (VCS base `main @ 13dbee6`, branch `feature/F009-technical-portfolio-evaluation`)
- Environment: two separated stacks per TESTING.md —
  - Deterministic stack (all automated scenarios): docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter (extended with scripted fault profiles, eval-flag gated), eager or real-local worker as each scenario requires; no live-model dependency.
  - Controlled live stack (TS-017 only, delivery-time, owner-authorized): real DeepSeek provider + real Celery worker; bounded to 6 full passes + 1 real-worker recovery demonstration; recorded separately from deterministic suites.
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E + a11y checks)

## Risk Inventory

| Risk | F009 exposure | Coverage |
| --- | --- | --- |
| Dataset governance failure (private content, tampered/unlicensed file, silent manifest drift) | Dataset package accepted despite violation | TS-001 |
| False pass (criterion marked passed without evidence, or aggregate masking a failure) | Criteria engine honesty | TS-002, TS-003, TS-014 |
| Model-judge opinion becomes load-bearing | M-JUDGE leaking into blocking outcomes | TS-002 |
| Fault profiles leak into production behavior | Injection outside eval environments | TS-006 (gate assertions), TS-018 |
| Duplicate evaluation execution / double model cost | Idempotent-create violation | TS-004, TS-007 |
| Recovery evidence faked (retry billed as new run, completed scope lost) | Fault-scenario orchestration | TS-006, TS-008, TS-009 |
| Cost evidence silently zero where provider cannot report | Narration token capture | TS-003, TS-011 |
| Comparison merges incomparable passes | Cross-pass comparison logic | TS-012, TS-014 |
| Cross-workspace disclosure of evaluation data | New endpoints | TS-013 |
| Evidence-panel regression (F006 surfaces broken by the new region) | Shared panel integration | TS-014, TS-016, TS-018 |
| Live evidence window blocked (provider unavailable) | Live protocol honesty | TS-017 (provider-unavailable recording) |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 dataset governance (license/manifest/fail-closed) | TS-001 |
| AC-002 result binding to immutable inputs | TS-004, TS-005, TS-016 |
| AC-003 deterministic criterion outcomes | TS-002, TS-005 |
| AC-004 duplicate-submission idempotency evidence | TS-007 |
| AC-005 supersession-safety evidence | TS-008 |
| AC-006 injected-failure recovery evidence | TS-006, TS-017 (real-worker demonstration) |
| AC-007 partial-render explicitness | TS-009 |
| AC-008 memory pinning recorded | TS-005, TS-010 |
| AC-009 two live passes per unit, unmasked comparison | TS-017, TS-014 |
| AC-010 failure/missing-evidence never masked; diagnostics labeled | TS-002, TS-003, TS-014 |
| AC-011 model-opinion boundary | TS-002 |
| AC-012 narration token capture / honest missing-evidence | TS-003, TS-011, TS-017 |
| AC-013 evidence experience + report surfaces | TS-012, TS-014, TS-015, TS-016 |
| AC-014 comparison-unavailable on incomparable passes | TS-012, TS-014 |
| AC-015 non-disclosure + deletion cascade | TS-013 |

## Test Scenarios

### TS-001: Dataset governance — three licensed, manifest-verified units, fail-closed

- Protects: `AC-001`
- Risk/type: Governance / Integrity
- Given: the shipped dataset package (three units with license dedications, dataset revision, SHA-256 manifest); plus adversarial variants — a tampered file, an unlicensed file, a manifest with a wrong hash
- When: the dataset loader runs for each variant
- Then: the valid package loads all three units (`travelling-around` English, `natural-disasters` Chinese, `cultural-heritage` bilingual) with their scripted interview answers and expected-evidence direction; every adversarial variant fails closed with the governance rule named; no partial unit loads
- Level: Unit
- Automation target/path: `apps/backend/tests/test_evaluation_dataset.py`
- Result/evidence: NOT RUN

### TS-002: Criteria engine determinism, classification honesty, and model-judge boundary

- Protects: `AC-003`, `AC-010`, `AC-011`
- Risk/type: Rule / Honesty
- Given: recorded evaluation states (fixtures) covering: all blocking criteria met; one blocking criterion failed; one criterion unevaluable; diagnostic metrics present including an M-JUDGE opinion
- When: the criteria engine computes outcomes twice from identical state, then with an M-JUDGE "pass" opinion on a state whose blocking evidence is failed/missing
- Then: identical state yields identical outcomes; the failed criterion yields fail and the unevaluable yields missing_evidence (never pass); diagnostic metrics carry no pass/fail values; the overall outcome derives only from blocking criteria; M-JUDGE alone never flips any blocking outcome
- Level: Unit
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-003: Missing-evidence honesty — provider cannot report stream usage

- Protects: `AC-012` (missing-evidence part), `AC-010`
- Risk/type: Honesty
- Given: a pass whose narration stream produced no usage record (provider limitation fixture)
- When: criteria and metrics are computed
- Then: the affected cost component records missing_evidence with the precise reason; no zero is substituted; the pass outcome and report display show 证据缺失/未记录 rather than a pass
- Level: Unit + Integration
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-004: Evaluation pass creation is idempotent (single execution, no double cost)

- Protects: `AC-002` (binding), Spec D10 idempotency
- Risk/type: Idempotency / Concurrency
- Given: an owner and a dataset unit; evaluation-identity tuple (project, dataset revision, unit, pass index, mode, scenario)
- When: the same pass is created twice sequentially and twice concurrently
- Then: all creates converge on one record; the scripted pipeline executes exactly once (observed by model-call/trace counts); the duplicate responses identify the existing pass; audit reflects one creation
- Level: Integration/API/Concurrency
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-005: Deterministic full-pipeline pass — complete binding and blocking evidence

- Protects: `AC-002`, `AC-003`, `AC-008`
- Risk/type: Integration / Correctness
- Given: the deterministic stack (FakeModelAdapter, raised evaluation-environment quota), one dataset unit
- When: a full-pipeline evaluation pass runs to completion
- Then: the recorded result binds dataset revision, unit, source records, confirmed brief/blueprint versions, run ids, artifact ids, model configuration snapshot, memory state (`empty (F013 not implemented)`), and trace references; C-TRACE-1, C-GROUND-1, C-ART-1, C-MEM-1 outcomes are computed with evidence links; the evaluation project is isolated (no reads of other projects)
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-006: Fault: provider transient + worker failure — checkpoint recovery without duplicate billing

- Protects: `AC-006`
- Risk/type: Recovery / Fault injection
- Given: an evaluation scenario with the eval fault profile active (fake adapter + eval flag), scripting a mid-run provider failure and an in-task worker-death hook
- When: the scenario executes and recovery runs
- Then: the same run resumes from its checkpoint; completed scope is preserved; no duplicate model work is billed for completed scope (trace/token accounting compared); C-RECOV-1 records the recovery trace; the fault profile is ignored when either the adapter is not fake or the eval flag is unset (gate assertions)
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-007: Fault: concurrent duplicate submission returns the existing run

- Protects: `AC-004`
- Risk/type: Idempotency / Concurrency
- Given: an evaluation scenario issuing two concurrent identical generation starts against the same confirmed versions
- When: both submissions land
- Then: exactly one run is created and billed; the duplicate converges on the existing run; C-IDEM-1 records the duplicate-submission evidence with both request traces
- Level: Integration/API/Concurrency
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-008: Fault: stale-version supersession during an active run

- Protects: `AC-005`
- Risk/type: Concurrency / Safety
- Given: an evaluation scenario confirming a new brief/blueprint version while a generation run is active
- When: supersession executes at the safe checkpoint
- Then: the stale run never publishes over the newer version's artifacts; the older results remain historical and readable; C-SUPER-1 records the safe-checkpoint evidence
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-009: Fault: truncated model JSON — explicit partial-render failure

- Protects: `AC-007`
- Risk/type: Honesty / Fault injection
- Given: an eval fault profile returning a truncated JSON model response during artifact production
- When: the pipeline processes it
- Then: an explicit validation failure with bounded recovery is recorded; no fabricated artifact is marked complete; C-RENDER-1 records fail with the violating trace; a recovered retry (fresh complete response) completes honestly
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-010: Memory pinning configuration recorded on every pass

- Protects: `AC-008`
- Risk/type: Comparability / Audit
- Given: deterministic and (recorded evidence from) live passes
- When: pass configuration is snapshotted
- Then: every pass records the memory state; Phase-1 value is exactly `empty (F013 not implemented)`; C-MEM-1 fails only when recording is absent
- Level: Unit + Integration
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-011: Narration stream usage captured into trace events

- Protects: `AC-012`
- Risk/type: Contract / Telemetry
- Given: the adapter streaming a narration with usage data (fake fixture; live verification happens in TS-017)
- When: the stream completes
- Then: token usage and estimated cost are recorded on the owning trace events per the existing pattern; NULL stays NULL (未记录), never zero; the adapter requests stream usage (`stream_options.include_usage` or provider equivalent) on narration streams (request-shape assertion)
- Level: Unit + Integration
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py` (+ adapter unit assertions in `tests/test_model_parsing.py` extension if needed)
- Result/evidence: NOT RUN

### TS-012: Overview/report API contract — outcomes, comparison availability, supersession

- Protects: `AC-013` (data contract), `AC-014`
- Risk/type: Contract
- Given: an evaluation set with comparable passes (same unit+revision+config), incomparable passes (differing config and differing revision), and a superseded-configuration result after a dataset-revision bump
- When: overview and report endpoints are read
- Then: per-unit per-pass states and overall outcomes are correct; comparable passes present side-by-side data with no aggregate-only row; incomparable passes present comparison-unavailable with the precise reason; superseded results display the superseded-configuration state and stay readable; report data carries bound versions, config snapshot, memory state, and fault-scenario outcomes
- Level: API
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-013: Authorization non-disclosure and deletion cascade

- Protects: `AC-015`
- Risk/type: Security / Privacy
- Given: a second teacher account, an unauthenticated caller, and a workspace owning evaluation passes/results
- When: every F009 endpoint is requested cross-workspace/unauthenticated; then the project is deleted
- Then: all requests return the authorization-denied class without existence disclosure; deletion removes evaluation rows with no residue
- Level: API + Integration
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py`
- Result/evidence: NOT RUN

### TS-014: Evidence-panel region + pass detail component states

- Protects: `AC-009`, `AC-010`, `AC-013` (presentation), UX/UI State Matrix
- Risk/type: UI interaction
- Given: mocked payloads (empty not-run, queued/active, partial evidence, pass, fail, missing evidence, provider unavailable, superseded configuration, comparison unavailable, duplicate-create notice, cost 未记录)
- When: the 证据 panel with the 技术评估 region renders each
- Then: states use the designed chips/markers; blocking vs diagnostic groups render with 非阻断 labels; comparison shows columns only when comparable; the 启动评估 modal enforces selection, shows the live cost sentence, and returns the 该遍次已存在 notice on duplicates; errors map to the designed inline states; F006 evidence surfaces below remain intact
- Level: Component
- Automation target/path: `apps/web/__tests__/` Vitest + Testing Library (evidence-panel extension tests)
- Result/evidence: NOT RUN

### TS-015: Technical report route — print-styled honest report

- Protects: `AC-013` (report view)
- Risk/type: UI / Contract
- Given: mocked report data (pass set, fail set, missing-evidence set, comparison-unavailable)
- When: the print-styled report route renders
- Then: bound versions, dataset revision, config snapshot, memory state, per-unit per-pass criterion outcomes, fault-scenario outcomes, and cost/latency evidence render; failures stay explicit; product-validation status shows 未评估; app chrome hidden by the print stylesheet; semantic headings present
- Level: Component
- Automation target/path: `apps/web/__tests__/` Vitest report-route tests
- Result/evidence: NOT RUN

### TS-016: E2E journey — start deterministic pass, inspect outcomes, open report (keyboard + a11y)

- Protects: `AC-002`, `AC-003`, `AC-013` end to end
- Risk/type: E2E / Accessibility
- Given: the deterministic stack with a seeded project and a completable scripted unit
- When: the owner opens the 证据 panel, starts a deterministic evaluation pass via the modal, observes queued → active → completed, inspects criterion outcomes with evidence expansion, and opens the print-styled report
- Then: every step is keyboard-operable with correct focus management; states and outcomes match the payload; no failure is masked; scripted a11y checks pass
- Level: E2E + Accessibility
- Automation target/path: Playwright `e2e/` evaluation journey (deterministic stack; no live model)
- Result/evidence: NOT RUN

### TS-017: Live evidence protocol — six passes + real-worker recovery demonstration

- Protects: `AC-009`, `AC-006` (live recovery), `AC-012` (live stream usage)
- Risk/type: Controlled live-model evaluation
- Given: the controlled live stack (real DeepSeek, real Celery worker, owner-authorized, DeepSeek credentials present), the three dataset units
- When: two full live passes per unit execute (six total), and one real-worker stop/restart recovery demonstration runs mid-generation
- Then: each pass records per-criterion outcomes and raw per-pass metrics (latency, cost incl. narration streams where the provider reports usage); passes display side by side with no normalization; any failed or missing-evidence criterion stays explicit; the worker demonstration records same-run resume with preserved scope; provider unavailability during the window records the provider-unavailable state with partial evidence rather than fabricated outcomes
- Level: Live integration (separate from deterministic CI; owner-authorized execution at delivery; evidence appended to the Execution Evidence Snapshot)
- Automation target/path: harness-driven execution recorded manually in this document; bounded by definition (6 passes + 1 demonstration)
- Result/evidence: NOT RUN

### TS-018: Prior-surface and full-suite regression

- Protects: F001–F008 surfaces, evidence-panel integration
- Risk/type: Regression
- Given: the workspace with all prior tabs and the extended 证据 panel
- When: prior journeys (generation/deck/exercise/evidence/version-compare/alignment) and full backend/web suites run
- Then: prior surfaces behave unchanged; the evidence inventory/summary/events/narration surfaces remain intact; no prior test regressions
- Level: E2E + full suites
- Automation target/path: existing Playwright journeys + backend/web full suites
- Result/evidence: NOT RUN

## Parallel-feature integration/merge regression

`N/A - no concurrent work items` — F009 is the sole claimed `NEXT` item; single-member repository.

## Automation Feasibility

TS-001..TS-016 and TS-018 are fully automatable on the deterministic stack (fake adapter with eval-gated fault profiles; eager or local-real worker; MinIO real bytes). TS-017 is by definition a controlled live-model protocol: it runs once at delivery with owner authorization and DeepSeek credentials, is bounded (six passes + one demonstration), and is recorded in the Execution Evidence Snapshot rather than in deterministic CI — the TESTING.md separation rule. Residual risk accepted: two passes per unit give variance evidence, not statistical claims (Spec assumption).

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core AC verifiable with ≥1 TS | YES | Traceability table: AC-001..AC-015 all mapped |
| TR-02 | Happy Path, Alternative Flows, boundaries | YES | TS-005 happy path; TS-001/003/009/012/017 boundaries and alternatives |
| TR-03 | Error, Authentication/Security, Regression | YES | TS-013 security; TS-014/018 regression; error paths inside TS-001/003/012/014 |
| TR-04 | Idempotency/Concurrency/Transaction/Consistency | YES | TS-004/007/008 |
| TR-05 | Retry/Timeout/Migration/Compatibility/performance | YES | TS-006 recovery/retry; migration additive (Plan-verified); latency/cost measured as evidence, not asserted thresholds (Spec D2) |
| TR-06 | UI interaction/state, Accessibility, E2E | YES | TS-014/015/016 |
| TR-07 | Levels/automation targets target observable behavior | YES | API payload/status/trace-accounting assertions; component/E2E assert what users see |
| TR-08 | Environment/data/fixtures available | YES | Deterministic stack existing; live stack bounded and owner-authorized (TS-017 protocol defined) |
| TR-09 | Bug branch | N/A - new Feature, no Bug |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open | YES | All deterministic scenarios automatable; TS-017 verifiable under its controlled protocol |
| TR-11 | Concurrent NEXT integration slice | N/A - no concurrent work items |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `15803bdc1837`) + UI READY manifest (`ux-ui-f009-r1` @ `d3860c7a8c05`) + this artifact `test-design-f009-r1` @ `1623fedd4aa1`
- Evidence checklist result: ALL YES (TR-01..TR-11, with recorded N/A reasons where permitted)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01
- Approval scope: F009 Test Design at `test-design-f009-r1`

## Execution Evidence Snapshot

Recorded 2026-09-01, branch `feature/F009-technical-portfolio-evaluation`, deterministic stack (docker compose PostgreSQL/Redis/MinIO; FakeModelAdapter; eager tasks; local MinIO real bytes).

| Scenario | Result | Evidence |
| --- | --- | --- |
| TS-001 dataset governance (3 units, fail-closed variants) | PASS | `tests/test_evaluation_dataset.py` 8 tests (valid load; tampered/unlisted/missing-manifest/unlicensed-unit/key-mismatch/unlicensed-header fail closed; deletion cascade) |
| TS-002 criteria determinism, classification, judge boundary | PASS | `test_engine_deterministic_classification_and_judge_boundary` (M-JUDGE never flips blocking; missing_evidence never pass) |
| TS-003 missing-evidence honesty | PASS | `test_engine_missing_evidence_never_zeroes_cost` (null cost surfaced, never zero) |
| TS-004 idempotent creation incl. concurrent | PASS | `test_evaluation_create_is_idempotent_single_execution` (duplicate returns existing; ThreadPool concurrent create converges — IntegrityError race fixed with converge-on-conflict) |
| TS-005 deterministic full pipeline, complete binding | PASS | `test_full_pipeline_binds_versions_runs_artifacts_config_memory` (C-TRACE/GROUND/ART/MEM pass with evidence; ≥5 bound runs; memory snapshot recorded) |
| TS-006 fault: provider/worker recovery, gated profiles | PASS | `test_fault_recovery_resumes_same_run_no_duplicate_billing` + `test_fault_profiles_gated_to_fake_evaluation_environments` (resume same run, preserved scope, model_calls == expected; profiles refused without fake adapter or eval flag) |
| TS-007 fault: duplicate submission | PASS | `test_fault_duplicate_submission_converges_on_one_run` (both submissions return the same run; one run per version pair) |
| TS-008 fault: stale-version supersession | PASS | `test_fault_stale_version_superseded_never_publishes` (stale run superseded, newer pair completes, no stale publish) |
| TS-009 fault: partial render | PASS | `test_fault_partial_render_records_explicit_failure` (explicit lesson-failed event; recovered run completes; no fabricated success) |
| TS-010 memory pinning on every pass | PASS | engine test + snapshot assertions in TS-005 |
| TS-011 narration usage capture | PASS | `test_narration_stream_usage_captured_into_trace_events` (tokens + estimated cost on narration trace events) + `test_deepseek_stream_requests_provider_usage` (request carries `stream_options.include_usage`) |
| TS-012 overview/report contract | PASS | `test_report_contract_comparison_and_supersession` (set-level missing_evidence → pass progression; comparison available on second pass; superseded-configuration marking) + `test_overview_marks_superseded_dataset_revision` + requirement rejections |
| TS-013 non-disclosure + deletion | PASS | `test_cross_workspace_no_disclosure` (cross-workspace 403/404, unauthenticated 401) + cascade test in `test_evaluation_dataset.py` |
| TS-014 region component states | PASS | Vitest `__tests__/technical-evaluation.test.tsx` (empty, states incl. provider-unavailable/superseded, criteria groups with 非阻断, modal cost sentence + duplicate notice, governance error mapping) |
| TS-015 report route | PASS | Vitest report-view tests (honest statuses, comparison unavailable, print hint, error state) |
| TS-016 E2E browser journey | ENVIRONMENT-BLOCKED | Spec delivered at `e2e/evaluation-journeys.spec.ts` (gated `E2E_EVAL_FAULT=1`); Clerk E2E credentials absent and backend not running in this session. Substitute coverage green: backend TS-004/005/012 + component TS-014/015. Resume: run under `E2E_EVAL_FAULT=1` with the fault stack and credentials present, append evidence |
| TS-017 live evidence protocol | PASS | Owner-authorized execution 2026-09-01 (DeepSeek live provider; evidence files `live-evidence.json`, `live-evidence-summary.txt`, `worker-recovery-evidence.json` in this directory). Six live passes: cultural-heritage p1/p2 pass, natural-disasters p1/p2 pass, travelling-around p1 pass, travelling-around p2 **fail** (C-ART-1: slide-deck lesson 3 not downloadable) — the honest per-pass failure stays explicit per Spec D3/AC-009/AC-010. Per-pass estimated cost $0.0097-$0.0141 incl. narration usage capture. Real-worker stop/restart recovery: SIGKILL at lesson 1 (status generating, 2 calls) → worker restart → same idempotent run re-dispatched → complete, lesson-1 checksum byte-identical, model_calls 2→4 (remaining lessons only; no duplicate billing). travelling-around p1's first attempt failed at harness level (live planning-draft commit timing); the harness gained bounded draft waits (deterministic suites re-verified green) and the pass re-executed to completion |
| TS-018 regression | PASS (suites) | Full backend suite 221 passed + ruff clean (2026-09-01); web 63/63 Vitest, eslint 0 errors (7 pre-existing e2e warnings), `tsc --noEmit` clean, `next build` clean. Browser journeys environment-blocked with TS-016 |

Full-suite verification (2026-09-01): backend `uv run pytest` exit-0 (221 passed, incl. 24 F009 tests) + `ruff check` clean; web Vitest 63/63, eslint 0 errors, tsc clean, production build clean.

### Recorded deviations and residuals (owner-visible)

- M-1 (environment class, pre-existing): `client.stream(...)` SSE consumption deadlocks in this environment before the first chunk for idle keepalive streams — reproduced identically on the F008 baseline (`git stash` verified), while the same tests pass with data-bearing streams and a minimal TestClient probe passes. The F006 keepalive test now consumes the endpoint generator in-process with unchanged assertions (deterministic substitute); other TestClient streaming tests remain unchanged and green. Root cause sits outside this Feature (TestClient/httpx interplay); revisit if it recurs.
- M-2 (contract note): `_SlowStreamAdapter`/`BlockingFake` test stubs upgraded to the F009 D9 `stream_with_usage` contract (usage surfaced via holder; legacy `stream` kept delegating).
- M-3 (defect fixed in delivery, F003-owned surface): truncated/unparseable model JSON was misclassified as a provider failure (bounded Celery retries → "provider retries exhausted") with no explicit per-lesson validation-failure event. Fixed per Spec D6/AC-007: per-lesson `LessonValidationError` with bounded in-node retry, explicit failed-event, parse-failure trace. Deck/exercise graphs keep the legacy classification (no F009 scenario exercises them); candidate follow-up work item.
- L-1: concurrent-duplicate evaluation create initially surfaced IntegrityError (race) — fixed with converge-on-conflict (same pattern as generation-run identity); regression covered by the concurrent create test.
- L-2: E2E browser journeys require Clerk E2E credentials (`E2E_TEACHER_EMAIL/PASSWORD`) and a running fault stack; not available in this session (same class as F008 M-1).
- L-3 (live-execution environment note): the six live passes and the recovery demonstration ran through the real DeepSeek provider; passes executed with in-process eager task execution because the real-worker path hit two pre-existing environment defects outside F009 scope — concurrent `PostgresSaver.setup()` racing on `checkpoint_migration` creation, and Celery prefork/memory-checkpointer state inconsistency for live interviews (the class STAGE B-001 deferred to F012). The recovery demonstration itself used the real worker (real dispatch, SIGKILL, restart, re-dispatch). Resume condition for full real-worker passes: resolve the checkpointer races (F012 territory) or pin `CHECKPOINT_BACKEND=postgres` with serialized setup.
- L-4 (harness hardening during live execution): bounded waits added for discovery/planning draft persistence and a blueprint-sync retry (live-model commit timing); `ensure_bucket` made race-tolerant for parallel first uploads; evaluation failure reasons now carry compact stack frames. Deterministic suites re-verified green after each change (24/24).

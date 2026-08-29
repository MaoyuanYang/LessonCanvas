# Test Design: F003 Recoverable Unit Lesson Plans

## Inputs and Environment

- Spec: `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `193e90d10b68` (`SPEC READY` PASS)
- UX/UI: `specs/F003-recoverable-unit-lesson-plans/ux-ui.md` @ `ux-ui-f003-r1` / approved content `43f93abc6ed3` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (contain full manifests; VCS base `4ccc4ef`)
- Environment: existing deterministic harness — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter for logic, Clerk token fixtures; live DeepSeek only for separately authorized live evidence
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E), manual keyboard/a11y pass

## Risk Inventory

| Risk (from TESTING.md map + Spec) | F003 exposure | Coverage |
| --- | --- | --- |
| Duplicate submission or retry | Duplicate model cost / artifacts | TS-001, TS-015 |
| Worker or provider failure loses work | Long generation restarts from zero | TS-003, TS-004, TS-016 |
| Upstream revision during generation | Stale output overwrites newer version | TS-006 |
| Broken Office exports | Claimed deliverable unopenable | TS-002, TS-012 |
| Long-task UI ambiguity | Teacher retries or loses recovery path | TS-020, TS-021, TS-022 |
| Cross-account access | Private artifacts/traces leak | TS-011, TS-018 |
| Prompt or document injection via generated content | Content changes policy / grants tools | TS-019 |
| Streaming interruption or reconnect | Duplicate work or lost progress | TS-007, TS-008 |
| Cost runaway | Cap not enforced | TS-005 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 complete valid artifact set | TS-002, TS-012 |
| AC-002 idempotent start | TS-001, TS-015 |
| AC-003 fast acknowledgement | TS-001, TS-025 |
| AC-004 progress visibility | TS-007, TS-020, TS-023 |
| AC-005 transient failure resume, completed work intact | TS-003, TS-016, TS-026 |
| AC-006 Worker crash checkpoint resume | TS-003, TS-004, TS-026 |
| AC-007 model-call cap | TS-005, TS-028 |
| AC-008 supersession | TS-006, TS-027 |
| AC-009 SSE replay | TS-007, TS-029 |
| AC-010 narration stop | TS-008, TS-022, TS-029 |
| AC-011 partial visibility + resume | TS-009, TS-021, TS-026 |
| AC-012 authorized download | TS-011 |
| AC-013 complete trace | TS-013 |
| AC-014 structural validation | TS-002, TS-012 |
| AC-015 deletion cascade | TS-014 |
| AC-016 language mode | TS-002, TS-013 |

## Test Scenarios

### TS-001: Generation start binds confirmed versions, idempotent, gated

- Protects: `AC-002`, `AC-003`
- Risk/type: Happy / Idempotency / Boundary
- Given: a project with confirmed brief vN + blueprint vM; a project without confirmed versions
- When: generation start is requested (including double submit and concurrent duplicates)
- Then: with versions, a run bound to (vN, vM) is created/returned identically on duplicates and acknowledged with a queued snapshot; without versions, a requirement error names the prerequisite and no run or model call is created
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: seeded confirmed versions via brief/blueprint services; FakeModelAdapter
- Result/evidence: NOT RUN

### TS-002: Full run completes every lesson with structurally valid DOCX in the bound language mode

- Protects: `AC-001`, `AC-014`, `AC-016`
- Risk/type: Happy / Contract
- Given: confirmed blueprint with K lessons and language mode (zh / en / bilingual variants)
- When: the workflow runs to completion with the real python-docx renderer
- Then: every lesson has an artifact that is openable by the parser, contains the required top-level sections (D1), has non-empty body, follows the language mode, and the run reaches `complete`
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: FakeModelAdapter scripted plans; real renderer + MinIO
- Result/evidence: NOT RUN

### TS-003: Per-lesson checkpoint — resume skips completed lessons

- Protects: `AC-005`, `AC-006`
- Risk/type: Recovery / Idempotency
- Given: a run where lessons 1..j completed and lesson j+1 fails (injected provider error)
- When: the run resumes (retry or teacher resume)
- Then: lessons 1..j keep their original artifacts (unchanged object keys/checksums), only lessons j+1.. run, and total model calls increase by exactly the incomplete lessons' work
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: FakeModelAdapter with per-lesson failure script; call counter assertion
- Result/evidence: NOT RUN

### TS-004: Worker crash mid-run resumes from checkpoint on re-dispatch

- Protects: `AC-006`
- Risk/type: Recovery / Concurrency
- Given: a run interrupted without completing its current lesson (simulated crash: task ends abnormally mid-lesson)
- When: the same run id is re-dispatched (Celery redelivery / resume endpoint)
- Then: the run continues from the last per-lesson checkpoint, no completed lesson re-runs, and no duplicate artifact versions are published
- Level: Integration (service-level crash simulation + Celery eager redelivery)
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: eager Celery; injected abrupt termination
- Result/evidence: NOT RUN

### TS-005: Per-run model-call cap is authoritative

- Protects: `AC-007`
- Risk/type: Boundary / Cost
- Given: a run with cap C smaller than the work required for K lessons
- When: generation runs
- Then: exactly at the cap no further model call begins, the run enters `capped_failure`, completed lessons remain valid and downloadable, and the API exposes cap usage and a recovery path
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: small cap setting; FakeModelAdapter call counter
- Result/evidence: NOT RUN

### TS-006: Supersession stops the old run at a safe checkpoint without stale publication

- Protects: `AC-008`
- Risk/type: Consistency / Version conflict
- Given: an active generation run bound to (vN, vM); a newer brief/blueprint version is confirmed mid-run
- When: the run reaches its next safe checkpoint
- Then: the run is marked `superseded`, stops, its artifacts remain historical under the old version binding, and no artifact is published over the newer version; starting generation on the new version yields a new run
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: confirm-version hooks from F002; mid-run confirmation injection
- Result/evidence: NOT RUN

### TS-007: SSE authoritative event log and Last-Event-ID replay

- Protects: `AC-004`, `AC-009`
- Risk/type: Contract / Streaming
- Given: an active run emitting ordered events with per-run monotonic ids
- When: a client disconnects and reconnects with `Last-Event-ID`, and another client polls the snapshot concurrently
- Then: replay returns exactly the missed events in order, no event is duplicated or lost across reconnects, replay triggers no model work (call counter unchanged), and the snapshot always reflects authoritative state
- Level: API/Contract
- Automation target/path: `apps/backend/tests/test_generation.py` (SSE via httpx stream)
- Data/fixture/environment: deterministic event fixtures
- Result/evidence: NOT RUN

### TS-008: Stopping narration never affects the run

- Protects: `AC-010`
- Risk/type: Streaming / Semantics
- Given: active generation with narration streaming
- When: narration stop is invoked
- Then: the narration stream ends, run state/per-lesson progress and artifact production continue to completion, and trace integrity is preserved
- Level: API
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: FakeModelAdapter narration
- Result/evidence: NOT RUN

### TS-009: Partial failure visibility and scoped resume

- Protects: `AC-005`, `AC-011`
- Risk/type: Partial Failure / Recovery
- Given: a run where some lessons failed terminally after retries and others completed
- When: the teacher inspects the run and triggers resume
- Then: per-lesson outcomes and reasons are visible in the snapshot, resume re-dispatches the same run for failed/incomplete lessons only, and completed artifacts are untouched
- Level: API + Component
- Automation target/path: `apps/backend/tests/test_generation.py`; `apps/web/__tests__/generation-panel.test.tsx`
- Data/fixture/environment: mixed-outcome fixture
- Result/evidence: NOT RUN

### TS-010: Resume rejects ineligible terminal states

- Protects: Run state machine invariant (Spec State Transitions)
- Risk/type: Rule / Boundary
- Given: runs in `terminal_failure`, `superseded`, `complete`
- When: resume is requested
- Then: each is rejected with an explicit state-conflict error naming the current state; no state regresses
- Level: API
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: state fixtures
- Result/evidence: NOT RUN

### TS-011: Authorized download with non-disclosing denial

- Protects: `AC-012`
- Risk/type: Authorization / Privacy
- Given: a completed artifact; its owner; a different workspace's teacher; an artifact record whose binary is missing
- When: download is requested by each
- Then: owner receives the exact stored binary (checksum match); cross-workspace receives the authorization-denied class response without confirming existence; missing-binary artifacts are never in ready/downloadable state
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: two workspaces; MinIO object manipulation
- Result/evidence: NOT RUN

### TS-012: Invalid render never becomes ready

- Protects: `AC-014`, artifact invariant
- Risk/type: Broken Office export / Error
- Given: a lesson whose rendered file is corrupt/empty or missing required sections (injected renderer fault)
- When: validation runs
- Then: the lesson enters failed with a structural reason, the artifact never reaches ready, other lessons are unaffected, and the file is not downloadable
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: corrupted-bytes and section-missing fixtures
- Result/evidence: NOT RUN

### TS-013: Complete per-stage trace with cost and latency

- Protects: `AC-013`, `AC-016`
- Risk/type: Observability / Evidence
- Given: a run with mixed outcomes (success, failure, retry, cap or supersession)
- When: traces are reviewed in the owning workspace
- Then: every model call, tool call (render/validate), specialist transition, failure, and retry appears with prompt/output references, cost, and latency; nothing appears outside the owning workspace
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: mixed-outcome fixture
- Result/evidence: NOT RUN

### TS-014: Project deletion cascades to run data and binaries

- Protects: `AC-015`
- Risk/type: Privacy / Deletion
- Given: a project with runs, artifacts, events, traces, and stored DOCX binaries
- When: the project is deleted
- Then: all rows and object-storage binaries are removed; no orphaned events or files remain
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: deletion service; MinIO listing assertion
- Result/evidence: NOT RUN

### TS-015: Concurrent duplicate starts converge on one run

- Protects: `AC-002`
- Risk/type: Concurrency / Transaction
- Given: the same project with confirmed versions
- When: multiple start requests race (threads/processes)
- Then: exactly one run row exists for the bound versions (DB unique constraint), all callers receive the same run, and no duplicate model work begins
- Level: Concurrency/Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: parallel transactions against PostgreSQL
- Result/evidence: NOT RUN

### TS-016: Provider hard failure after bounded retries is terminal with work preserved

- Protects: `AC-005`, D5 taxonomy
- Risk/type: Error / Recovery boundary
- Given: a provider that fails persistently for lesson j after the retry budget
- When: retries exhaust
- Then: the run ends in `terminal_failure` (or `partial_failure` when other lessons completed), completed lessons remain valid and downloadable, and resume is not offered for the terminal cause
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: persistent-failure FakeModelAdapter; retry budget fixture
- Result/evidence: NOT RUN

### TS-017: Object-storage write failure fails the lesson without faking success

- Protects: Spec Error Cases (storage boundary)
- Risk/type: Error / Consistency
- Given: MinIO write fails for one lesson (injected fault)
- When: the lesson's render step runs
- Then: the lesson enters failed with the storage reason, no ready artifact is recorded, and other lessons continue
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: storage fault injection
- Result/evidence: NOT RUN

### TS-018: Cross-account non-disclosure on all F003 surfaces

- Protects: Authorization boundary
- Risk/type: Security / Privacy
- Given: teacher B attempts every F003 endpoint (start/snapshot/events/resume/download) on teacher A's project
- When: requests are made
- Then: every response is the authorization-denied class without existence disclosure
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: dual-workspace fixtures
- Result/evidence: NOT RUN

### TS-019: Generated content is untrusted output

- Protects: Business rule (untrusted generated content)
- Risk/type: Injection
- Given: model output containing injection payloads (fake tool grants, policy text, prompt instructions)
- When: the workflow consumes and renders it
- Then: no tool beyond the registered render/validate tools is invoked, no policy or authorization changes, and the payload renders as inert document text
- Level: Integration
- Automation target/path: `apps/backend/tests/test_generation.py`
- Data/fixture/environment: injection-payload FakeModelAdapter scripts
- Result/evidence: NOT RUN

### TS-020: Generation panel states render correctly

- Protects: `AC-003`, `AC-004` (UI)
- Risk/type: UI state
- Given: snapshot fixtures for queued/generating/validating/complete/partial/capped/superseded/terminal/blocked
- When: the generation panel renders each
- Then: phase tracker, per-lesson states, outcome banners, cap usage, and bound versions display per D-PROG/D-ART; unavailable state names the blueprint gate
- Level: Component (Vitest + Testing Library)
- Automation target/path: `apps/web/__tests__/generation-panel.test.tsx`
- Data/fixture/environment: mocked API client
- Result/evidence: NOT RUN

### TS-021: Partial failure interaction — reasons, resume, download

- Protects: `AC-011`, `AC-012` (UI)
- Risk/type: Interaction / Recovery
- Given: a partial-failure snapshot with per-lesson reasons
- When: the teacher reviews and triggers scoped resume (modal) and downloads a completed lesson
- Then: the modal names affected lessons, resume calls the endpoint once with loading/disabled states, download retrieves the authorized file, and terminal states show no resume
- Level: Component/Interaction
- Automation target/path: `apps/web/__tests__/generation-panel.test.tsx`
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-022: Reconnect banner and narration stop in the UI

- Protects: `AC-009`, `AC-010` (UI)
- Risk/type: Interaction / Streaming
- Given: an SSE drop mid-progress and an active narration stream
- When: disconnect/stop occur
- Then: the reconnect banner states remote work continues and restores progress on replay; stopping narration stops display only while progress markers continue
- Level: Component
- Automation target/path: `apps/web/__tests__/generation-panel.test.tsx`
- Data/fixture/environment: mocked event source
- Result/evidence: NOT RUN

### TS-023: E2E happy path — confirmed blueprint to downloadable plans (live stack)

- Protects: `AC-001`..`AC-004` end to end
- Risk/type: E2E / Critical path
- Given: the authenticated teacher account with a confirmed blueprint (existing journey)
- When: the teacher starts generation, waits for completion, and downloads a lesson plan
- Then: the full UI path works against the running system (API + Celery Worker + PostgreSQL + MinIO + live model per TQ-002); downloads produce a real DOCX
- Level: E2E (Playwright, `CLERK_E2E=1` gated)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts` (extended)
- Data/fixture/environment: compose services; real Worker process participating; live DeepSeek
- Result/evidence: NOT RUN

### TS-024: Keyboard and screen-reader pass on the generation flow

- Protects: Accessibility requirement (`docs/UX.md`, WCAG 2.2 AA)
- Risk/type: Accessibility
- Given: the implemented generation view
- When: a manual keyboard/focus pass runs start → leave/return → partial failure → resume → download, plus automated a11y checks
- Then: all actions keyboard reachable, focus managed per ux-ui.md, live-region announcements throttled and correct, no color-only cues
- Level: Accessibility (automated checks + manual pass)
- Automation target/path: Playwright a11y checks + recorded manual pass evidence
- Data/fixture/environment: implemented UI
- Result/evidence: NOT RUN

### TS-025: E2E blocked start — no confirmed blueprint routes to the gate

- Protects: `AC-003` (teacher-blocked path) end to end
- Risk/type: E2E / Boundary
- Given: an authenticated project without a confirmed blueprint
- When: the teacher opens `教案生成`
- Then: the unavailable state names the blueprint gate and links to it; no run exists and no start action is offered
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts` (fresh-project fixture)
- Data/fixture/environment: compose services; no model calls expected
- Result/evidence: NOT RUN

### TS-026: E2E partial failure and scoped resume (fault-injected stack)

- Protects: `AC-005`, `AC-006`, `AC-011` end to end
- Risk/type: E2E / Recovery
- Given: the running stack with the deterministic fault instance per TQ-002 (fake adapter scripted to fail lesson j after lessons 1..j-1 complete; real Worker)
- When: the teacher watches the run fail partially, then triggers scoped resume
- Then: failed lessons show reasons, resume re-dispatches the same run, completed lessons stay downloadable without re-running, and the run reaches complete after the scripted fault clears
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts` (fault instance profile)
- Data/fixture/environment: compose services; fake-adapter backend instance + real Worker; scripted per-lesson failure
- Result/evidence: NOT RUN

### TS-027: E2E supersession — new version stops the active run

- Protects: `AC-008` end to end
- Risk/type: E2E / Version conflict
- Given: an active generation run (live stack) and a confirmed newer brief/blueprint version mid-run
- When: the run reaches its safe checkpoint
- Then: the UI shows the superseded banner naming the newer version, old artifacts remain historical, and starting generation on the new version produces a new run that completes
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts`
- Data/fixture/environment: compose services; live model; mid-run confirmation via existing brief revision journey
- Result/evidence: NOT RUN

### TS-028: E2E cap exhaustion — capped state with preserved work

- Protects: `AC-007` end to end
- Risk/type: E2E / Cost boundary
- Given: the deterministic fault instance configured with a per-run model-call cap smaller than the unit requires (cap is a setting)
- When: generation runs past the cap
- Then: the capped banner shows usage and recovery guidance, completed lessons remain downloadable, and no further model work occurs
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts` (small-cap instance profile)
- Data/fixture/environment: fake-adapter backend instance with small cap env; real Worker
- Result/evidence: NOT RUN

### TS-029: E2E SSE reconnect and narration stop on a live run

- Protects: `AC-009`, `AC-010` end to end
- Risk/type: E2E / Streaming
- Given: an active run with progress streaming (live stack)
- When: the page reloads mid-run (worst-case disconnect) and narration is stopped
- Then: the view reconnects via `Last-Event-ID`, missed events restore progress without duplication, stopping narration stops display only, and the run completes unaffected
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts`
- Data/fixture/environment: compose services; live model
- Result/evidence: NOT RUN

## Scenario Selection Notes

- Load/performance runs: `N/A for F003` — bounded performance evidence belongs to F009 evaluation; per-stage latency is captured in traces (TS-013).
- Visual regression suite: `N/A for F003` — the new panel's states are covered by component-level state assertions (TS-020..022); shared-component visual baselines are unchanged (reuse-only decisions).
- Migration backward compatibility: additive tables only; verified by the migration task's integration proof in the Plan (no legacy data rewrite).
- Regression protection: existing 80 backend + 16 web suites must stay green; the F002 supersession hooks (TS-006) extend the existing brief-reconfirmation path.

## Open Test Questions

| ID | Question | Severity | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Exact per-run model-call cap default | Non-critical | Implementation assignee | Chosen in the Implementation Plan with per-lesson call accounting; Spec behavior (cap authoritative, capped state) is testable at any value (TS-005) | RESOLVED |
| TQ-002 | E2E model provider and fault-injection strategy | Non-critical | `YMY / Project Owner` | Dual-instance E2E: the default live stack (DeepSeek + real Worker) covers happy path, blocked start, supersession, and SSE reconnect (TS-023/025/027/029); a deterministic fault instance (`LESSONCANVAS_MODEL_ADAPTER=fake` + small cap env, same services) drives partial-failure/resume and cap paths (TS-026/028), making failure E2E reproducible at zero model cost. Component/integration suites stay fake-based | RESOLVED |
| TQ-003 | Worker-crash simulation mechanism | Non-critical | Implementation assignee | Service-level abrupt-termination plus Celery eager-mode redelivery in integration tests (TS-004); a real process-kill test is not required for Phase-1 evidence | RESOLVED |

No Critical Test Question is `OPEN` or `DEFERRED`.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable and mapped. | YES | Traceability table covers AC-001..AC-016 |
| TR-02 | Happy Path, Alternative Flows, boundaries covered. | YES | TS-001/002 happy; TS-003/004/009 alternatives; TS-005/010/015/016 boundaries |
| TR-03 | Error, Auth/Security, Regression covered. | YES | TS-011/018/019 security; TS-012/016/017 errors; regression via existing suites + supersession hook coverage |
| TR-04 | Idempotency, Concurrency, Transaction, Consistency covered. | YES | TS-001/003/004/006/015 |
| TR-05 | Retry/timeout, migration/compat, performance covered or N/A. | YES | TS-016/017; migration additive (Notes); performance N/A with reason |
| TR-06 | UI interaction/state, Accessibility, E2E covered per risk. | YES | TS-020/021/022 components; full user-journey E2E TS-023/025/026/027/028/029 (live stack + deterministic fault instance); a11y TS-024 |
| TR-07 | Levels and automation targets appropriate, not implementation-only. | YES | All scenarios assert observable API/UI/DB/storage outcomes |
| TR-08 | Environment, data, fixtures, dependencies available. | YES | Existing harness reused; renderer is real python-docx; storage MinIO; fakes scripted |
| TR-09 | Bug reproduction/regression or confirmed surrogate. | YES | `N/A - new Feature, no Bug`; the observed initializing-strand gap is covered by TS-003/TS-004 recovery paths |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open/deferred. | YES | All TQs resolved, none Critical |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `193e90d10b68`, UX/UI `ux-ui-f003-r1` / approved content `43f93abc6ed3`, plus their Gate Record manifests (VCS base `4ccc4ef`), `docs/TESTING.md`, and this artifact `test-design-f003-r2` @ `880a6a4a418c` (revision r2: full code-path E2E coverage added per owner review; r1 superseded)
- Evidence checklist result: ALL YES (TR-01..TR-10)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `193e90d10b68`
- Validated UI revision or complete skip-decision link: `ux-ui-f003-r1` / `43f93abc6ed3`
- Validated Test Design revision: `test-design-f003-r2` @ `880a6a4a418c`
- Validated at: 2026-08-29
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-29 (r1 revision requested: full code-path E2E coverage; r2 approved)
- Approval scope: F003 Test Design at `test-design-f003-r2`

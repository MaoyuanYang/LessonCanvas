# Test Design: F005 Lesson Exercises and Answers

## Inputs and Environment

- Spec: `specs/F005-lesson-exercises-and-answers/spec.md` @ `41b391751a33` (`SPEC READY` PASS)
- UX/UI: `specs/F005-lesson-exercises-and-answers/ux-ui.md` @ `ux-ui-f005-r1` / approved content `78923f6468b7` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (contain full manifests; VCS base `main @ 123523a`)
- Environment: existing deterministic harness — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter for logic, Clerk token fixtures; live DeepSeek only for separately authorized live evidence; real `python-docx` renderer in every automated suite
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E), manual keyboard/a11y pass, one controlled manual Word open smoke (Spec D7)

## Risk Inventory

| Risk (from TESTING.md map + Spec) | F005 exposure | Coverage |
| --- | --- | --- |
| Duplicate submission or retry | Duplicate model cost / pair artifacts | TS-001, TS-015 |
| Worker or provider failure loses work | Exercise generation restarts from zero | TS-003, TS-004, TS-016 |
| Upstream revision during generation | Stale pairs overwrite newer version | TS-006 |
| Broken Office exports | Unopenable DOCX pair | TS-002, TS-012, TS-031 |
| Exercise/answer pairing mismatch | Missing, orphan, or empty answers hidden by ready state | TS-002, TS-012, TS-031 |
| Prerequisite bypass | Exercises drift from confirmed lesson plans | TS-001, TS-013, TS-025 |
| Difficulty binding bypass | Tier overwritten, duplicated, or ignored | TS-001, TS-007, TS-013, TS-020 |
| Long-task UI ambiguity | Teacher retries or loses recovery path | TS-020, TS-021, TS-022 |
| Cross-account access | Private exercise artifacts/traces leak | TS-011, TS-018 |
| Prompt or document injection via generated content | Content changes policy / grants tools | TS-019 |
| Streaming interruption or reconnect | Duplicate work or lost progress | TS-007, TS-022 |
| Cost runaway | Exercise-run cap not enforced | TS-005 |
| Workspace-shell extension regression | Adding the seventh view breaks existing panels | TS-023 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 complete valid pair set | TS-002, TS-030 |
| AC-002 idempotent start | TS-001, TS-015 |
| AC-003 fast acknowledgement | TS-001, TS-020 |
| AC-004 progress + pair summary + tier visibility | TS-007, TS-020, TS-030 |
| AC-005 transient failure resume, completed work intact | TS-003, TS-009, TS-026 |
| AC-006 Worker crash checkpoint resume | TS-003, TS-004, TS-026 |
| AC-007 exercise-run model-call cap | TS-005, TS-028 |
| AC-008 supersession | TS-006, TS-027 |
| AC-009 SSE replay | TS-007, TS-022, TS-029 |
| AC-010 narration stop | TS-008, TS-022, TS-029 |
| AC-011 partial visibility + resume | TS-009, TS-021, TS-026 |
| AC-012 authorized dual download | TS-011, TS-021 |
| AC-013 complete trace | TS-013 |
| AC-014 deterministic pairing validation | TS-002, TS-012, TS-031 |
| AC-015 deletion cascade | TS-014 |
| AC-016 language mode | TS-002, TS-013 |
| AC-017 lesson-plan prerequisite gate | TS-001, TS-020, TS-025 |
| AC-018 lesson-plan context recorded in trace | TS-013 |
| AC-019 difficulty recording and immutability | TS-001, TS-007, TS-013, TS-020 |
| AC-020 bounded category selection and numbering | TS-002, TS-012 |

## Test Scenarios

### TS-001: Exercise start binds confirmed versions, the complete lesson-plan run, and the difficulty tier — idempotent, gated, tier-validated

- Protects: `AC-002`, `AC-003`, `AC-017`, `AC-019`
- Risk/type: Happy / Idempotency / Boundary / Input validation
- Given: a project with confirmed brief vN + blueprint vM and a complete lesson-plan run for (vN, vM); a project without confirmed versions; a project with confirmed versions but no or an incomplete lesson-plan run; start bodies with a missing or invalid tier, and a duplicate start requesting a different tier
- When: exercise start is requested (including double submit)
- Then: with the prerequisite met and a valid tier, an exercise run bound to (vN, vM) and the lesson-plan run is created/returned identically on duplicates with the recorded tier surfaced; a duplicate requesting a different tier still returns the existing run with its recorded tier and never overwrites it or creates a second run; without confirmed versions or without a complete lesson-plan run, a requirement error names the exact failed prerequisite and no exercise run or model call is created; a missing or invalid tier returns an input-validation error listing the three tiers and creates nothing
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: seeded confirmed versions + completed lesson-plan run via existing services; FakeModelAdapter
- Result/evidence: NOT RUN

### TS-002: Full exercise run completes every lesson with a structurally valid, correctly paired DOCX pair in the bound language mode

- Protects: `AC-001`, `AC-014`, `AC-016`, `AC-020`
- Risk/type: Happy / Contract
- Given: a completed lesson-plan run for a confirmed blueprint with K lessons and language mode (zh / en / bilingual variants)
- When: the exercise workflow runs to completion with the real python-docx renderer
- Then: every lesson has an exercise DOCX and answer DOCX that are openable by the parser, contain the required D1 sections (lesson title, instructions naming tier and objectives, category headings; answer title and answer entries), use 3–4 categories from the six-category catalog, number items continuously from 1 within configured item-count bounds, satisfy E == A numbering equality with non-empty answers, follow the language mode, and the run reaches `complete` with pair summaries (item/category counts) recorded
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: FakeModelAdapter scripted pairs derived from scripted lesson plans; real renderer + MinIO
- Result/evidence: NOT RUN

### TS-003: Per-pair checkpoint — resume skips completed lessons

- Protects: `AC-005`, `AC-006`
- Risk/type: Recovery / Idempotency
- Given: an exercise run where lessons 1..j completed and lesson j+1 fails (injected provider error)
- When: the run resumes (retry or teacher resume)
- Then: lessons 1..j keep their original pairs (unchanged object keys/checksums for both files), only lessons j+1.. run, and total model calls increase by exactly the incomplete lessons' work
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: FakeModelAdapter with per-lesson failure script; call counter assertion
- Result/evidence: NOT RUN

### TS-004: Worker crash mid-exercise-run resumes from checkpoint on re-dispatch

- Protects: `AC-006`
- Risk/type: Recovery / Concurrency
- Given: an exercise run interrupted without completing its current lesson (simulated crash)
- When: the same run id is re-dispatched (Celery redelivery / resume endpoint)
- Then: the run continues from the last per-lesson checkpoint, no completed pair re-runs, and no duplicate artifact versions are published
- Level: Integration (service-level crash simulation + Celery eager redelivery)
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: eager Celery; injected abrupt termination
- Result/evidence: NOT RUN

### TS-005: Exercise-run model-call cap is authoritative

- Protects: `AC-007`
- Risk/type: Boundary / Cost
- Given: an exercise run with cap C smaller than the work required for K lessons
- When: exercise generation runs
- Then: exactly at the cap no further model call begins, the run enters `capped_failure`, completed pairs remain valid and downloadable, and the API exposes cap usage and a recovery path
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: small cap setting; FakeModelAdapter call counter
- Result/evidence: NOT RUN

### TS-006: Supersession stops the exercise run at a safe checkpoint without stale publication

- Protects: `AC-008`
- Risk/type: Consistency / Version conflict
- Given: an active exercise run bound to (vN, vM); a newer brief/blueprint version is confirmed mid-run
- When: the run reaches its next safe checkpoint
- Then: the run is marked `superseded`, stops, its pairs remain historical under the old version binding, no pair is published over the newer version, and starting exercises on the new version yields a new run (with a fresh tier choice)
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: confirm-version hooks from F002; mid-run confirmation injection
- Result/evidence: NOT RUN

### TS-007: SSE authoritative exercise event log, Last-Event-ID replay, and snapshot tier visibility

- Protects: `AC-004`, `AC-009`, `AC-019`
- Risk/type: Contract / Streaming
- Given: an active exercise run emitting ordered events with per-run monotonic ids
- When: a client disconnects and reconnects with `Last-Event-ID`, and another client polls the snapshot concurrently
- Then: replay returns exactly the missed events in order, no event is duplicated or lost, replay triggers no model work, and the snapshot always reflects authoritative state including per-lesson pair summaries and the recorded difficulty tier
- Level: API/Contract
- Automation target/path: `apps/backend/tests/test_exercise_generation.py` (SSE via httpx stream)
- Data/fixture/environment: deterministic event fixtures
- Result/evidence: NOT RUN

### TS-008: Stopping narration never affects the exercise run

- Protects: `AC-010`
- Risk/type: Streaming / Semantics
- Given: active exercise generation with narration streaming
- When: narration stop is invoked
- Then: the narration stream ends, run state/per-lesson progress and pair production continue to completion, and trace integrity is preserved
- Level: API
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: FakeModelAdapter narration
- Result/evidence: NOT RUN

### TS-009: Partial failure visibility and scoped resume

- Protects: `AC-005`, `AC-011`
- Risk/type: Partial Failure / Recovery
- Given: an exercise run where some lessons failed terminally after retries and others completed
- When: the teacher inspects the run and triggers resume
- Then: per-lesson outcomes and reasons are visible in the snapshot, resume re-dispatches the same run for failed/incomplete lessons only, and completed pairs are untouched
- Level: API + Component
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`; `apps/web/__tests__/exercise-panel.test.tsx`
- Data/fixture/environment: mixed-outcome fixture
- Result/evidence: NOT RUN

### TS-010: Resume rejects ineligible terminal states

- Protects: Exercise run state machine invariant (Spec State Transitions)
- Risk/type: Rule / Boundary
- Given: exercise runs in `terminal_failure`, `superseded`, `complete`
- When: resume is requested
- Then: each is rejected with an explicit state-conflict error naming the current state; no state regresses
- Level: API
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: state fixtures
- Result/evidence: NOT RUN

### TS-011: Authorized dual download with non-disclosing denial and file-parameter validation

- Protects: `AC-012`
- Risk/type: Authorization / Privacy
- Given: a completed pair; its owner; a different workspace's teacher; a pair record whose binary is missing; download requests with a missing or invalid `file` parameter
- When: download is requested by each
- Then: owner receives the exact stored binary for the requested file (checksum match, DOCX media type) — the exercise download serves the exercise file and the answer download serves the answer file, never the other; cross-workspace receives the authorization-denied class response without confirming existence; a missing/invalid `file` parameter is a validation error; missing-binary pairs are never in ready/downloadable state
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: two workspaces; MinIO object manipulation
- Result/evidence: NOT RUN

### TS-012: Invalid or mismatched pair never becomes ready

- Protects: `AC-014`, `AC-020`, artifact invariant
- Risk/type: Broken Office export / Pairing / Error
- Given: lessons whose rendered pairs are corrupt/empty, missing required D1 sections, numbering not starting at 1 or non-contiguous, item count outside configured bounds, an answer set missing one exercise number, an answer set with an orphan answer, or an empty/whitespace answer entry (injected renderer/model faults and fixture pairs)
- When: validation runs
- Then: each lesson enters failed with the specific structural or pairing reason, the pair never reaches ready, other lessons are unaffected, and neither file is downloadable
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: corrupted-bytes fixture; pair fixtures built with python-docx that are missing sections, mismatch-numbered, out-of-bounds, or empty-answer
- Result/evidence: NOT RUN

### TS-013: Complete per-stage trace with cost, latency, lesson-plan context, and difficulty

- Protects: `AC-013`, `AC-016`, `AC-018`, `AC-019`
- Risk/type: Observability / Evidence
- Given: an exercise run with mixed outcomes (success, failure, retry, cap or supersession)
- When: traces are reviewed in the owning workspace
- Then: every model call, tool call (render/validate pair), specialist transition, failure, and retry appears with prompt/output references, cost, and latency; each lesson's exercise-draft trace records the consumed lesson-plan content and blueprint objectives as its primary input context and names the bound difficulty tier; nothing appears outside the owning workspace
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: mixed-outcome fixture
- Result/evidence: NOT RUN

### TS-014: Project deletion cascades to exercise run data and binaries

- Protects: `AC-015`
- Risk/type: Privacy / Deletion
- Given: a project with exercise runs, exercise artifacts, events, traces, and stored DOCX binaries
- When: the project is deleted
- Then: all rows and object-storage binaries (both files of every pair) are removed; no orphaned events or files remain
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: deletion service; MinIO listing assertion
- Result/evidence: NOT RUN

### TS-015: Concurrent duplicate exercise starts converge on one run

- Protects: `AC-002`
- Risk/type: Concurrency / Transaction
- Given: the same project with the prerequisite met
- When: multiple exercise start requests race (threads/processes)
- Then: exactly one exercise run row exists for the bound versions and artifact kind (DB unique constraint), all callers receive the same run with one recorded tier, no duplicate model work begins, and coexisting lesson-plan/deck runs for the same versions are unaffected
- Level: Concurrency/Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: parallel transactions against PostgreSQL
- Result/evidence: NOT RUN

### TS-016: Provider hard failure after bounded retries is terminal with work preserved

- Protects: `AC-005`, Spec D5 taxonomy
- Risk/type: Error / Recovery boundary
- Given: a provider that fails persistently for lesson j after the retry budget
- When: retries exhaust
- Then: the exercise run ends in `terminal_failure` (or `partial_failure` when other lessons completed), completed pairs remain valid and downloadable, and resume is not offered for the terminal cause
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: persistent-failure FakeModelAdapter; retry budget fixture
- Result/evidence: NOT RUN

### TS-017: Object-storage write failure fails the lesson without faking success

- Protects: Spec Error Cases (storage boundary)
- Risk/type: Error / Consistency
- Given: MinIO write fails for one lesson (injected fault)
- When: the lesson's render step runs
- Then: the lesson enters failed with the storage reason, no ready pair is recorded, and other lessons continue
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: storage fault injection
- Result/evidence: NOT RUN

### TS-018: Cross-account non-disclosure on all F005 surfaces

- Protects: Authorization boundary
- Risk/type: Security / Privacy
- Given: teacher B attempts every F005 endpoint (start/snapshot/events/resume/download both files) on teacher A's project
- When: requests are made
- Then: every response is the authorization-denied class without existence disclosure
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: dual-workspace fixtures
- Result/evidence: NOT RUN

### TS-019: Generated exercise content is untrusted output

- Protects: Business rule (untrusted generated content)
- Risk/type: Injection
- Given: model exercise/answer output containing injection payloads (fake tool grants, policy text, prompt instructions) in items, instructions, and answer entries
- When: the workflow consumes and renders it
- Then: no tool beyond the registered render/validate pair tools is invoked, no policy or authorization changes, and the payload renders as inert document text in both files
- Level: Integration
- Automation target/path: `apps/backend/tests/test_exercise_generation.py`
- Data/fixture/environment: injection-payload FakeModelAdapter scripts
- Result/evidence: NOT RUN

### TS-020: Exercise panel states render correctly — tier group, both prerequisite kinds, pair summary

- Protects: `AC-003`, `AC-004`, `AC-017`, `AC-019`, `AC-020` (UI)
- Risk/type: UI state
- Given: snapshot fixtures for queued/generating/validating/complete/partial/capped/superseded/terminal/blocked, prerequisite fixtures (blueprint unconfirmed; lesson plans missing/incomplete), and the start surface with the tier radio group (no default, all three tiers)
- When: the exercise panel renders each and start is attempted without a tier
- Then: phase tracker, per-lesson pair states with item/category counts and validation status, outcome banners, cap usage, bound versions, and recorded tier display per D-EXPROG/D-EXART/D-EXDIFF; each unavailable state names its exact prerequisite and links to the right view; submit without a tier shows the field-level message and focus moves to the radio group; when a run exists the selector is replaced by the recorded tier; no in-browser preview exists
- Level: Component (Vitest + Testing Library)
- Automation target/path: `apps/web/__tests__/exercise-panel.test.tsx`
- Data/fixture/environment: mocked API client
- Result/evidence: NOT RUN

### TS-021: Partial failure interaction — reasons, resume, dual download

- Protects: `AC-011`, `AC-012` (UI)
- Risk/type: Interaction / Recovery
- Given: a partial-failure snapshot with per-lesson reasons
- When: the teacher reviews and triggers scoped resume (modal) and downloads both files of a completed pair
- Then: the modal names affected lessons, resume calls the endpoint once with loading/disabled states, the two download actions retrieve the correct authorized DOCX each, and terminal states show no resume
- Level: Component/Interaction
- Automation target/path: `apps/web/__tests__/exercise-panel.test.tsx`
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-022: Reconnect banner and narration stop in the UI

- Protects: `AC-009`, `AC-010` (UI)
- Risk/type: Interaction / Streaming
- Given: an SSE drop mid-progress and an active narration stream
- When: disconnect/stop occur
- Then: the reconnect banner states remote work continues and restores progress on replay; stopping narration stops display only while progress markers continue
- Level: Component
- Automation target/path: `apps/web/__tests__/exercise-panel.test.tsx`
- Data/fixture/environment: mocked event source
- Result/evidence: NOT RUN

### TS-023: Workspace-shell extension is behavior-preserving for existing views

- Protects: Seventh-view integration boundary (ux-ui.md D-EXGEN)
- Risk/type: Regression
- Given: the workspace shell extended with the `练习与答案` view consuming the shared artifact-run components unchanged
- When: the existing F003/F004 panel component suites and the workspace-panels suite run unchanged
- Then: every pre-existing web test passes without modification; the shared components expose no F005-only behavior to F003/F004 surfaces; the seventh tab navigates correctly alongside the existing six
- Level: Regression (Component)
- Automation target/path: `apps/web/__tests__/generation-panel.test.tsx` + `deck-panel.test.tsx` + `workspace-panels.test.tsx` (unchanged) + new seventh-tab assertions
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-024: Keyboard and screen-reader pass on the exercise flow

- Protects: Accessibility requirement (`docs/UX.md`, WCAG 2.2 AA)
- Risk/type: Accessibility
- Given: the implemented exercise view
- When: a manual keyboard/focus pass runs tier selection → prerequisite-gated start → leave/return → partial failure → resume → dual download, plus automated a11y checks
- Then: all actions keyboard reachable, the tier fieldset announces required state and error, focus managed per ux-ui.md, live-region announcements throttled and correct, no color-only cues, the two download buttons distinctly named
- Level: Accessibility (automated checks + manual/scripted pass)
- Automation target/path: Playwright a11y checks + recorded pass evidence
- Data/fixture/environment: implemented UI
- Result/evidence: NOT RUN

### TS-025: E2E blocked start — incomplete lesson plans route to the prerequisite

- Protects: `AC-017` end to end
- Risk/type: E2E / Boundary
- Given: an authenticated project with confirmed versions but no complete lesson-plan run
- When: the teacher opens `练习与答案`
- Then: the unavailable state names the lesson-plan prerequisite and links to `教案生成`; no exercise run exists and no start action is offered
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/exercise-journeys.spec.ts`
- Data/fixture/environment: compose services; no model calls expected
- Result/evidence: NOT RUN

### TS-026: E2E partial failure and scoped resume (fault-injected stack)

- Protects: `AC-005`, `AC-006`, `AC-011` end to end
- Risk/type: E2E / Recovery
- Given: the running stack with the deterministic fault instance (`LESSONCANVAS_MODEL_ADAPTER=fake`; scripted lesson-plan run completes, pair for lesson j fails after lessons 1..j-1 complete; real Worker)
- When: the teacher watches the exercise run fail partially, then triggers scoped resume
- Then: failed lessons show reasons, resume re-dispatches the same run, completed pairs stay downloadable without re-running, and the run reaches complete after the scripted fault clears
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/exercise-journeys.spec.ts`
- Data/fixture/environment: compose services; fake-adapter backend instance + real Worker; scripted per-lesson failure
- Result/evidence: NOT RUN

### TS-027: E2E supersession — new version stops the active exercise run

- Protects: `AC-008` end to end
- Risk/type: E2E / Version conflict
- Given: an active exercise run (live stack) and a confirmed newer brief/blueprint version mid-run
- When: the run reaches its safe checkpoint
- Then: the UI shows the superseded banner naming the newer version, old pairs remain historical, and starting exercises on the new version produces a new run (fresh tier choice) that completes
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/exercise-journeys.spec.ts`
- Data/fixture/environment: compose services; live model; mid-run confirmation via existing brief revision journey
- Result/evidence: NOT RUN

### TS-028: E2E cap exhaustion — capped state with preserved work

- Protects: `AC-007` end to end
- Risk/type: E2E / Cost boundary
- Given: the deterministic fault instance configured with an exercise-run model-call cap smaller than the unit requires
- When: exercise generation runs past the cap
- Then: the capped banner shows usage and recovery guidance, completed pairs remain downloadable, and no further model work occurs
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/exercise-journeys.spec.ts` (small-cap instance profile)
- Data/fixture/environment: fake-adapter backend instance with small cap env; real Worker
- Result/evidence: NOT RUN

### TS-029: E2E SSE reconnect and narration stop on a live exercise run

- Protects: `AC-009`, `AC-010` end to end
- Risk/type: E2E / Streaming
- Given: an active exercise run with progress streaming (live stack)
- When: the page reloads mid-run (worst-case disconnect) and narration is stopped
- Then: the view reconnects via `Last-Event-ID`, missed events restore progress without duplication, stopping narration stops display only, and the run completes unaffected
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/exercise-journeys.spec.ts`
- Data/fixture/environment: compose services; live model
- Result/evidence: NOT RUN

### TS-030: E2E happy path — completed lesson plans to downloadable pairs (live stack)

- Protects: `AC-001`..`AC-004` end to end
- Risk/type: E2E / Critical path
- Given: the authenticated teacher account with a completed lesson-plan run (existing journey)
- When: the teacher selects a difficulty tier, starts exercise generation, waits for completion, inspects the pair summary, and downloads both files of a pair
- Then: the full UI path works against the running system (API + Celery Worker + PostgreSQL + MinIO + live model per TQ-002); both downloads produce real DOCX files whose pair summaries match the artifact record
- Level: E2E (Playwright, `CLERK_E2E=1` gated)
- Automation target/path: `apps/web/e2e/exercise-journeys.spec.ts`
- Data/fixture/environment: compose services; real Worker; live DeepSeek
- Result/evidence: NOT RUN

### TS-031: Controlled manual Word open smoke (Spec D7)

- Protects: `AC-014` openability/editability beyond parser-level evidence
- Risk/type: Smoke / Evidence
- Given: pairs produced by the TS-030 live run
- When: a controlled manual pass opens each downloaded exercise and answer DOCX in Word/WPS
- Then: every file opens without repair, required sections are present, text is editable, numbering matches across the pair, and answer entries are non-empty; results recorded as delivery evidence
- Level: Smoke (manual, one-time, owner-observed)
- Automation target/path: recorded evidence in this document's Execution Evidence Snapshot
- Data/fixture/environment: local Office application; TS-030 artifacts
- Result/evidence: NOT RUN

## Scenario Selection Notes

- Load/performance runs: `N/A for F005` — bounded performance evidence belongs to F009 evaluation; per-stage latency is captured in traces (TS-013).
- Visual regression suite: `N/A for F005` — exercise panel states are covered by component-level assertions (TS-020..022); seventh-view integration is covered by the unchanged-behavior regression suite (TS-023), not visual baselines.
- Migration backward compatibility: additive schema only (exercise artifact table, run difficulty column); verified by the migration task's integration proof in the Plan (no legacy data rewrite).
- Regression protection: existing 124 backend + 30 web suites must stay green unchanged; the F003/F004 panel suites double as the shared-component behavior-preservation proof (TS-023).
- E2E environment risk: TS-026/TS-028 carry the known Clerk dev-instance session instability observed in F004 (M-1 residual); if blocked, substitute automated coverage plus a recorded residual applies per the same owner-approved pattern.

## Open Test Questions

| ID | Question | Severity | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Exercise-run cap default, per-lesson item-count bounds, and category-count bounds | Non-critical | Implementation assignee | Chosen in the Implementation Plan and recorded in settings; Spec behavior (cap authoritative, bounded grammar) is testable at any value (TS-005, TS-012) | RESOLVED |
| TQ-002 | E2E model provider and fault-injection strategy | Non-critical | `YMY / Project Owner` | Reuse the F003/F004 dual-instance pattern unchanged: default live stack (real DeepSeek + real Worker) for TS-027/029/030; deterministic fault instance (`LESSONCANVAS_MODEL_ADAPTER=fake` + small cap env) for TS-026/028 and the prerequisite E2E TS-025; component/integration suites stay fake-based | RESOLVED |
| TQ-003 | Deterministic construction of invalid/mismatched pair fixtures | Non-critical | Implementation assignee | python-docx builds the negatives directly in fixtures: missing sections, numbering off-by-one on either side, orphan answers, empty answer cells, out-of-bounds counts, corrupted bytes — all deterministic in CI (TS-012) | RESOLVED |
| TQ-004 | Scope of the manual Word smoke | Non-critical | `YMY / Project Owner` | One-time controlled pass over the TS-030 artifacts (both files of sampled pairs) recorded in the Execution Evidence Snapshot (Spec D7); CI carries no Office dependency; deeper file evidence may come with F009 | RESOLVED |

No Critical Test Question is `OPEN` or `DEFERRED`.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable and mapped. | YES | Traceability table covers AC-001..AC-020 |
| TR-02 | Happy Path, Alternative Flows, boundaries covered. | YES | TS-001/002 happy incl. prerequisite and tier boundaries; TS-003/004/009 alternatives; TS-005/010/012/015/016 boundaries |
| TR-03 | Error, Auth/Security, Regression covered. | YES | TS-011/018/019 security; TS-012/016/017 errors; regression via existing suites + seventh-view behavior-preservation (TS-023) |
| TR-04 | Idempotency, Concurrency, Transaction, Consistency covered. | YES | TS-001/003/004/006/015 |
| TR-05 | Retry/timeout, migration/compat, performance covered or N/A. | YES | TS-016/017; migration additive (Notes); performance N/A with reason |
| TR-06 | UI interaction/state, Accessibility, E2E covered per risk. | YES | TS-020/021/022/023 components; E2E TS-025/026/027/028/029/030 (live stack + deterministic fault instance); a11y TS-024 |
| TR-07 | Levels and automation targets appropriate, not implementation-only. | YES | All scenarios assert observable API/UI/DB/storage outcomes |
| TR-08 | Environment, data, fixtures, dependencies available. | YES | Existing harness reused; renderer is real python-docx; storage MinIO; fakes scripted; manual smoke scope owner-confirmed (TQ-004) |
| TR-09 | Bug reproduction/regression or confirmed surrogate. | YES | `N/A - new Feature, no Bug`; integration risk covered by TS-023 unchanged-suite proof |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open/deferred. | YES | All four TQs resolved, none Critical |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `41b391751a33`, UX/UI `ux-ui-f005-r1` / approved content `78923f6468b7`, plus their Gate Record manifests (VCS base `main @ 123523a`), `docs/TESTING.md`, and this artifact `test-design-f005-r1` @ `29b9ad5c42d2`
- Evidence checklist result: ALL YES (TR-01..TR-10)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `41b391751a33`
- Validated UI revision or complete skip-decision link: `ux-ui-f005-r1` / `78923f6468b7`
- Validated Test Design revision: `test-design-f005-r1` @ `29b9ad5c42d2`
- Validated at: 2026-08-31
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-31
- Approval scope: F005 Test Design at `test-design-f005-r1`

## Execution Evidence Snapshot (2026-08-31)

All 31 scenarios executed and passed:

| Suite | Evidence |
| --- | --- |
| TS-001..TS-019 | `apps/backend/tests/test_exercise_generation.py` — 26 tests green within the 150-test backend suite (real python-docx renderer + MinIO + PostgreSQL; concurrency via parallel transactions; prerequisite gate, tier validation and immutability, checkpoint resume with model-call accounting, cap, supersession, SSE replay, dual downloads, injection inertness, deletion cascade) |
| TS-020..TS-022 | `apps/web/__tests__/exercise-panel.test.tsx` — 9 tests green within the 39-test web suite |
| TS-023 | `apps/web/__tests__/generation-panel.test.tsx` + `deck-panel.test.tsx` + `workspace-panels.test.tsx` unchanged and green — shared `artifact-run.tsx` consumed unmodified; seventh tab navigates alongside the existing six |
| TS-024 | scripted keyboard pass incl. the tier fieldset (fault stack: radio focus + Space selection, Enter start, focus-verified dual downloads) — passed |
| TS-025 | exercise prerequisite gate E2E (fault stack; both unavailable kinds + startable after plans complete) — passed (17.5s after one intermittent Clerk dev-instance hang re-run, F004 M-1 class) |
| TS-026 | partial failure -> scoped resume -> complete on the fault stack (scripted TRANSIENT_FAIL exhausting bounded retries, then teacher resume) — passed |
| TS-027 | mid-run supersession of the active exercise run (live stack, real DeepSeek + real Worker) — passed |
| TS-028 | cap exhaustion on the small-cap fault stack (`LESSONCANVAS_MAX_MODEL_CALLS_PER_EXERCISE_RUN=1`; capped banner + lesson 1 pair downloadable) — passed (21.7s) |
| TS-029 | leave/reconnect/reload progress restoration on the live stack — passed (2.3m) |
| TS-030 | full happy path on the live stack (tier selection -> blocked-submit check -> complete -> pair summaries + both DOCX downloads) — passed (2.3m, after the live-defect fix below) |
| TS-031 | Word 16.0 COM open smoke over all 12 files of the TS-030 run's six pairs — every file opens without repair with correct titles and editable text (e.g. lesson-01: exercise 27 paragraphs/956 chars, answer 11/650; manifest with SHA-256 prefixes recorded at delivery) |

Execution profile note (recorded per TQ-002): the fault stack ran `LESSONCANVAS_MODEL_ADAPTER=fake` with **eager task execution** — the F003 recorded profile — because real-Worker Celery retries insert two 180 s default delays that exceed the journey budgets (F004's real-worker fault profile hit this and left TS-026/TS-028 as M-1 residuals); the live stack ran real DeepSeek + real Celery Worker (solo pool) for TS-027/029/030; web served from the production build (`next start`); journeys executed serially (`--workers=1`, shared persistent Clerk profile); Clerk E2E uses the `@clerk/testing` token. Environment hygiene: leftover E2E projects had filled the workspace quota (429 on create); they were cascade-deleted before the passing runs.

Live-model defect found and fixed during TS-030 (mirrors F004's renderer-defect pattern): writing-task reference answers are naturally multi-line, and the pairing validator's numbered-entry regex anchored content at the first line end (`(.*)$`), so a pair with a multi-line answer was falsely judged `missing answers: [N]`. Fix: the entry anchor now requires only the leading `N.` and captures across newlines (DOTALL); renderer unchanged; regression test `test_pair_validation_accepts_multi_line_writing_answers` added; all captured live drafts replay green (the one out-of-bounds 6-category draft is correctly still rejected and recovered by the bounded retry). Backend suite re-verified after the fix: 150 passed + ruff clean.

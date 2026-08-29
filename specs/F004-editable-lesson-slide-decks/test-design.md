# Test Design: F004 Editable Lesson Slide Decks

## Inputs and Environment

- Spec: `specs/F004-editable-lesson-slide-decks/spec.md` @ `b913da61ec40` (`SPEC READY` PASS)
- UX/UI: `specs/F004-editable-lesson-slide-decks/ux-ui.md` @ `ux-ui-f004-r1` / approved content `05e5748c9a4d` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (contain full manifests; VCS base `b727734`)
- Environment: existing deterministic harness — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter for logic, Clerk token fixtures; live DeepSeek only for separately authorized live evidence; real `python-pptx` renderer in every automated suite
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E), manual keyboard/a11y pass, one controlled manual Office open smoke (Spec D7)

## Risk Inventory

| Risk (from TESTING.md map + Spec) | F004 exposure | Coverage |
| --- | --- | --- |
| Duplicate submission or retry | Duplicate model cost / deck artifacts | TS-001, TS-015 |
| Worker or provider failure loses work | Deck generation restarts from zero | TS-003, TS-004, TS-016 |
| Upstream revision during generation | Stale decks overwrite newer version | TS-006 |
| Broken Office exports | Unopenable or non-editable PPTX | TS-002, TS-012, TS-031 |
| Prerequisite bypass | Decks drift from confirmed lesson plans | TS-001, TS-013, TS-025 |
| Long-task UI ambiguity | Teacher retries or loses recovery path | TS-020, TS-021, TS-022 |
| Cross-account access | Private deck artifacts/traces leak | TS-011, TS-018 |
| Prompt or document injection via generated content | Content changes policy / grants tools | TS-019 |
| Streaming interruption or reconnect | Duplicate work or lost progress | TS-007, TS-022 |
| Cost runaway | Deck-run cap not enforced | TS-005 |
| Shared-component refactor regression (D-DECKDS) | F003 教案生成 behavior changes silently | TS-023 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 complete valid deck set | TS-002, TS-030 |
| AC-002 idempotent start | TS-001, TS-015 |
| AC-003 fast acknowledgement | TS-001, TS-020 |
| AC-004 progress + structure summary visibility | TS-007, TS-020, TS-030 |
| AC-005 transient failure resume, completed work intact | TS-003, TS-009, TS-026 |
| AC-006 Worker crash checkpoint resume | TS-003, TS-004, TS-026 |
| AC-007 deck-run model-call cap | TS-005, TS-028 |
| AC-008 supersession | TS-006, TS-027 |
| AC-009 SSE replay | TS-007, TS-022, TS-029 |
| AC-010 narration stop | TS-008, TS-022, TS-029 |
| AC-011 partial visibility + resume | TS-009, TS-021, TS-026 |
| AC-012 authorized download | TS-011, TS-021 |
| AC-013 complete trace | TS-013 |
| AC-014 structural validation incl. editability | TS-002, TS-012, TS-031 |
| AC-015 deletion cascade | TS-014 |
| AC-016 language mode | TS-002, TS-013 |
| AC-017 lesson-plan prerequisite gate | TS-001, TS-020, TS-025 |
| AC-018 lesson-plan context recorded in trace | TS-013 |

## Test Scenarios

### TS-001: Deck start binds confirmed versions and the complete lesson-plan run, idempotent, gated

- Protects: `AC-002`, `AC-003`, `AC-017`
- Risk/type: Happy / Idempotency / Boundary
- Given: a project with confirmed brief vN + blueprint vM and a complete lesson-plan run for (vN, vM); a project without confirmed versions; a project with confirmed versions but no or an incomplete lesson-plan run
- When: deck start is requested (including double submit)
- Then: with the prerequisite met, a deck run bound to (vN, vM) and the lesson-plan run is created/returned identically on duplicates and acknowledged with a queued snapshot; without confirmed versions or without a complete lesson-plan run, a requirement error names the exact failed prerequisite and no deck run or model call is created
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: seeded confirmed versions + completed lesson-plan run via existing services; FakeModelAdapter
- Result/evidence: NOT RUN

### TS-002: Full deck run completes every lesson with structurally valid editable PPTX in the bound language mode

- Protects: `AC-001`, `AC-014`, `AC-016`
- Risk/type: Happy / Contract
- Given: a completed lesson-plan run for a confirmed blueprint with K lessons and language mode (zh / en / bilingual variants)
- When: the deck workflow runs to completion with the real python-pptx renderer
- Then: every lesson has a deck that is openable by the parser, contains the required D1 slides (title, objectives, key/difficult points, at least one stage slide, homework), presents non-empty editable text frames, records a slide count within configured bounds, follows the language mode, and the run reaches `complete`
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: FakeModelAdapter scripted decks derived from scripted lesson plans; real renderer + MinIO
- Result/evidence: NOT RUN

### TS-003: Per-deck checkpoint — resume skips completed lessons

- Protects: `AC-005`, `AC-006`
- Risk/type: Recovery / Idempotency
- Given: a deck run where lessons 1..j completed and lesson j+1 fails (injected provider error)
- When: the run resumes (retry or teacher resume)
- Then: lessons 1..j keep their original decks (unchanged object keys/checksums), only lessons j+1.. run, and total model calls increase by exactly the incomplete lessons' work
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: FakeModelAdapter with per-lesson failure script; call counter assertion
- Result/evidence: NOT RUN

### TS-004: Worker crash mid-deck-run resumes from checkpoint on re-dispatch

- Protects: `AC-006`
- Risk/type: Recovery / Concurrency
- Given: a deck run interrupted without completing its current lesson (simulated crash)
- When: the same run id is re-dispatched (Celery redelivery / resume endpoint)
- Then: the run continues from the last per-lesson checkpoint, no completed deck re-runs, and no duplicate artifact versions are published
- Level: Integration (service-level crash simulation + Celery eager redelivery)
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: eager Celery; injected abrupt termination
- Result/evidence: NOT RUN

### TS-005: Deck-run model-call cap is authoritative

- Protects: `AC-007`
- Risk/type: Boundary / Cost
- Given: a deck run with cap C smaller than the work required for K lessons
- When: deck generation runs
- Then: exactly at the cap no further model call begins, the run enters `capped_failure`, completed decks remain valid and downloadable, and the API exposes cap usage and a recovery path
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: small cap setting; FakeModelAdapter call counter
- Result/evidence: NOT RUN

### TS-006: Supersession stops the deck run at a safe checkpoint without stale publication

- Protects: `AC-008`
- Risk/type: Consistency / Version conflict
- Given: an active deck run bound to (vN, vM); a newer brief/blueprint version is confirmed mid-run
- When: the run reaches its next safe checkpoint
- Then: the run is marked `superseded`, stops, its decks remain historical under the old version binding, no deck is published over the newer version, and starting decks on the new version yields a new run
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: confirm-version hooks from F002; mid-run confirmation injection
- Result/evidence: NOT RUN

### TS-007: SSE authoritative deck event log and Last-Event-ID replay

- Protects: `AC-004`, `AC-009`
- Risk/type: Contract / Streaming
- Given: an active deck run emitting ordered events with per-run monotonic ids
- When: a client disconnects and reconnects with `Last-Event-ID`, and another client polls the snapshot concurrently
- Then: replay returns exactly the missed events in order, no event is duplicated or lost, replay triggers no model work, and the snapshot always reflects authoritative state including per-lesson slide counts
- Level: API/Contract
- Automation target/path: `apps/backend/tests/test_deck_generation.py` (SSE via httpx stream)
- Data/fixture/environment: deterministic event fixtures
- Result/evidence: NOT RUN

### TS-008: Stopping narration never affects the deck run

- Protects: `AC-010`
- Risk/type: Streaming / Semantics
- Given: active deck generation with narration streaming
- When: narration stop is invoked
- Then: the narration stream ends, run state/per-lesson progress and deck production continue to completion, and trace integrity is preserved
- Level: API
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: FakeModelAdapter narration
- Result/evidence: NOT RUN

### TS-009: Partial failure visibility and scoped resume

- Protects: `AC-005`, `AC-011`
- Risk/type: Partial Failure / Recovery
- Given: a deck run where some lessons failed terminally after retries and others completed
- When: the teacher inspects the run and triggers resume
- Then: per-lesson outcomes and reasons are visible in the snapshot, resume re-dispatches the same run for failed/incomplete lessons only, and completed decks are untouched
- Level: API + Component
- Automation target/path: `apps/backend/tests/test_deck_generation.py`; `apps/web/__tests__/deck-panel.test.tsx`
- Data/fixture/environment: mixed-outcome fixture
- Result/evidence: NOT RUN

### TS-010: Resume rejects ineligible terminal states

- Protects: Deck run state machine invariant (Spec State Transitions)
- Risk/type: Rule / Boundary
- Given: deck runs in `terminal_failure`, `superseded`, `complete`
- When: resume is requested
- Then: each is rejected with an explicit state-conflict error naming the current state; no state regresses
- Level: API
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: state fixtures
- Result/evidence: NOT RUN

### TS-011: Authorized deck download with non-disclosing denial

- Protects: `AC-012`
- Risk/type: Authorization / Privacy
- Given: a completed deck; its owner; a different workspace's teacher; a deck record whose binary is missing
- When: download is requested by each
- Then: owner receives the exact stored binary (checksum match, PPTX media type); cross-workspace receives the authorization-denied class response without confirming existence; missing-binary decks are never in ready/downloadable state
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: two workspaces; MinIO object manipulation
- Result/evidence: NOT RUN

### TS-012: Invalid or non-editable deck never becomes ready

- Protects: `AC-014`, artifact invariant
- Risk/type: Broken Office export / Error
- Given: lessons whose rendered files are corrupt/empty, missing required D1 slides, image-only slides with no text frames, or exceed the configured slide-count bound (injected renderer/model faults and fixture decks)
- When: validation runs
- Then: each lesson enters failed with the structural reason, the deck never reaches ready, other lessons are unaffected, and the file is not downloadable
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: corrupted-bytes fixture; deck fixtures built with python-pptx that are missing sections, picture-only, or over/under the count bound
- Result/evidence: NOT RUN

### TS-013: Complete per-stage trace with cost, latency, and lesson-plan context

- Protects: `AC-013`, `AC-018`, `AC-016`
- Risk/type: Observability / Evidence
- Given: a deck run with mixed outcomes (success, failure, retry, cap or supersession)
- When: traces are reviewed in the owning workspace
- Then: every model call, tool call (render/validate deck), specialist transition, failure, and retry appears with prompt/output references, cost, and latency; each lesson's deck-draft trace records the consumed lesson-plan content as its primary input context; nothing appears outside the owning workspace
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: mixed-outcome fixture
- Result/evidence: NOT RUN

### TS-014: Project deletion cascades to deck run data and binaries

- Protects: `AC-015`
- Risk/type: Privacy / Deletion
- Given: a project with deck runs, deck artifacts, events, traces, and stored PPTX binaries
- When: the project is deleted
- Then: all rows and object-storage binaries are removed; no orphaned events or files remain
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: deletion service; MinIO listing assertion
- Result/evidence: NOT RUN

### TS-015: Concurrent duplicate deck starts converge on one run

- Protects: `AC-002`
- Risk/type: Concurrency / Transaction
- Given: the same project with the prerequisite met
- When: multiple deck start requests race (threads/processes)
- Then: exactly one deck run row exists for the bound versions and artifact kind (DB unique constraint), all callers receive the same run, and no duplicate model work begins; the coexisting lesson-plan run for the same versions is unaffected
- Level: Concurrency/Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: parallel transactions against PostgreSQL
- Result/evidence: NOT RUN

### TS-016: Provider hard failure after bounded retries is terminal with work preserved

- Protects: `AC-005`, Spec D5 taxonomy
- Risk/type: Error / Recovery boundary
- Given: a provider that fails persistently for lesson j after the retry budget
- When: retries exhaust
- Then: the deck run ends in `terminal_failure` (or `partial_failure` when other lessons completed), completed decks remain valid and downloadable, and resume is not offered for the terminal cause
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: persistent-failure FakeModelAdapter; retry budget fixture
- Result/evidence: NOT RUN

### TS-017: Object-storage write failure fails the lesson without faking success

- Protects: Spec Error Cases (storage boundary)
- Risk/type: Error / Consistency
- Given: MinIO write fails for one lesson (injected fault)
- When: the lesson's render step runs
- Then: the lesson enters failed with the storage reason, no ready deck is recorded, and other lessons continue
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: storage fault injection
- Result/evidence: NOT RUN

### TS-018: Cross-account non-disclosure on all F004 surfaces

- Protects: Authorization boundary
- Risk/type: Security / Privacy
- Given: teacher B attempts every F004 endpoint (start/snapshot/events/resume/download) on teacher A's project
- When: requests are made
- Then: every response is the authorization-denied class without existence disclosure
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: dual-workspace fixtures
- Result/evidence: NOT RUN

### TS-019: Generated deck content is untrusted output

- Protects: Business rule (untrusted generated content)
- Risk/type: Injection
- Given: model deck output containing injection payloads (fake tool grants, policy text, prompt instructions) in slide text and speaker notes
- When: the workflow consumes and renders it
- Then: no tool beyond the registered render/validate deck tools is invoked, no policy or authorization changes, and the payload renders as inert slide/notes text
- Level: Integration
- Automation target/path: `apps/backend/tests/test_deck_generation.py`
- Data/fixture/environment: injection-payload FakeModelAdapter scripts
- Result/evidence: NOT RUN

### TS-020: Deck panel states render correctly, including both prerequisite kinds and structure summary

- Protects: `AC-003`, `AC-004`, `AC-017` (UI)
- Risk/type: UI state
- Given: snapshot fixtures for queued/generating/validating/complete/partial/capped/superseded/terminal/blocked, plus prerequisite fixtures (blueprint unconfirmed; lesson plans missing/incomplete)
- When: the deck panel renders each
- Then: phase tracker, per-lesson deck states with slide counts and validation status, outcome banners, cap usage, and bound versions display per D-DECKPROG/D-DECKART; each unavailable state names its exact prerequisite and links to the right view; no in-browser preview exists
- Level: Component (Vitest + Testing Library)
- Automation target/path: `apps/web/__tests__/deck-panel.test.tsx`
- Data/fixture/environment: mocked API client
- Result/evidence: NOT RUN

### TS-021: Partial failure interaction — reasons, resume, download

- Protects: `AC-011`, `AC-012` (UI)
- Risk/type: Interaction / Recovery
- Given: a partial-failure snapshot with per-lesson reasons
- When: the teacher reviews and triggers scoped resume (modal) and downloads a completed deck
- Then: the modal names affected lessons, resume calls the endpoint once with loading/disabled states, download retrieves the authorized PPTX, and terminal states show no resume
- Level: Component/Interaction
- Automation target/path: `apps/web/__tests__/deck-panel.test.tsx`
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-022: Reconnect banner and narration stop in the UI

- Protects: `AC-009`, `AC-010` (UI)
- Risk/type: Interaction / Streaming
- Given: an SSE drop mid-progress and an active narration stream
- When: disconnect/stop occur
- Then: the reconnect banner states remote work continues and restores progress on replay; stopping narration stops display only while progress markers continue
- Level: Component
- Automation target/path: `apps/web/__tests__/deck-panel.test.tsx`
- Data/fixture/environment: mocked event source
- Result/evidence: NOT RUN

### TS-023: Design System promotion is behavior-preserving for F003 surfaces

- Protects: D-DECKDS refactor boundary (ux-ui.md UIQ-003)
- Risk/type: Regression
- Given: the shared per-lesson artifact progress list and run-outcome banner components extracted per D-DECKDS and consumed by both `教案生成` and `课件生成`
- When: the existing F003 generation-panel component suite and the shared-component suite run unchanged
- Then: every pre-existing F003 web test passes without modification (same states, copy, and semantics); the shared components expose no F004-only behavior to F003 surfaces
- Level: Regression (Component)
- Automation target/path: `apps/web/__tests__/generation-panel.test.tsx` (unchanged) + new shared-component tests
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-024: Keyboard and screen-reader pass on the deck flow

- Protects: Accessibility requirement (`docs/UX.md`, WCAG 2.2 AA)
- Risk/type: Accessibility
- Given: the implemented deck view
- When: a manual keyboard/focus pass runs prerequisite-gated start → leave/return → partial failure → resume → download, plus automated a11y checks
- Then: all actions keyboard reachable, focus managed per ux-ui.md, live-region announcements throttled and correct, no color-only cues
- Level: Accessibility (automated checks + manual/scripted pass)
- Automation target/path: Playwright a11y checks + recorded pass evidence
- Data/fixture/environment: implemented UI
- Result/evidence: NOT RUN

### TS-025: E2E blocked start — incomplete lesson plans route to the prerequisite

- Protects: `AC-017` end to end
- Risk/type: E2E / Boundary
- Given: an authenticated project with confirmed versions but no complete lesson-plan run
- When: the teacher opens `课件生成`
- Then: the unavailable state names the lesson-plan prerequisite and links to `教案生成`; no deck run exists and no start action is offered
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/deck-journeys.spec.ts`
- Data/fixture/environment: compose services; no model calls expected
- Result/evidence: NOT RUN

### TS-026: E2E partial failure and scoped resume (fault-injected stack)

- Protects: `AC-005`, `AC-006`, `AC-011` end to end
- Risk/type: E2E / Recovery
- Given: the running stack with the deterministic fault instance (`LESSONCANVAS_MODEL_ADAPTER=fake`; scripted lesson-plan run completes, deck for lesson j fails after lessons 1..j-1 complete; real Worker)
- When: the teacher watches the deck run fail partially, then triggers scoped resume
- Then: failed lessons show reasons, resume re-dispatches the same run, completed decks stay downloadable without re-running, and the run reaches complete after the scripted fault clears
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/deck-journeys.spec.ts`
- Data/fixture/environment: compose services; fake-adapter backend instance + real Worker; scripted per-lesson failure
- Result/evidence: NOT RUN

### TS-027: E2E supersession — new version stops the active deck run

- Protects: `AC-008` end to end
- Risk/type: E2E / Version conflict
- Given: an active deck run (live stack) and a confirmed newer brief/blueprint version mid-run
- When: the run reaches its safe checkpoint
- Then: the UI shows the superseded banner naming the newer version, old decks remain historical, and starting decks on the new version produces a new run that completes
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/deck-journeys.spec.ts`
- Data/fixture/environment: compose services; live model; mid-run confirmation via existing brief revision journey
- Result/evidence: NOT RUN

### TS-028: E2E cap exhaustion — capped state with preserved work

- Protects: `AC-007` end to end
- Risk/type: E2E / Cost boundary
- Given: the deterministic fault instance configured with a deck-run model-call cap smaller than the unit requires
- When: deck generation runs past the cap
- Then: the capped banner shows usage and recovery guidance, completed decks remain downloadable, and no further model work occurs
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/deck-journeys.spec.ts` (small-cap instance profile)
- Data/fixture/environment: fake-adapter backend instance with small cap env; real Worker
- Result/evidence: NOT RUN

### TS-029: E2E SSE reconnect and narration stop on a live deck run

- Protects: `AC-009`, `AC-010` end to end
- Risk/type: E2E / Streaming
- Given: an active deck run with progress streaming (live stack)
- When: the page reloads mid-run (worst-case disconnect) and narration is stopped
- Then: the view reconnects via `Last-Event-ID`, missed events restore progress without duplication, stopping narration stops display only, and the run completes unaffected
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/deck-journeys.spec.ts`
- Data/fixture/environment: compose services; live model
- Result/evidence: NOT RUN

### TS-030: E2E happy path — completed lesson plans to downloadable decks (live stack)

- Protects: `AC-001`..`AC-004` end to end
- Risk/type: E2E / Critical path
- Given: the authenticated teacher account with a completed lesson-plan run (existing journey)
- When: the teacher starts deck generation, waits for completion, inspects the structure summary, and downloads a deck
- Then: the full UI path works against the running system (API + Celery Worker + PostgreSQL + MinIO + live model per TQ-002); downloads produce a real PPTX whose structure summary matches the artifact record
- Level: E2E (Playwright, `CLERK_E2E=1` gated)
- Automation target/path: `apps/web/e2e/authenticated.spec.ts` (extended) or `deck-journeys.spec.ts`
- Data/fixture/environment: compose services; real Worker; live DeepSeek
- Result/evidence: NOT RUN

### TS-031: Controlled manual Office open smoke (Spec D7)

- Protects: `AC-014` editability/openability beyond parser-level evidence
- Risk/type: Smoke / Evidence
- Given: decks produced by the TS-030 live run
- When: a controlled manual pass opens each downloaded deck in PowerPoint/WPS
- Then: every deck opens without repair, required slides are present, slide text is editable, and speaker notes are visible; results recorded as delivery evidence
- Level: Smoke (manual, one-time, owner-observed)
- Automation target/path: recorded evidence in this document's Execution Evidence Snapshot
- Data/fixture/environment: local Office application; TS-030 artifacts
- Result/evidence: NOT RUN

## Scenario Selection Notes

- Load/performance runs: `N/A for F004` — bounded performance evidence belongs to F009 evaluation; per-stage latency is captured in traces (TS-013).
- Visual regression suite: `N/A for F004` — deck panel states are covered by component-level assertions (TS-020..022); D-DECKDS promotion is covered by the unchanged-behavior regression suite (TS-023), not visual baselines.
- Migration backward compatibility: additive schema only (deck artifact identity); verified by the migration task's integration proof in the Plan (no legacy data rewrite).
- Regression protection: existing 102 backend + 22 web suites must stay green unchanged; the F003 panel suite doubles as the D-DECKDS behavior-preservation proof (TS-023).

## Open Test Questions

| ID | Question | Severity | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Deck-run cap default and per-deck slide-count bounds | Non-critical | Implementation assignee | Chosen in the Implementation Plan and recorded in settings; Spec behavior (cap authoritative, bounded structure) is testable at any value (TS-005, TS-012) | RESOLVED |
| TQ-002 | E2E model provider and fault-injection strategy | Non-critical | `YMY / Project Owner` | Reuse the F003 dual-instance pattern unchanged: default live stack (real DeepSeek + real Worker) for TS-027/029/030; deterministic fault instance (`LESSONCANVAS_MODEL_ADAPTER=fake` + small cap env) for TS-026/028 and the prerequisite E2E TS-025; component/integration suites stay fake-based | RESOLVED |
| TQ-003 | Deterministic construction of non-editable/invalid deck fixtures | Non-critical | Implementation assignee | python-pptx builds the negatives directly in fixtures: picture-only slides, missing required sections, empty text frames, over/under count bounds, corrupted bytes — all deterministic in CI (TS-012) | RESOLVED |
| TQ-004 | Scope of the manual Office smoke | Non-critical | `YMY / Project Owner` | One-time controlled pass over the TS-030 artifacts recorded in the Execution Evidence Snapshot (Spec D7); CI carries no Office dependency; deeper file evidence may come with F009 | RESOLVED |

No Critical Test Question is `OPEN` or `DEFERRED`.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable and mapped. | YES | Traceability table covers AC-001..AC-018 |
| TR-02 | Happy Path, Alternative Flows, boundaries covered. | YES | TS-001/002 happy incl. prerequisite boundary; TS-003/004/009 alternatives; TS-005/010/012/015/016 boundaries |
| TR-03 | Error, Auth/Security, Regression covered. | YES | TS-011/018/019 security; TS-012/016/017 errors; regression via existing suites + D-DECKDS behavior-preservation (TS-023) |
| TR-04 | Idempotency, Concurrency, Transaction, Consistency covered. | YES | TS-001/003/004/006/015 |
| TR-05 | Retry/timeout, migration/compat, performance covered or N/A. | YES | TS-016/017; migration additive (Notes); performance N/A with reason |
| TR-06 | UI interaction/state, Accessibility, E2E covered per risk. | YES | TS-020/021/022/023 components; E2E TS-025/026/027/028/029/030 (live stack + deterministic fault instance); a11y TS-024 |
| TR-07 | Levels and automation targets appropriate, not implementation-only. | YES | All scenarios assert observable API/UI/DB/storage outcomes |
| TR-08 | Environment, data, fixtures, dependencies available. | YES | Existing harness reused; renderer is real python-pptx; storage MinIO; fakes scripted; manual smoke scope owner-confirmed (TQ-004) |
| TR-09 | Bug reproduction/regression or confirmed surrogate. | YES | `N/A - new Feature, no Bug`; refactor risk covered by TS-023 unchanged-suite proof |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open/deferred. | YES | All four TQs resolved, none Critical |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `b913da61ec40`, UX/UI `ux-ui-f004-r1` / approved content `05e5748c9a4d`, plus their Gate Record manifests (VCS base `b727734`), `docs/TESTING.md`, and this artifact `test-design-f004-r1` @ `4afef155b09f`
- Evidence checklist result: ALL YES (TR-01..TR-10)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `b913da61ec40`
- Validated UI revision or complete skip-decision link: `ux-ui-f004-r1` / `05e5748c9a4d`
- Validated Test Design revision: `test-design-f004-r1` @ `4afef155b09f`
- Validated at: 2026-08-29
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-29
- Approval scope: F004 Test Design at `test-design-f004-r1`

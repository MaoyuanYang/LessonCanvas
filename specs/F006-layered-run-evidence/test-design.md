# Test Design: F006 Layered Run Evidence

## Inputs and Environment

- Spec: `specs/F006-layered-run-evidence/spec.md` @ `b43922d2cc17` (`SPEC READY` PASS)
- UX/UI: `specs/F006-layered-run-evidence/ux-ui.md` @ `ux-ui-f006-r1` / `4bff46959bb0` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (contain full manifests; VCS base `main @ 5804e86`)
- Environment: existing deterministic harness — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter for logic, Clerk token fixtures; live DeepSeek only for separately authorized live evidence
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E + a11y checks), manual keyboard/screen-reader pass (B-001)

## Risk Inventory

| Risk (from TESTING.md map + Spec) | F006 exposure | Coverage |
| --- | --- | --- |
| Cross-account access / existence disclosure | Trace payloads leak across workspaces | TS-006, TS-020 |
| Read-only promise broken | Evidence view mutates run/quota state | TS-007, TS-018 |
| Pagination gaps/duplicates under concurrent appends | Incomplete or doubled evidence pages | TS-003 |
| Missing telemetry masked as zero/complete | Legacy runs look costed or fully instrumented | TS-004, TS-005 |
| Cost misread as billed truth | Estimate presented as provider billing | TS-005, TS-016 |
| Prompt/output content treated as trusted | Injection via trace payloads | TS-015, TS-020 |
| Legacy endpoint removal regression | Old trace endpoint tests/surfaces break | TS-013, TS-019 |
| Migration corrupts existing traces | Additive columns break legacy rows | TS-014 |
| Narration quota/cost discipline | Explanation streaming creates unbounded model cost | TS-009 |
| Deletion leaves evidence copies | Traces survive project/account deletion | TS-008 |
| Workspace-shell extension regression | Eighth view breaks existing panels | TS-019 |
| Known streaming fragility (F003 residual) | SSE early-drop root cause unresolved | TS-023 |
| Known teardown fragility (F004 M-2) | StaleDataError run-teardown semantics unresolved | TS-024 |
| Accessibility debt (STAGE B-001) | Keyboard pass pending at this UI touch | TS-022 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 teacher summary first | TS-002, TS-016, TS-020 |
| AC-002 technical expansion | TS-003, TS-010, TS-016, TS-020 |
| AC-003 cursor paging | TS-003, TS-012, TS-016 |
| AC-004 missing telemetry explicit | TS-004, TS-016 |
| AC-005 estimated cost labeling | TS-005, TS-010, TS-016 |
| AC-006 no cross-user disclosure | TS-006, TS-020 |
| AC-007 read-only interactions | TS-007, TS-018 |
| AC-008 deletion | TS-008 |
| AC-009 explanation narration | TS-009, TS-017, TS-020, TS-021 |
| AC-010 safe display/copy | TS-015, TS-016 |
| AC-011 discovery/planning coverage | TS-001, TS-002, TS-011, TS-020 |
| AC-012 superseded marking | TS-002, TS-016 |
| AC-013 keyboard/screen reader | TS-022 |
| AC-014 legacy endpoint removal | TS-013 |
| AC-015 small-screen boundary | TS-016, TS-018 |

## Test Scenarios

### TS-001: Run inventory covers all five kinds with summary metrics

- Protects: `AC-011`
- Risk/type: Happy / Contract
- Given: a project with discovery, planning, lesson-plan, slide-deck, and exercise runs in mixed states (active, settled, superseded)
- When: the owner requests the evidence inventory
- Then: every run appears exactly once with kind, teacher-language status, bound versions where applicable, recency, model-call usage vs cap, aggregate estimated cost, and artifact/scope counts; runs from other projects never appear; an empty project yields an empty list (not an error)
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: seeded runs via existing services; FakeModelAdapter
- Result/evidence: NOT RUN

### TS-002: Layer-1 summary is teacher-readable, version-bound, and honest about state

- Protects: `AC-001`, `AC-011`, `AC-012`
- Risk/type: Happy / Contract
- Given: one settled partial-failure generation run with per-lesson reasons, one superseded generation run with a newer confirmed version, one draft_ready discovery run, one provider_failed planning run
- When: the owner opens each run's summary
- Then: each summary shows bound brief/blueprint versions, authoritative status in teacher language, per-lesson/scope outcomes with failure reasons, recovery pointers naming the owning surface, model-call usage vs cap, aggregate estimated cost and latency, and evidence-category availability; the superseded run is marked with the newer version identified and never presented as current; discovery/planning summaries surface interview-round structure; no raw prompt text appears in Layer 1
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: mixed-state fixtures
- Result/evidence: NOT RUN

### TS-003: Technical event stream is complete, ordered, payload-bearing, and cursor-stable under concurrent appends

- Protects: `AC-002`, `AC-003`
- Risk/type: Contract / Concurrency
- Given: a run with many recorded events (model, tool, phase, lesson, run events spanning lessons) exceeding page size; a Worker appending new events while pages are read
- When: pages are fetched sequentially by cursor (and with an event-kind filter)
- Then: events return in stable order with per-event kind, lesson scope where applicable, latency, tokens, estimated cost, model identifier, and full prompt/response payloads; consecutive pages neither skip nor duplicate any event under concurrent appends; the filter returns only matching kinds; cursor exhaustion returns an explicit end marker
- Level: Integration/API + Concurrency
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: bulk event fixture; parallel append session
- Result/evidence: NOT RUN

### TS-004: Legacy events without token/cost/model data display explicit gaps while status stays authoritative

- Protects: `AC-004`
- Risk/type: Boundary / Honesty
- Given: pre-F006 trace rows (no token/cost/model columns populated) attached to a settled run, plus a narration-gap run
- When: summary and event pages are served
- Then: each legacy row carries an explicit not-recorded marker, the summary carries a telemetry-gap notice, and the run/artifact status comes from run tables unchanged — never inferred from trace completeness
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: legacy-shape fixtures (columns null)
- Result/evidence: NOT RUN

### TS-005: Estimated cost derives from the settings price table and is labeled, never zero-masked

- Protects: `AC-005`
- Risk/type: Calculation / Boundary
- Given: token usage (prompt/completion) recorded per event; a configured price table; a second table with different prices; events with zero or missing usage
- When: cost is computed and displayed
- Then: cost equals tokens x configured per-token prices for the event's model, changes when the table changes at write time only (stored, not recomputed for old events), and events without usage show not-recorded rather than 0 USD; the API payload marks cost as estimated
- Level: Unit + Integration
- Automation target/path: `apps/backend/tests/test_evidence.py` (cost computation unit + persisted-value assertions)
- Data/fixture/environment: price-table settings fixture
- Result/evidence: NOT RUN

### TS-006: Authorization boundary — non-disclosing denial on every evidence surface

- Protects: `AC-006`
- Risk/type: Security / Privacy
- Given: teacher A's project with runs; teacher B; an unauthenticated caller; a run id from another workspace; a random run id inside A's project
- When: each caller requests inventory, summary, events (all filter/paging variants), narration start, and narration stream
- Then: teacher B and the unauthenticated caller receive the authorization-denied class without confirming the project, run, or content existence; teacher A receives not-found for a foreign run id; no error body contains prompt text, storage paths, or provider identifiers beyond the taxonomy
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: dual-workspace fixtures
- Result/evidence: NOT RUN

### TS-007: Evidence interactions change no business state

- Protects: `AC-007`
- Risk/type: Invariant / Read-only
- Given: runs in active and settled states with known snapshots (run rows, artifact rows, quota counters, version tables)
- When: the full interaction sequence runs (inventory, summary, every events page, filter, narration start + stream + stop)
- Then: every run row, artifact row, event log, quota counter, and version table is byte-identical before and after, except the narration's own trace event and its workspace-quota reservation; no run status transition occurs
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: state snapshot diffing
- Result/evidence: NOT RUN

### TS-008: Deletion removes all evidence surfaces with their backing data

- Protects: `AC-008`
- Risk/type: Privacy / Deletion
- Given: a project with all five run kinds, events, traces, artifacts, binaries, and recorded narrations
- When: the project (and in a second case the account) is deleted
- Then: inventory, summary, and events requests return not-found for the owning teacher afterward; trace/event/artifact rows and binaries are gone; no orphaned evidence rows remain
- Level: Integration
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: deletion service; MinIO listing assertion
- Result/evidence: NOT RUN

### TS-009: Explanation narration — stream, stop, record, quota, idempotency, failure

- Protects: `AC-009`
- Risk/type: Streaming / Cost discipline
- Given: a settled run with mixed outcomes; workspace quota near limit; a duplicate narration start; a provider failure script
- When: narration is started, streamed, stopped; duplicated; started at exhausted quota; started under provider failure
- Then: tokens stream over SSE with stop available and the complete text recorded as a trace event on the narrated run; narration reserves workspace quota and never any run cap; a duplicate start while active returns the active narration rather than a second stream; exhausted quota returns the quota class naming the workspace boundary while recorded evidence stays readable; provider failure returns the provider class with retry as an owner action and no automatic loop; run state never changes
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: FakeModelAdapter narration; quota counter fixtures
- Result/evidence: NOT RUN

### TS-010: New generation/discovery events persist tokens, model identifier, and estimated cost

- Protects: `AC-002`, `AC-005` (data foundation)
- Risk/type: Observability / Write path
- Given: fresh discovery, planning, and generation runs executed after this Feature (FakeModelAdapter with usage fields)
- When: their trace events are written
- Then: every model/tool event persists prompt tokens, completion tokens, model identifier, and write-time estimated cost; existing prompt/response payloads and latency capture are unchanged; the ORM/migration alignment (freed `run_id`) holds with both discovery and generation run ids
- Level: Integration
- Automation target/path: `apps/backend/tests/test_evidence.py` (+ existing generation suites asserting the new columns)
- Data/fixture/environment: existing run fixtures
- Result/evidence: NOT RUN

### TS-011: Discovery and planning evidence includes interview rounds and specialist/tool events

- Protects: `AC-011`
- Risk/type: Coverage
- Given: a discovery run and a planning run with question rounds, teacher answers, narration, standards tool call, and draft-build events
- When: their evidence is served
- Then: interview rounds (roles, round indices, content) and `model.*`/`tool.*` events appear inside the same layered structure with the same metrics and gap markers as generation runs; no second, weaker structure exists for these kinds
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: existing interview fixtures
- Result/evidence: NOT RUN

### TS-012: Malformed cursor, unknown filter, and page-bound violations are validation errors

- Protects: `AC-003`, Spec Error Cases
- Risk/type: Input validation / Boundary
- Given: requests with a malformed cursor, an unknown event kind, and out-of-bounds limit values
- When: served
- Then: each returns the input-validation class without partial data; the limit clamps to configured bounds when a valid range is exceeded; the list state on the client is unchanged
- Level: API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: —
- Result/evidence: NOT RUN

### TS-013: Legacy trace endpoint is removed with no surviving consumer

- Protects: `AC-014`
- Risk/type: Regression / Contract cleanup
- Given: the repository before F006 (endpoint + `test_trace.py` suite) and after
- When: `GET /projects/{id}/trace` is requested post-F006 and the full backend suite runs
- Then: the endpoint no longer exists (404 route miss), its tests are replaced by the evidence suites, and no frontend or backend code path references it; the workspace remains fully green
- Level: API/Regression
- Automation target/path: `apps/backend/tests/test_evidence.py` (removal assertion) + full-suite rerun
- Data/fixture/environment: —
- Result/evidence: NOT RUN

### TS-014: Additive migration preserves existing traces and runs

- Protects: Spec Data Changes (backward compatibility)
- Risk/type: Migration
- Given: a populated pre-F006 database (all five run kinds, legacy event shapes)
- When: the F006 migration applies
- Then: existing rows are intact with null evidence columns, indexes are created, the freed-`run_id` alignment changes no data, and the application reads pre/post rows without error
- Level: Integration (migration up/down on seeded DB)
- Automation target/path: `apps/backend/tests/test_evidence.py` (migration proof) per the Plan's migration task
- Data/fixture/environment: seeded legacy snapshot
- Result/evidence: NOT RUN

### TS-015: Trace payloads are untrusted data on every serving path

- Protects: `AC-010`
- Risk/type: Injection
- Given: prompts, responses, filenames, and metadata containing injection payloads (fake tool grants, policy text, HTML/script fragments)
- When: inventory, summary, events, and narration responses are served
- Then: payloads ride as inert JSON string values with no interpretation, execution, or policy effect; error responses never embed payload content; storage paths never appear
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_evidence.py`
- Data/fixture/environment: injection-payload fixtures
- Result/evidence: NOT RUN

### TS-016: Evidence view renders every designed state with honest metrics

- Protects: `AC-001`..`AC-005`, `AC-012`, `AC-015` (UI)
- Risk/type: UI state
- Given: fixtures for empty inventory, loaded inventory (five kinds), summaries (settled complete, partial with reasons, superseded naming newer version, discovery draft_ready, provider_failed), legacy-gap events, token/cost-bearing events, multi-page events, and small-screen viewport
- When: the evidence view renders each state and the owner pages, filters, expands a row, and copies a payload
- Then: Layer 1 renders before any expansion with teacher-language status, versions, outcomes, recovery links, usage, and 估算-labeled aggregates; gap rows show 未记录; the technical disclosure is collapsed by default; load-more appends pages with explicit loading and a terminus; expanded rows render inert text with copy; superseded marking names the newer version; below 1024px summary stays readable and expansion/narration defer behind the desktop-required notice; no payload is written to browser storage
- Level: Component (Vitest + Testing Library)
- Automation target/path: `apps/web/__tests__/evidence-panel.test.tsx`
- Data/fixture/environment: mocked API client
- Result/evidence: NOT RUN

### TS-017: Narration interaction — start, stop, failure, quota

- Protects: `AC-009` (UI)
- Risk/type: Interaction / Streaming
- Given: a summary with narration available; a streaming narration; a provider-failed narration; a quota-exhausted start
- When: the owner starts, stops, and retries
- Then: the stream renders incrementally in the shared conversation region with stop; stop ends display only; provider failure shows the named class with retry as an owner action; quota exhaustion names the workspace boundary; the narrate button disables while streaming and re-enables after terminal states
- Level: Component/Interaction
- Automation target/path: `apps/web/__tests__/evidence-panel.test.tsx`
- Data/fixture/environment: mocked SSE
- Result/evidence: NOT RUN

### TS-018: Read-only UI — no state-changing surface, safe navigation

- Protects: `AC-007`, `AC-015` (UI)
- Risk/type: Interaction / Invariant
- Given: the evidence view over mixed-state runs
- When: every interaction is exercised (select, expand, copy, filter, page, narration) and recovery links are followed
- Then: the only non-GET request ever issued is narration start; recovery links navigate to the owning workspace views without mutating anything; the desktop gate defers depth below 1024px
- Level: Component/Interaction
- Automation target/path: `apps/web/__tests__/evidence-panel.test.tsx`
- Data/fixture/environment: request-spy mocks
- Result/evidence: NOT RUN

### TS-019: Workspace-shell extension is behavior-preserving for existing views

- Protects: Eighth-view integration boundary (ux-ui.md D-EVIDTAB)
- Risk/type: Regression
- Given: the workspace shell extended with the `运行证据` view
- When: the existing F003/F004/F005 panel suites and the workspace-panels suite run unchanged
- Then: every pre-existing web test passes without modification; the eighth tab navigates alongside the existing seven; the shared artifact-run surfaces expose no F006-only behavior
- Level: Regression (Component)
- Automation target/path: existing suites unchanged + new eighth-tab assertions in `apps/web/__tests__/workspace-panels.test.tsx`
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-020: E2E evidence journey on the fault-injected stack

- Protects: `AC-001`..`AC-006`, `AC-009`, `AC-010`, `AC-011` end to end
- Risk/type: E2E / Critical path
- Given: the deterministic fault stack (`LESSONCANVAS_MODEL_ADAPTER=fake`) with a scripted project: completed discovery/planning interviews, a complete lesson-plan run, a partial-failure deck run, a superseded exercise-era run state (or scripted equivalent)
- When: the teacher opens `运行证据`, inspects the inventory and one run's summary, expands technical evidence, pages, expands a payload, starts and stops narration
- Then: all five kinds appear; the summary names failures and recovery links that navigate correctly; pages and disclosures work; 未记录/估算 markers show where scripted; narration streams and stops; no teaching state changes
- Level: E2E (Playwright, fault stack)
- Automation target/path: `apps/web/e2e/evidence-journeys.spec.ts`
- Data/fixture/environment: compose services; fake-adapter backend; real or eager Worker per TQ-002
- Result/evidence: NOT RUN

### TS-021: E2E live-stack evidence over a real generated run

- Protects: `AC-001`..`AC-005`, `AC-009` end to end with the real provider
- Risk/type: E2E / Live evidence
- Given: the live stack (real DeepSeek + real Worker) and a completed unit journey (existing generation journey state)
- When: the teacher inspects that run's summary and technical evidence and runs one narration
- Then: token/cost/model fields are populated and labeled 估算 for post-F006 events, payloads render inertly, narration completes with real tokens, and the recorded trace event exists
- Level: E2E (Playwright, `CLERK_E2E=1` gated)
- Automation target/path: `apps/web/e2e/evidence-journeys.spec.ts`
- Data/fixture/environment: compose services; live DeepSeek
- Result/evidence: NOT RUN

### TS-022: B-001 keyboard and screen-reader pass (executed at this UI touch)

- Protects: `AC-013`, STAGE B-001 unblock condition
- Risk/type: Accessibility
- Given: the implemented evidence view and the core workspace flows
- When: the pending manual keyboard pass runs inventory → summary → disclosure → paging → payload expand/copy → narration start/stop, plus core-flow spot checks per B-001's recorded scope
- Then: every action is keyboard reachable with managed focus, disclosures announce state, live regions are throttled and correct, no color-only or motion-dependent meaning exists, and the pass is recorded in this document's Execution Evidence Snapshot (closing B-001)
- Level: Accessibility (manual/scripted pass + automated checks)
- Automation target/path: Playwright a11y checks + recorded pass evidence
- Data/fixture/environment: implemented UI
- Result/evidence: NOT RUN

### TS-023: F003 residual — SSE early-drop root cause investigation (Bug branch)

- Protects: Streaming integrity across the evidence narration surface; F003 recorded residual
- Risk/type: Investigation / Regression
- Given: the recorded F003 symptom (SSE stream drops early; mitigated by 3s snapshot polling + auto-reconnect) and the F006 narration stream sharing the same transport
- When: reproduction is attempted under controlled load/disconnect profiles on the evidence SSE path
- Then: either a root cause is identified and fixed with a regression test, or reproduction attempts, captured evidence, an owner-confirmed mitigation assessment, and residual risk are recorded per the evidence-based surrogate rule; the existing mitigation stays in force either way
- Level: Investigation + Regression
- Automation target/path: findings recorded in `specs/F006-layered-run-evidence/review.md`; any regression test lands beside the SSE suites
- Data/fixture/environment: compose services; scripted disconnect profiles
- Result/evidence: NOT RUN

### TS-024: F004 M-2 residual — StaleDataError run-teardown semantics investigation (Bug branch)

- Protects: Run teardown consistency at supersession; F004 recorded residual (shared with F011)
- Risk/type: Investigation / Consistency
- Given: the recorded F004 M-2 symptom (StaleDataError during run teardown on supersession paths)
- When: supersession journeys are re-run with the evidence view observing the run concurrently
- Then: either the teardown semantics defect is confirmed and fixed with a regression test, or the non-reproduction evidence and residual risk are recorded and the item is explicitly re-routed to F011 with the owner's confirmation
- Level: Investigation + Regression
- Automation target/path: findings recorded in `specs/F006-layered-run-evidence/review.md`; any fix lands with a test in the owning suite
- Data/fixture/environment: fault stack; supersession fixtures
- Result/evidence: NOT RUN

## Scenario Selection Notes

- Load/performance runs: `N/A for F006` — bounded pagination is contract-tested (TS-003); throughput evidence belongs to F009.
- Visual regression suite: `N/A for F006` — state coverage is component-level (TS-016..018); shared-surface preservation is proven by unchanged suites (TS-019).
- Parallel-feature integration: `N/A - no concurrent work items` (A-006 is the sole active item; verified in STAGE Active Work).
- E2E environment risk: the Clerk dev-instance session instability class (F004/F005 M-1) may reappear; the owner-approved substitute-coverage-plus-residual pattern applies if blocking.
- Migration is additive only; no legacy rewrite (TS-014).

## Open Test Questions

| ID | Question | Severity | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Price-table values and page-size defaults/max | Non-critical | Implementation assignee | Chosen in the Implementation Plan and recorded in settings; Spec behavior (estimate labeling, never zero-masking) is testable at any value (TS-005, TS-012) | RESOLVED |
| TQ-002 | E2E model provider and fault-injection strategy | Non-critical | `YMY / Project Owner` | Reuse the F003–F005 dual-instance pattern unchanged: fault stack (`LESSONCANVAS_MODEL_ADAPTER=fake`, eager or real Worker) for TS-020; live stack (real DeepSeek + real Worker) for TS-021; component/integration suites stay fake-based | RESOLVED |
| TQ-003 | SSE early-drop reproduction strategy (TS-023) | Non-critical | Implementation assignee | Attempted reproduction under scripted disconnect profiles; if non-deterministic, the evidence-based surrogate rule applies (attempts + captured evidence + owner-confirmed mitigation + residual risk) — never a claimed false reproduction | RESOLVED |
| TQ-004 | B-001 pass scope at this UI touch | Non-critical | `YMY / Project Owner` | Manual keyboard/screen-reader pass over the evidence view (TS-022 flow) plus core-flow spot checks; recorded in the Execution Evidence Snapshot, closing B-001 | RESOLVED |

No Critical Test Question is `OPEN` or `DEFERRED`.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable and mapped. | YES | Traceability table covers AC-001..AC-015 |
| TR-02 | Happy Path, Alternative Flows, boundaries covered. | YES | TS-001/002 happy; TS-004/005/012/013/014 boundaries; TS-009/TS-020 alternatives incl. superseded and gap states |
| TR-03 | Error, Auth/Security, Regression covered. | YES | TS-006/015 security+injection; TS-012 errors; TS-013/019 regression incl. endpoint removal and shell extension |
| TR-04 | Idempotency, Concurrency, Transaction, Consistency covered. | YES | TS-003 (concurrent-append cursor), TS-007 (state-identity), TS-009 (narration idempotency), TS-024 (teardown consistency) |
| TR-05 | Retry/timeout, migration/compat, performance covered or N/A. | YES | TS-009 provider-failure retry semantics; TS-014 migration; performance N/A with reason (Notes) |
| TR-06 | UI interaction/state, Accessibility, E2E covered per risk. | YES | TS-016/017/018 components; TS-020/021 E2E; TS-022 a11y closing B-001 |
| TR-07 | Levels and automation targets appropriate, not implementation-only. | YES | All scenarios assert observable API/UI/DB/storage outcomes |
| TR-08 | Environment, data, fixtures, dependencies available. | YES | Existing harness reused; fault/live stacks per TQ-002; legacy-shape fixtures constructed in-test |
| TR-09 | Bug reproduction/regression or confirmed surrogate. | YES | Two recorded residual investigations (TS-023/TS-024) follow the Bug branch incl. the surrogate rule (TQ-003) |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open/deferred. | YES | All four TQs resolved, none Critical |
| TR-11 | Concurrent work-item integration slice or justified N/A. | YES | `N/A - no concurrent work items` (A-006 sole active; STAGE verified) |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `b43922d2cc17`, UX/UI `ux-ui-f006-r1` / `4bff46959bb0`, plus their Gate Record manifests (VCS base `main @ 5804e86`), `docs/TESTING.md`, and this artifact `test-design-f006-r1` @ `e2e261591bd8`
- Evidence checklist result: ALL YES (TR-01..TR-11)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `b43922d2cc17`
- Validated UI revision or complete skip-decision link: `ux-ui-f006-r1` / `4bff46959bb0`
- Validated Test Design revision: `test-design-f006-r1` @ `e2e261591bd8`
- Validated at: 2026-08-31
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-31
- Approval scope: F006 Test Design at `test-design-f006-r1`

## Execution Evidence Snapshot (2026-08-31)

All 24 scenarios executed and passed:

| Suite | Evidence |
| --- | --- |
| TS-001..TS-015, TS-023 regression | `apps/backend/tests/test_evidence.py` — 20 tests green within the full backend suite (exit 0, ruff clean; real python-docx renderer + MinIO + PostgreSQL; five-kind inventory, layer-1 summaries incl. superseded naming, cursor stability under concurrent append, legacy-gap honesty, price-table estimates, non-disclosing authorization, read-only invariance, deletion cascade, narration lifecycle with deterministic slow-stream adapter, query validation, legacy endpoint removal, injection inertness, SSE keepalive regression) |
| TS-010 write path | Existing generation/discovery/planning suites re-verified green with `record_trace` usage/model extensions (tokens + model persisted on model events; tools stay null) |
| TS-016..TS-019 | `apps/web/__tests__/evidence-panel.test.tsx` — 8 tests green within the 47-test web suite (empty state + navigation, summary-first with 估算 labeling and gaps, superseded banner, pagination + inert payload disclosure + copy, narration quota mapping, read-only request discipline, small-screen deferral, eighth-tab navigation); all pre-existing suites unchanged and green; eslint/tsc/build clean |
| TS-020a / TS-020 / TS-022 | evidence E2E on the fault stack (fake adapter, eager execution; production `next start` build) — empty state, full journey (inventory → summary → expansion → payload disclosure → narration), and the keyboard-only B-001 pass (Tab/Enter through inventory, row expansion with `aria-expanded`, narration start) all passed |
| TS-021 | evidence E2E on the live stack (real DeepSeek + real Celery Worker solo pool) — 1.4 m: token/cost/model fields populated and labeled on live events, payloads inert, real explanation narration completed |
| TS-023 | Root cause identified and fixed: silent idle gaps during per-lesson model calls let idle-timeout consumers drop the stream (reproduced with a 15 s read-timeout probe against a live run). Fix: SSE comment keepalives (`STREAM_KEEPALIVE_SECONDS = 5.0`) on generation/deck/exercise/narration streams + regression test. Verified end-to-end: identical disconnect probe completes a live 6-lesson run with 0 silent ends, 4 keepalives, clean `end`, 22/22 event frames |
| TS-024 | Reproduced (project deleted at `generating` 4/6 against the live model → `StaleDataError` on the in-flight lesson update, F004 M-2 class); concurrent evidence observers saw only 200-before/404-after with no 5xx; Worker settles via bounded retry; no orphan rows. Hardening routed to F011 (owner to confirm at refinement) |

Execution profile notes (per TQ-002): fault stack ran the fake adapter with eager execution against compose services; live stack ran real DeepSeek + real Celery Worker (solo pool); web served from the production build; journeys executed serially. Environment events recorded in `review.md` M-1 (one Clerk dev-instance stall + quota-orchestration cleanup before the passing TS-020 run) and L-2 (multi-DB/shared-Redis probe hazard, documentation only).

# Test Design: F007 Versioned Targeted Regeneration

## Inputs and Environment

- Spec: `specs/F007-versioned-targeted-regeneration/spec.md` @ `fb351456a2ee` (`SPEC READY` PASS)
- UX/UI: `specs/F007-versioned-targeted-regeneration/ux-ui.md` @ `ux-ui-f007-r1` / `97597ad3c608` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (VCS base `main @ 87ae292`)
- Environment: existing deterministic harness — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter for logic, Clerk token fixtures; live DeepSeek only for separately authorized live evidence
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E + a11y checks)

## Risk Inventory

| Risk | F007 exposure | Coverage |
| --- | --- | --- |
| Over-scoping (silent whole-unit cost) or under-scoping (stale retained work) | Matrix misclassifies a change | TS-001, TS-005, TS-006 |
| Old run publishes over new version | Supersession race at confirm | TS-003, TS-017 |
| Duplicate targeted runs / re-billed retained lessons | Idempotency or scope drift | TS-004, TS-005 |
| Retained artifacts lose provenance or availability | Read-time retention join wrong | TS-005, TS-009 |
| Coverage gate bypass or over-block | Deck/exercise starts under transitions | TS-008 |
| Stale edit overwrites newer version | Conflict handling | TS-002 |
| Scoped resume touches retained lessons | Checkpoint scope leak | TS-007 |
| Workspace-shell extension regression | Ninth view + family-panel changes break F003–F006 surfaces | TS-013 |
| Cross-account disclosure | New endpoints leak transitions | TS-010 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 new version + visible scope | TS-002, TS-003, TS-014 |
| AC-002 safe-checkpoint supersession | TS-003, TS-017 |
| AC-003 retained presentation + downloads, no re-billing | TS-005, TS-014 |
| AC-004 stale conflict | TS-002 |
| AC-005 reasons + uncertainty | TS-001, TS-012 |
| AC-006 lesson-level scoping | TS-001, TS-005 |
| AC-007 unit-level scoping | TS-001 |
| AC-008 structural add/remove | TS-001, TS-006 |
| AC-009 scoped idempotent start | TS-004 |
| AC-010 scoped resume | TS-007 |
| AC-011 coverage prerequisite | TS-008 |
| AC-012 comparison view | TS-009, TS-012, TS-014 |
| AC-013 non-disclosure | TS-010 |
| AC-014 deletion | TS-011 |

## Test Scenarios

### TS-001: Impact matrix classification correctness across all delta classes

- Protects: `AC-005`, `AC-006`, `AC-007`, `AC-008` (preview part)
- Risk/type: Rule / Boundary
- Given: a confirmed pair and draft deltas of each class — brief `output_language_mode`; each brief unit-context field; blueprint unit objectives; one lesson's `activity_outline`; `lesson_count` increase and decrease; an artificial unclassifiable field change; and a no-delta draft
- When: the impact preview is computed
- Then: unit-level deltas return all lessons × all families; the lesson-level delta returns exactly that lesson for plans with decks/exercises marked transitively affected; structural deltas name added/removed lessons with unchanged retained; the unclassifiable delta widens to the larger scope with the uncertainty flag set; the no-delta draft reports no material change; every verdict row names its triggering change
- Level: Unit + Integration/API
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: seeded confirmed pair via existing services; direct draft payloads
- Result/evidence: NOT RUN

### TS-002: Revision seeding, immutability, and stale-conflict

- Protects: `AC-001` (version creation), `AC-004`
- Risk/type: Rule / Conflict
- Given: a confirmed pair; a draft seeded from it; a second client confirming a newer version first
- When: the first client saves/confirm against the stale base_revision
- Then: a version-conflict error names the current versions and nothing is written; the confirmed version fields are byte-identical before and after any draft operations; the seeded draft equals the confirmed fields until edited
- Level: API
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: dual-session fixtures
- Result/evidence: NOT RUN

### TS-003: Confirm superscedes active runs at safe checkpoints without stale publication

- Protects: `AC-002`
- Risk/type: Consistency / Version conflict
- Given: an active generation run for the old pair mid-unit (scripted lesson pacing), and a confirmed new version
- When: the older run passes its next lesson checkpoint
- Then: it settles `superseded`, its completed artifacts remain historical downloads, nothing publishes under the new pair, and starting a targeted run on the new pair is a distinct run identity
- Level: Integration
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: fake adapter with per-lesson pacing; existing supersession fixtures
- Result/evidence: NOT RUN

### TS-004: Targeted run creation scopes, records once, and converges under duplicates

- Protects: `AC-009`
- Risk/type: Idempotency / Concurrency
- Given: a new confirmed pair with a lesson-level delta and a prior complete plan/deck/exercise set for the old pair
- When: the teacher starts family regeneration (twice sequentially, and concurrently from N callers)
- Then: exactly one run per family exists for the pair; its recorded scope equals the matrix-derived affected lessons for that family and never widens on later requests; sequential and concurrent duplicates all receive the same run; artifact rows exist only for scoped lessons
- Level: Integration/Concurrency
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: parallel transactions against PostgreSQL
- Result/evidence: NOT RUN

### TS-005: Retention presents, downloads, and never re-bills unaffected lessons

- Protects: `AC-003`, `AC-006` (retention part)
- Risk/type: Provenance / Cost discipline
- Given: a completed targeted plan/deck/exercise set under the new pair with some lessons retained
- When: snapshots and downloads are served
- Then: retained lessons appear as retained entries with the prior artifact id, source version pair, run id, and working authorized downloads; the prior artifacts' checksums and rows are unchanged; the targeted run's model-call count reflects only scoped lessons (no re-billing of retained work); the F006 evidence view shows both old and new runs
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: transition fixtures with checksum assertions
- Result/evidence: NOT RUN

### TS-006: Structural lesson add/remove across the transition

- Protects: `AC-008`
- Risk/type: Boundary
- Given: a revision that adds and removes lessons while keeping others unchanged
- When: the transition completes with targeted runs
- Then: added lessons are generated by each family's scoped run; removed lessons' artifacts are historical and never appear current; unchanged lessons retain; the comparison marks each verdict
- Level: Integration
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: blueprint with reindexed lessons
- Result/evidence: NOT RUN

### TS-007: Scoped failure and resume never touch retained lessons

- Protects: `AC-010`
- Risk/type: Recovery / Scope leak
- Given: a targeted run where one scoped lesson fails persistently after others complete
- When: the teacher resumes
- Then: the F003–F005 checkpoint resume re-executes only failed/incomplete scoped lessons; retained lessons' artifacts are untouched (checksums unchanged, no model calls); the run settles per the existing taxonomy
- Level: Integration
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: scripted per-lesson failure; call accounting
- Result/evidence: NOT RUN

### TS-008: Coverage prerequisite gates deck/exercise targeted starts

- Protects: `AC-011`
- Risk/type: Rule / Boundary
- Given: a transition where some lessons' plans are retained-complete and others await the new plan run; deck start attempted (a) before the plan run exists, (b) after a partial plan run leaves one scoped lesson failed, (c) after coverage completes via in-run + retained plans
- When: deck/exercise start is requested in each state
- Then: (a) and (b) return the requirement class naming the uncovered lessons and recovery; (c) creates the scoped deck run; retained plan coverage satisfies the gate exactly like in-run coverage
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: staged coverage fixtures
- Result/evidence: NOT RUN

### TS-009: Current-transition comparison payload

- Protects: `AC-012`
- Risk/type: Contract
- Given: a completed transition with affected, retained, and historical lessons
- When: the transition endpoint is read
- Then: it returns from/to versions, the intent diff, per-lesson × family verdicts with reasons, and old/new artifact status with download availability for both; a project without a transition reports the first-version state explicitly
- Level: API/Contract
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: transition fixtures
- Result/evidence: NOT RUN

### TS-010: Authorization non-disclosure on F007 endpoints

- Protects: `AC-013`
- Risk/type: Security / Privacy
- Given: teacher A's project with transitions; teacher B; unauthenticated; foreign run/lesson references
- When: impact, transition, and family starts are requested by each
- Then: B/unauthenticated receive 401/404 without content or existence disclosure; A receives the contract; error bodies carry no internals
- Level: API/Security
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: dual-workspace fixtures
- Result/evidence: NOT RUN

### TS-011: Read-only surfaces and deletion cascade

- Protects: `AC-014`, Spec invariants
- Risk/type: Privacy / Invariant
- Given: a transitioned project with scoped runs and derived retention
- When: impact/transition are read repeatedly and the project (and account) is then deleted
- Then: reads change no business state; after deletion all F007 data (scope column values, runs, artifacts, events, traces, binaries) is gone and endpoints return not-found; no retention residue survives anywhere
- Level: Integration
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: deletion service; storage listing
- Result/evidence: NOT RUN

### TS-012: UI states — revision entry, impact preview, conflict, scoped start, retained rows, comparison

- Protects: `AC-001`..`AC-012` (UI surfaces)
- Risk/type: UI state
- Given: fixtures for revision entry (with/without confirmed pair), preview (unit-level, lesson-level, structural, uncertainty, no-delta), stale-conflict modal, scoped start with N + existing-run states, retained rows with provenance and download, comparison view, uncovered-prerequisite message, small-screen viewport
- When: each surface renders and interactions run (seed, preview, confirm-conflict, scoped start, download retained, browse comparison)
- Then: every state matches ux-ui.md (verdicts with reasons, uncertainty Alert, consequence text in the confirm modal, 沿用 badge + provenance, scoped count on the start button, conflict modal naming current versions, desktop-required notices below 1024px); no state-changing request fires from the comparison view
- Level: Component (Vitest + Testing Library)
- Automation target/path: `apps/web/__tests__/regeneration-panels.test.tsx`
- Data/fixture/environment: mocked API client
- Result/evidence: NOT RUN

### TS-013: Workspace-shell extension is behavior-preserving

- Protects: Ninth-view integration boundary (ux-ui.md D-VERSTAB) and family-panel changes
- Risk/type: Regression
- Given: the shell with the ninth 版本对比 view and transition-aware family panels
- When: all pre-existing web suites run unchanged
- Then: every F001–F006 test passes without modification; the ninth tab navigates alongside the existing eight; the shared artifact-run surfaces expose no F007-only behavior outside the retained variant
- Level: Regression (Component)
- Automation target/path: existing suites unchanged + ninth-tab assertions
- Data/fixture/environment: mocked API
- Result/evidence: NOT RUN

### TS-014: E2E fault-stack journey — revise, preview, confirm, regenerate scoped, compare

- Protects: `AC-001`..`AC-012` end to end
- Risk/type: E2E / Critical path
- Given: the fault stack with a completed unit (plans/decks/exercises) for version pair 1
- When: the teacher revises one lesson's blueprint fields, previews impact, confirms v2, triggers 再生成受影响课程 in each family, and opens 版本对比
- Then: the preview scopes to that lesson across families; older runs supersede safely; targeted runs regenerate only the affected lesson while other lessons show 沿用 with working downloads; the comparison shows old/new with both downloads; no teaching state changes from the comparison view
- Level: E2E (Playwright, fault stack)
- Automation target/path: `apps/web/e2e/regeneration-journeys.spec.ts`
- Data/fixture/environment: compose services; fake-adapter backend
- Result/evidence: NOT RUN

### TS-015: E2E live-stack journey — real revision with live model

- Protects: `AC-001`..`AC-003`, `AC-012` end to end with the real provider
- Risk/type: E2E / Live evidence
- Given: the live stack with a completed unit for pair 1 (existing journey state or seeded live)
- When: the teacher revises one lesson field, confirms, and regenerates that family scoped
- Then: the targeted run completes for the affected lesson only against real DeepSeek; retained lessons stay untouched; comparison and downloads work; F006 evidence shows the scoped run's token/cost footprint limited to scope
- Level: E2E (Playwright, `CLERK_E2E=1` gated)
- Automation target/path: `apps/web/e2e/regeneration-journeys.spec.ts`
- Data/fixture/environment: compose services; live DeepSeek + real Worker
- Result/evidence: NOT RUN

### TS-016: Keyboard and screen-reader pass over the revision path

- Protects: Accessibility requirement (WCAG 2.2 AA core flow)
- Risk/type: Accessibility
- Given: the implemented revision → preview → confirm → scoped-start → comparison path
- When: a scripted keyboard pass runs plus automated a11y checks
- Then: all actions keyboard reachable; confirm/conflict modals trap and return focus; verdict tables carry headers and text semantics; no color-only verdicts; announcements polite and correct
- Level: Accessibility (scripted pass + automated checks)
- Automation target/path: Playwright a11y checks + recorded evidence
- Data/fixture/environment: implemented UI (fault stack)
- Result/evidence: NOT RUN

### TS-017: Concurrent confirm vs targeted start consistency

- Protects: `AC-002`, `AC-009` under races
- Risk/type: Concurrency / Transaction
- Given: an active old-pair run, a pending confirmation, and simultaneous targeted-start attempts racing the version switch
- When: confirm and starts interleave
- Then: starts binding the new pair all carry identical scope; any start racing ahead of the confirm either waits on the confirmed pair or fails with the requirement class (never a run bound to a half-switched pair); the old run never publishes over the new pair; exactly one run per family per pair results
- Level: Concurrency/Integration
- Automation target/path: `apps/backend/tests/test_regeneration.py`
- Data/fixture/environment: parallel transactions with controlled interleaving
- Result/evidence: NOT RUN

## Scenario Selection Notes

- Load/performance: `N/A for F007` — impact computation is bounded by lesson count; cost evidence via scoped model-call accounting (TS-005).
- Visual regression: `N/A` — component state coverage (TS-012) plus shared-surface regression (TS-013).
- Parallel-feature integration: `N/A - no concurrent work items` (A-007 sole active; STAGE verified).
- Bug branch: `N/A - new Feature`; the F004 M-2 fast-fail hardening stays routed to F011 (F007 review will re-confirm non-expansion).
- E2E environment risk: known Clerk dev-instance class may reappear; owner-approved substitute-coverage-plus-residual pattern applies.

## Open Test Questions

| ID | Question | Severity | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Scope-column representation (JSON array vs child table) | Non-critical | Implementation assignee | Chosen in the Implementation Plan; Spec behavior (scope fixed at creation, never widens) is testable at either representation (TS-004) | RESOLVED |
| TQ-002 | E2E profiles | Non-critical | `YMY / Project Owner` | Reuse the dual-instance pattern: fault stack (fake adapter) for TS-014/016; live stack (real DeepSeek + real Worker) for TS-015 | RESOLVED |
| TQ-003 | Deterministic impact fixtures | Non-critical | Implementation assignee | Draft payloads constructed directly per matrix class incl. an artificial unclassifiable field via a reserved test-only path or direct service call (no production escape hatch) | RESOLVED |

No Critical Test Question is `OPEN` or `DEFERRED`.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable and mapped | YES | Traceability covers AC-001..AC-014 |
| TR-02 | Happy Path, Alternative Flows, boundaries covered | YES | TS-001/003/004/005/006/008 boundaries; TS-002/007/017 alternatives |
| TR-03 | Error, Auth/Security, Regression covered | YES | TS-002/008/010 errors+security; TS-013 regression |
| TR-04 | Idempotency, Concurrency, Transaction, Consistency covered | YES | TS-003/004/011/017 |
| TR-05 | Retry/timeout, migration/compat, performance covered or N/A | YES | TS-007 recovery; migration additive (Plan); performance N/A with reason |
| TR-06 | UI interaction/state, Accessibility, E2E covered per risk | YES | TS-012 components; TS-014/015 E2E; TS-016 a11y |
| TR-07 | Levels and automation targets appropriate, not implementation-only | YES | All scenarios assert observable API/UI/DB/storage outcomes |
| TR-08 | Environment, data, fixtures, dependencies available | YES | Existing harness; matrix fixtures per TQ-003 |
| TR-09 | Bug reproduction/regression or confirmed surrogate | YES | `N/A - new Feature, no Bug`; routed F011 hardening excluded by scope |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open | YES | All three TQs resolved, none Critical |
| TR-11 | Concurrent work-item integration slice or justified N/A | YES | `N/A - no concurrent work items` |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `fb351456a2ee`, UX/UI `ux-ui-f007-r1` / `97597ad3c608`, their Gate Record manifests (VCS base `main @ 87ae292`), `docs/TESTING.md`, and this artifact `test-design-f007-r1` @ `69c9d0532f7a`
- Evidence checklist result: ALL YES (TR-01..TR-11)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `fb351456a2ee`
- Validated UI revision: `ux-ui-f007-r1` / `97597ad3c608`
- Validated Test Design revision: `test-design-f007-r1` @ `69c9d0532f7a`
- Validated at: 2026-08-31
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-31
- Approval scope: F007 Test Design at `test-design-f007-r1`

## Execution Evidence Snapshot (2026-08-31)

All 17 scenarios executed and passed:

| Suite | Evidence |
| --- | --- |
| TS-001..TS-011, TS-017 | `apps/backend/tests/test_regeneration.py` — 11 tests green within the full backend suite (exit 0) + ruff clean; matrix classes incl. uncertainty widening and citations-as-non-intent; preview API with draft-newer-than-version rule; scoped start with scope-once idempotency, concurrent convergence, and retention checksums; structural add/remove through the full brief-revision + re-planning path; coverage gate naming uncovered lessons; scoped resume with scoped-only call accounting; transition payload incl. first-version state; authorization; read-only + deletion; confirm-vs-start races |
| TS-012/TS-013 | `apps/web/__tests__/regeneration-panels.test.tsx` — 4 tests green within the 51-test web suite (compare panel states incl. embedded impact and read-only discipline; retained rows with provenance + downloads; ninth-tab navigation); all pre-existing suites unchanged; eslint/tsc/build clean |
| TS-014 | fault-stack journey: revise lesson 2 → embedded transition impact → confirm v2 → scoped plan regeneration with 沿用 provenance rows → comparison verdicts — passed (21.7s) |
| TS-016 | keyboard-only pass: tab focus + Enter navigation to 版本对比, embedded scope reading, keyboard scoped start with retained list — passed (23.2s) |
| TS-015 | live stack (real DeepSeek + real Worker): full unit → lesson-level revision → scoped regeneration completes for the affected lesson only, retained untouched — passed (1.3m) |

Execution profile notes (per TQ-002): fault stack ran the fake adapter with eager execution; live stack ran real DeepSeek + real Celery Worker (solo pool); web served from the production build; journeys serial. Delivery-found fixes recorded in `review.md` (M-1 coverage retention rule, M-2 embedded transition impact, M-3 pair-aware current-run rule — all fixed with tests before delivery).

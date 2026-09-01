# Test Design: F010 Teacher Product Validation

## Inputs and Environment

- Spec: `specs/F010-teacher-product-validation/spec.md` @ `66a3c94329a9` (`SPEC READY` PASS)
- UX/UI: `specs/F010-teacher-product-validation/ux-ui.md` @ `ux-ui-f010-r1` (`UI READY` PASS; hash in `STAGE.md` Gate Snapshot)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (VCS base `main @ 352db99`)
- Environment: deterministic stack for every automated scenario — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter-generated fixture packages, no live-model dependency anywhere (Spec: zero model calls in the whole Feature). The external-teacher real-review protocol (TS-014) is a delivery-time, owner-authorized evidence protocol recorded separately, never a CI case.
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction/a11y), Playwright (E2E)

## Risk Inventory

| Risk | F010 exposure | Coverage |
| --- | --- | --- |
| False pass (invalid evidence accepted, threshold mis-computed, aggregate masking a failure) | Product-validation honesty | TS-001, TS-002, TS-003, TS-011 |
| Result transfers to a changed package (stale result presented as current) | Version-binding violation | TS-006, TS-007 |
| Technical status and product status merge or mask each other | Separate-display violation | TS-007, TS-012 |
| Duplicate import recomputes or forks outcomes | Idempotency violation | TS-005 |
| Evaluator identity or original documents leak to public/read surfaces | Privacy-boundary violation | TS-009, TS-010 |
| Cross-workspace disclosure of assignments/evidence | Authorization violation | TS-008 |
| Imported untrusted content (filenames, notes, document) injects or breaks rendering | Untrusted-input violation | TS-010 |
| Existing F008/F009 surfaces regress from the status-field change | Shared-contract regression | TS-007, TS-015 |
| Real-review evidence unavailable or fabricated | Delivery-evidence honesty | TS-014 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 rubric schema governance | TS-001, TS-011 |
| AC-002 assignment binding + idempotency + gap rejection | TS-004 |
| AC-003 deterministic computation + thresholds | TS-002, TS-003 |
| AC-004 failed/not-complete explicitness + usability-claim block | TS-003, TS-007, TS-012 |
| AC-005 separate live display on all three surfaces | TS-007, TS-012 |
| AC-006 staleness after material change | TS-006 |
| AC-007 import idempotency + revision supersession + immutability | TS-005 |
| AC-008 privacy/publication boundary + deletion cascade | TS-008, TS-009 |
| AC-009 non-disclosure | TS-008 |
| AC-010 real-review delivery evidence | TS-014 |

## Test Scenarios

### TS-001: Rubric schema governance — fixed revision, full-violation listing, nothing persisted

- Protects: `AC-001`
- Risk/type: Validation / Integrity
- Given: the shipped rubric definition (`rubric-r1`: five dimensions 1–5 with notes, four severe classes with lesson+evidence, structural-rework rule, attestation fields); adversarial evidence payloads each violating different fields (out-of-range score, missing note, severe finding without lesson/evidence, rework true without reason, missing attestation)
- When: each payload is imported through the evidence endpoint
- Then: every violating field is listed in one requirement error; nothing persists; the assignment remains `pending_evidence`; a fully valid payload imports cleanly against the same schema
- Level: Unit + API
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-002: Outcome computation — thresholds, determinism, zero model calls

- Protects: `AC-003`, `AC-004` (unit thresholds)
- Risk/type: Rule / Honesty
- Given: valid evidence fixtures covering: all thresholds met; one severe finding; core mean 3.9; structural rework required; and combinations
- When: outcomes are computed twice from identical evidence
- Then: pass requires zero severe findings AND mean >= 4.0 AND rework false; each violated threshold alone yields `failed` with the violated rule named; identical evidence yields identical outcomes; computation issues no model-adapter calls (adapter spy at zero)
- Level: Unit
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-003: Overall status derivation — full vocabulary and precedence

- Protects: `AC-004`, Spec D6
- Risk/type: Rule / Honesty
- Given: project fixtures covering: no assignments; assignments with pending evidence; one unit failed while another pending; one unit `not_complete`; all units passed
- When: the overall product-validation status is derived
- Then: statuses are `not_evaluated`, `in_progress`, `failed` (definitive, with the failing unit named and pending units still shown), `not_complete`, `passed` respectively; no derivation path yields `passed` while any unit lacks complete evidence
- Level: Unit
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-004: Assignment creation — package binding, idempotency, gap rejection

- Protects: `AC-002`, Spec D8
- Risk/type: Idempotency / Concurrency / Integrity
- Given: an owner workspace with a fixture-generated complete package (fake-adapter generation producing all three families) and a second package with a missing family member
- When: assignments are created — twice sequentially and twice concurrently on the complete package, and once on the incomplete package
- Then: duplicates converge on one assignment bound to dataset revision, confirmed brief/blueprint versions, and per-lesson artifact ids + checksums; concurrent creates produce exactly one row; the incomplete package is rejected with a requirement error naming the missing family/lessons; the assignment payload never embeds mutable content, only identity references
- Level: Integration/API/Concurrency
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-005: Evidence import idempotency, rubric-revision supersession, terminal immutability

- Protects: `AC-007`
- Risk/type: Idempotency / Integrity
- Given: an assignment and two rubric evidence revisions (original r1 with an error, corrected r2)
- When: r1 is imported twice, then r2 imports on the same assignment
- Then: the duplicate r1 import returns the existing record without recompute or a second row; r2 supersedes r1 on the same assignment, the outcome recomputes only from r2; r1's evidence and its outcome remain readable with an explicit superseded marker; no terminal evidence or outcome row is ever mutated
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-006: Staleness — superseded package never transfers its result

- Protects: `AC-006`, Spec D5
- Risk/type: Version binding / Honesty
- Given: a concluded assignment (imported evidence, passed outcome) whose bound package is then superseded — first by targeted regeneration replacing an artifact, then (fresh fixture) by a newer confirmed pair
- When: the project's product-validation state is read after each supersession
- Then: the assignment settles stale with a pointer to what superseded it; the historical result stays readable with the stale marker; the overall status reflects `not_complete` until a new assignment concludes on the new package identity; the new package starts `not_evaluated`; no outcome value transfers
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-007: Live status on shared surfaces — separate, never merged, never masked

- Protects: `AC-005`, `AC-004` (usability-claim block), Spec D7
- Risk/type: Contract / Honesty
- Given: a project with technical package validated AND product validation failed (fixture: one unit with a severe finding); and the full vocabulary variants
- When: `GET /projects/{id}/alignment`, `GET .../technical-evaluation/report`, and the delivery report snapshot are read
- Then: every surface returns the live computed `product_validation_status` (field name unchanged, value no longer constant); technical status remains independently visible; no surface merges the two or derives one from the other; the technical-evaluation report keeps the independence sentence without the "until F010" clause
- Level: API/Contract
- Automation target/path: `apps/backend/tests/test_product_validation.py` (+ alignment/report assertions)
- Result/evidence: NOT RUN

### TS-008: Authorization and deletion — non-disclosure and cascade

- Protects: `AC-009`, `AC-008` (deletion part)
- Risk/type: Security / Privacy
- Given: two owner workspaces, one with assignments and imported evidence including stored original documents; an unauthenticated caller
- When: the second owner and the unauthenticated caller call every F010 endpoint with the first workspace's ids, then the first workspace's project is deleted
- Then: every cross-access returns authorization-denied without content or existence disclosure; after deletion, no assignment, evidence, outcome, or stored evidence document remains (database + object storage sweep)
- Level: API/Integration
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-009: Publication boundary — pseudonymous evidence only

- Protects: `AC-008`
- Risk/type: Privacy
- Given: imported evidence carrying the evaluator attestation and a stored original document
- When: every owner-authorized read surface (overview, detail, alignment, technical-evaluation report, delivery report) is serialized
- Then: only the pseudonymous evaluator reference, completed date, scores, severe-finding classes, and rubric revision appear; the original document is accessible only through its owner-authorized download path; no surface exposes identity/contact fields (none are recorded in publishable form)
- Level: API
- Automation target/path: `apps/backend/tests/test_product_validation.py`
- Result/evidence: NOT RUN

### TS-010: Untrusted input — imported evidence and filenames never inject or break rendering

- Protects: `AC-001` (security part), `AC-008`, AGENTS untrusted-input rule
- Risk/type: Injection / Robustness
- Given: evidence payloads whose notes/finding text carry HTML/script/markup payloads and whose original-document filenames carry path/markup payloads
- When: imported, stored, and rendered through the detail surface and the web component
- Then: content is stored and displayed as inert text (escaped at render); filenames never influence paths or markup; no evaluation or UI behavior changes from payload content
- Level: API + Component
- Automation target/path: `apps/backend/tests/test_product_validation.py`, `apps/web/components/__tests__/product-validation-region.test.tsx`
- Result/evidence: NOT RUN

### TS-011: Region UI — state matrix, import-form validation, duplicate notices

- Protects: `AC-001`, `AC-002`, `AC-003`, `AC-004`, `AC-006`, `AC-007` (UI halves)
- Risk/type: UI interaction / honesty
- Given: the 产品验证 region rendered with overview fixtures for each state (not evaluated, in progress, pending, passed, failed, not complete, stale) and an import flow with server-returned multi-field requirement errors plus a duplicate-revision notice
- When: the user opens the region, expands detail, submits invalid then valid evidence, and re-submits the same revision
- Then: every state renders its exact vocabulary text+marker; validation errors list every violating field inline with focus management; the duplicate shows 「该量表版本已导入」 without a second row; stale rows disable import with supersession guidance; empty state offers 创建评审分派 on desktop only
- Level: Component/Interaction
- Automation target/path: `apps/web/components/__tests__/product-validation-region.test.tsx`
- Result/evidence: NOT RUN

### TS-012: Status chips and reports UI — live vocabulary, separation, accessibility

- Protects: `AC-005`, `AC-004` (UI halves)
- Risk/type: UI honesty / Accessibility
- Given: the 对齐与交付 status pair, technical-evaluation report view, and delivery print-report view with the live status field across vocabulary variants (including technical validated + product failed)
- When: rendered and operated by keyboard (region entry → import form → detail → status pair), with status text asserted
- Then: the product chip renders the live vocabulary adjacent to but separate from the technical chip; both remain visible in the mixed case; report lines keep independence wording; statuses are text+marker (never color-alone); keyboard path completes with visible focus and polite announcements on outcome settle
- Level: Component/Interaction/Accessibility
- Automation target/path: `apps/web/components/__tests__/alignment-panel.test.tsx` (extended), report-view tests
- Result/evidence: NOT RUN

### TS-013: E2E owner journey — assignment to honest status (deterministic stack)

- Protects: `AC-002`, `AC-003`, `AC-005` end to end
- Risk/type: E2E
- Given: the deterministic stack with a fake-adapter-generated complete package in an evaluation project
- When: the owner creates an assignment, downloads the review materials (export + printable report + rubric sheet), imports valid evidence with a severe finding, and reads the 对齐与交付 and report surfaces
- Then: the journey completes with the unit shown 失败, the severe finding visible in detail, technical status independently visible, and the overall status honest at every step (待证据 → 失败)
- Level: E2E (Playwright, deterministic stack)
- Automation target/path: `apps/web/e2e/product-validation-journeys.spec.ts`
- Result/evidence: NOT RUN

### TS-014: Real-review delivery evidence protocol (external teacher)

- Protects: `AC-010`
- Risk/type: Delivery evidence / External dependency
- Given: three complete live packages for the dataset units (existing F009 live-pass projects, or fresh live passes re-authorized if the packages no longer exist); the participating external senior-high English teacher; the fixed `rubric-r1` sheet
- When: the teacher completes rubric reviews for the units and the owner imports the structured evidence with the retained original documents
- Then: the delivery evidence records per-unit outcomes, retained originals, the overall status, and the capture-channel label; any unavailable unit records honest `not_complete` with a reason rather than a substituted judgment
- Level: Delivery-time evidence protocol (owner-authorized; not a CI case)
- Automation target/path: recorded in the execution evidence snapshot below (import replayed as fixtures in TS-002 class coverage)
- Result/evidence: NOT RUN

### TS-015: Regression — shared surfaces keep F008/F009 behavior

- Protects: `AC-005` (compatibility), shared contracts
- Risk/type: Regression
- Given: the full backend and web suites including F008 alignment/export tests and F009 evaluation/report tests
- When: F010 changes land (status constant → computed value; new region)
- Then: all existing tests pass unchanged except asserted contract extensions (status value vocabulary); the evidence panel with both regions renders without layout regressions
- Level: Regression (full suites)
- Automation target/path: `uv run pytest`, `corepack pnpm web:test`, existing E2E alignment/evaluation journeys
- Result/evidence: NOT RUN

## Parallel-feature integration/merge regression

`N/A - no concurrent work items` (F011/F012/F013 remain `DRAFT` and unclaimed; single active member A-010).

## Bug Branch

`N/A - greenfield Feature; no pre-existing defect to reproduce.` Any defect discovered during implementation follows the Spec's Bug branch (reproduction -> regression scenario -> fix -> verification).

## Test Questions

| ID | Question | Severity | Status | Resolution |
| --- | --- | --- | --- | --- |
| TQ-001 | Where do fixture complete packages come from in automated scenarios? | Non-critical | RESOLVED | Fake-adapter generation through the existing services (same path F009 deterministic scenarios use); no live dependency |
| TQ-002 | Can the real-teacher protocol block automated gates? | Non-critical | RESOLVED | No — TS-014 is delivery-time evidence; all automated scenarios are deterministic; an unavailable teacher records honest `not_complete` (Spec D9) |
| TQ-003 | Rubric hand-out sheet generation — tested where? | Non-critical | RESOLVED | Printable sheet renders from assignment detail (UIQ-002); asserted in TS-011 component coverage and TS-013 E2E download |

No Critical Test Question is `OPEN` or `DEFERRED`.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable and mapped | YES | AC-001..AC-010 all mapped (traceability table) |
| TR-02 | Happy Path, Alternative Flows, boundaries covered | YES | TS-002 threshold boundaries, TS-006/TS-014 alternative flows, TS-013 happy journey |
| TR-03 | Error, Auth/Security, Regression covered | YES | TS-001 validation, TS-008/TS-009/TS-010 security/privacy, TS-015 regression |
| TR-04 | Idempotency/Concurrency/Transaction/Consistency covered | YES | TS-004 (concurrent create), TS-005 (idempotent import), single-transaction import per Spec |
| TR-05 | Retry/Timeout/Migration/Compatibility/Performance covered or N/A | YES | `N/A - synchronous zero-model reads/imports bounded by rubric size; no new migration of existing data (new tables only); compatibility asserted in TS-007/TS-015` |
| TR-06 | UI interaction/state, Accessibility, E2E covered | YES | TS-011, TS-012 (incl. a11y keyboard), TS-013 |
| TR-07 | Levels and automation targets appropriate, behavior-focused | YES | External contracts and rendered outcomes, not private structure |
| TR-08 | Environment/data/fixtures/dependencies available or alternative confirmed | YES | Deterministic fixtures via fake adapter; TS-014 external protocol with honest fallback confirmed by Spec D9 |
| TR-09 | Bug reproduction/surrogate requirement | YES | `N/A - greenfield; no existing defect` |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open | YES | All requirements have deterministic or protocol evidence; TQ-001..003 resolved |
| TR-11 | Concurrent-work-item integration slice | YES | `N/A - no concurrent work items` |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec @ `66a3c94329a9` (SPEC READY PASS) + `ux-ui-f010-r1` (UI READY PASS, hash in `STAGE.md`) + `docs/TESTING.md` @ `d2288beae040` + this artifact (hash below)
- Evidence checklist result: ALL YES (TR-01..TR-11)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Test Design revision: `test-design-f010-r1` @ (hash recorded in `STAGE.md` Gate Snapshot)
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01 (Spec D1–D9 approval covers thresholds, units, capture flow, and delivery protocol; scenario structure composes TESTING.md risk coverage)
- Approval scope: F010 Test Design at `test-design-f010-r1`

## Execution Evidence Snapshot

Deterministic stack results (2026-09-01, branch `feature/F010-teacher-product-validation`, fake adapter, eager tasks):

- TS-001 PASS — schema governance, full-violation listing, nothing persisted: `uv run pytest tests/test_product_validation.py -k "RubricSchema or requirement_errors"` (backend suite 48 F010 tests green; every-violation and per-field cases included).
- TS-002 PASS — thresholds, determinism, zero model calls: `TestRubricSchema` + `TestOutcomeComputation` (pure halves) and service halves inside `TestEvidenceImport`; adapter untouched by design (no adapter import in the module).
- TS-003 PASS — overall-status vocabulary and precedence: `TestOverallAndStaleness` (not_evaluated / in_progress / failed-definitive-with-pending / passed-requires-every-unit / not_complete).
- TS-004 PASS — assignment binding, sequential + concurrent idempotency, gap rejection: `TestAssignmentCreation` incl. 4-thread concurrent-create convergence and named slide_deck gaps.
- TS-005 PASS — import idempotency, submission-revision supersession, terminal immutability: `TestEvidenceImport::test_duplicate_revision_idempotent` and `test_corrected_revision_supersedes_and_prior_stays_immutable`.
- TS-006 PASS — staleness never transfers: `TestOverallAndStaleness::test_stale_after_newer_confirmed_pair_and_result_never_transfers` (newer-pair trigger) and `test_stale_after_package_artifact_change` (artifact-drift trigger); import blocked on stale.
- TS-007 PASS — live separate status on alignment/report/tech-eval report: `TestAPI::test_shared_surfaces_show_live_separate_status` (technical validated + product failed both explicit; note drops "until F010").
- TS-008 PASS — authorization/non-disclosure + cascade: `TestAPI::test_cross_workspace_and_unauthenticated_no_disclosure` (all endpoints 404/401 without disclosure) and `TestModelCascade` (rows swept via the real `delete_project_cascade`; document objects follow the artifacts-bucket path covered by `test_deletion.py`).
- TS-009 PASS — publication boundary: `TestAPI::test_publication_boundary_pseudonymous_only` (attestation fields exactly {evaluator_reference, completed_date}; report surfaces never expose the evaluator).
- TS-010 PASS — untrusted input inert: `TestAPI::test_untrusted_content_stored_verbatim_as_data` (script/path payloads stored and returned as data) + component rendering via React text nodes.
- TS-011 PASS — region UI: `__tests__/product-validation.test.tsx` (empty/pending/failed/stale vocabulary, create modal + duplicate notice + named gap, import form all-violation display, duplicate-revision notice, stale import disabled with guidance, not-complete conclusion with reason).
- TS-012 PASS — status pair + reports live with separation: `alignment-panel.test.tsx` (existing) and `product-validation.test.tsx` 状态对 describe (technical pass + product failure both visible; tech-eval report live value with independence sentence); keyboard/a11y semantics in component roles/labels/announcements.
- TS-013 NOT RUN (environment-gated) — E2E journey `e2e/product-validation-journeys.spec.ts` written and gated by `E2E_EVAL_FAULT=1` with the fake-adapter backend and Clerk E2E credentials, which are not present in this environment (same class as F009 TS-016). Substitute coverage green: backend TS-001..TS-009 + component TS-011/TS-012. Resume condition: re-run under the fault stack with owner-provided E2E credentials and append evidence here.
- TS-014 NOT RUN (delivery-time protocol) — executes with the participating teacher before delivery (Spec D9); see below.
- TS-015 PASS — regression: backend full suite green incl. F008 alignment/F009 evaluation suites (one asserted contract extension updated: `test_product_status_cannot_leave_not_evaluated` now asserts the live derived value, which is `not_evaluated` with no assignments); web 73/73 + eslint (0 errors; 7 pre-existing warnings unchanged) + tsc + build clean.

Command evidence: `uv run pytest` (full), `uv run ruff check src tests migrations`, `corepack pnpm web:test`, `web:lint`, `web:typecheck`, `web:build` — all green 2026-09-01.

- TS-014 DEFERRED (owner decision 2026-09-01: real teacher review postponed; delivery proceeds per Spec D9's honest fallback) — the not_complete capability is verified (backend `conclude_not_complete` + derivation + UI; TS-003/TS-011), runtime surfaces truthfully show 未评估 while no review assignments exist, and the pass-path evidence waits for the follow-up import. Follow-up: owner coordinates the teacher's reviews of the three units, creates assignments, imports evidence with retained originals, and appends the per-unit outcomes here (fresh authorized live passes if the F009 live-pass packages no longer exist).

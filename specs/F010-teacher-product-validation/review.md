# Review, PR, and DONE: F010 Teacher Product Validation

## Review Context

- Issue/work item: [GitHub Issue #20](https://github.com/MaoyuanYang/LessonCanvas/issues/20) (authorized, bound 2026-09-01)
- Stage activity / snapshot revision: A-010 `CODING_TESTING` -> `REVIEW`; STAGE-63 at review start (STAGE-64 records REVIEW)
- Spec / Gate / revision: `specs/F010-teacher-product-validation/spec.md` `SPEC READY: PASS` @ `66a3c94329a9` (decision log D1–D9, approved 2026-09-01)
- UX/UI / Gate / revision: `ux-ui.md` `UI READY: PASS` @ `ux-ui-f010-r1` / `35fe2b9b1417`
- Test Design / Gate / revision: `test-design.md` `TEST DESIGN READY: PASS` @ `test-design-f010-r1` / `eaa31cd897d6`
- Implementation Plan: `plan.md` @ `76fced0843e7` (T0–T6)
- Diff/revision reviewed: working tree on `feature/F010-teacher-product-validation` (base `main @ 352db99`)
- Decision Authority (named human + role): `YMY / Project Owner`

## Review Checklist

- [x] Scope matches the Spec; no requirements silently added or removed. (The API enumeration was completed truthfully during Documentation Sync — see Finding L-3.)
- [x] Every `AC-*` satisfied and `AC-* -> TS-* -> evidence` traceable (Acceptance Traceability below; TS-013/TS-014 evidence status explicit).
- [x] Architecture, API, database, and module boundaries comply (new `product_validation` module under Alignment-and-Evaluation ownership; zero model calls; no new infrastructure, cache, queue, or identity surface; lazy imports keep the module graph acyclic).
- [x] Reuse appropriate, no unnecessary duplication (region composes the F009 region pattern; status chips reuse the F008 pair; label maps follow the `lib/api.ts` convention; deletion composes `delete_project_cascade`).
- [x] Transaction, concurrency, idempotency, consistency correct (flush-before-store ordering, DB-enforced idempotent identity tuples, concurrent-create convergence tested, terminal immutability).
- [x] Authentication, permission, privacy, validation, error handling correct (ownership on every endpoint; cross-workspace non-disclosure tested; pseudonymous attestation only; untrusted filename/content inert; publication boundary asserted).
- [x] Migration, compatibility, rollout, rollback assessed (migration `f010b7c9d1e3` additive-only with downgrade; shared-surface field name unchanged, value vocabulary extended; one F008 assertion updated to the extended contract).
- [x] Tests verify behavior (external contracts, journeys, and rendered outcomes; no private-structure tests).
- [x] UI flow, states, error mapping, responsive, a11y, Design System correct per the approved artifact (client-side pre-validation added during review — Finding SF-1).
- [x] Code, Spec, Docs, Issue have no material drift (API/DATABASE/TESTING synced; spec API enumeration completed; ROADMAP/STAGE/Issue updated per authorization).

## Findings

| Severity | Location | Finding/risk | Resolution/owner | Status |
| --- | --- | --- | --- | --- |
| Medium (SF-1) | `product-validation-region.tsx` ImportForm | The import form lacked the client-side pre-validation the approved ux-ui Forms table specifies (server-side-only validation worked but deviated from the approved artifact) | Added `clientViolations()` mirroring the fixed schema (scores/notes/findings/rework/attestation) shown in the same all-violations display; server remains the schema authority; client-blocking test added (`client-side pre-validation blocks empty notes without calling the server`) | RESOLVED 2026-09-01 |
| High (SF-2) | `product_validation/service.py` import_evidence | Evidence-document object was stored before the identity collision was resolved; on the exceptional re-raise path a private object could be orphaned and would survive project deletion (deletion sweeps only row-referenced keys) — a privacy-boundary violation class | Reordered to flush-first (identity collisions surface before any private object is written), added explicit rollback on document-boundary rejection, and best-effort object deletion on commit failure; regression assertions added (`test_document_boundary_enforced` now asserts zero rows after each rejection) | RESOLVED 2026-09-01 |
| Medium (M-1) | `e2e/product-validation-journeys.spec.ts` | TS-013 browser journey environment-gated: `E2E_EVAL_FAULT=1` fault stack plus Clerk E2E teacher credentials are not present in this environment (same class as F009 TS-016) | Substitute coverage green (backend TS-001..TS-009; component TS-011/TS-012). Resume condition recorded in the Test Design execution snapshot: re-run under the fault stack with owner-provided credentials and append evidence | OPEN — owner-visible residual with resume condition |
| Medium (M-2) | delivery protocol | TS-014 real-teacher review protocol executes before delivery (Spec D9): requires the participating teacher to complete rubric reviews for the three units and the owner to import evidence with retained originals | Owner decision 2026-09-01: real review postponed; delivery proceeds per the D9 honest-fallback branch (capability verified; runtime truthfully 未评估 until assignments exist; follow-up import appends evidence to the Test Design snapshot) | RESOLVED by owner decision — residual follow-up recorded |
| Low (L-1) | alignment/technical-evaluation reads | The shared surfaces now derive overall status on every read; derivation recomputes package snapshots per latest assignment (bounded: ≤ dataset units × lessons) | Accepted: bounded by construction (3 units); no unbounded growth path (assignment identity includes package digest) | ACCEPTED |
| Low (L-2) | `_overview_row` API helper | Assignment-create/conclusion responses rebuild the overview to reuse one serialization path (N small queries, bounded) | Accepted for consistency; no correctness impact | ACCEPTED |
| Low (L-3) | spec API Behavior | The approved Spec enumerated four endpoints; implementation also exposes the conclusion and original-document-download endpoints, both specified as behavior in the approved Alternative Flows and D4 (download path additionally fixed by the approved Test Design TS-009 and ux-ui contract) | Documentation-fidelity completion during Documentation Sync, not a semantic requirement change; recorded here for Decision Authority visibility with the review approval | RESOLVED by record |

No Critical findings. Peer Review Record: `N/A - no PR review occurred` (PR not yet created at self-review time; external findings, if any, import here per the fix-slice rules).

## Verification Results

| Command/check | Scope | Result | Evidence/notes |
| --- | --- | --- | --- |
| `uv run ruff check src tests migrations` | backend lint | PASS | All checks passed (2026-09-01) |
| `uv run pytest` (full) | backend deterministic suites | PASS | 269 passed (48 F010) — final full rerun after SF-1/SF-2 fixes, 2026-09-01 |
| `corepack pnpm web:test` | web component/interaction | PASS | 74/74 (74 after review additions; 63 pre-F010 baseline all green) |
| `corepack pnpm web:lint` | web lint | PASS | 0 errors; 7 pre-existing warnings unchanged |
| `corepack pnpm web:typecheck` | web types | PASS | tsc clean |
| `corepack pnpm web:build` | production build | PASS | Compiled successfully, 6/6 static pages |
| `uv run alembic upgrade head` | migration | PASS | Applied via test DB (recreated fresh this session); additive-only `f010b7c9d1e3` |
| Playwright TS-013 | E2E journey | NOT RUN (environment-gated) | Spec written and gated; substitute coverage green; resume condition in Test Design snapshot |
| TS-014 teacher protocol | delivery evidence | NOT RUN (delivery-time) | Executes with owner coordination before delivery (Spec D9) |

### Acceptance Traceability

| AC | TS | Automated/manual evidence | Result |
| --- | --- | --- | --- |
| AC-001 | TS-001, TS-011 | `TestRubricSchema` + `TestAPI::test_requirement_errors_carry_every_violation` + import-form component tests (client+server paths) | PASS |
| AC-002 | TS-004 | `TestAssignmentCreation` (binding, sequential+concurrent idempotency, named gaps, unknown unit) | PASS |
| AC-003 | TS-002, TS-003 | `TestOutcomeComputation` + `TestEvidenceImport` (thresholds incl. exact-4.0 boundary, determinism, no adapter use) | PASS |
| AC-004 | TS-003, TS-007, TS-012 | `TestOverallAndStaleness` precedence + `test_shared_surfaces_show_live_separate_status` + component status-pair tests | PASS |
| AC-005 | TS-007, TS-012 | API contract tests on alignment/report/tech-eval report + component tests | PASS |
| AC-006 | TS-006 | `test_stale_after_newer_confirmed_pair_and_result_never_transfers` + `test_stale_after_package_artifact_change` + stale UI guidance | PASS |
| AC-007 | TS-005 | `test_duplicate_revision_idempotent` + `test_corrected_revision_supersedes_and_prior_stays_immutable` + duplicate-notice component test | PASS |
| AC-008 | TS-008, TS-009, TS-010 | deletion cascade, pseudonymous-only serialization, untrusted-content inertness | PASS |
| AC-009 | TS-008 | `test_cross_workspace_and_unauthenticated_no_disclosure` | PASS |
| AC-010 | TS-014 | Delivery-time protocol; honest `not_complete` capability verified (`conclude_not_complete` + UI) | PENDING delivery protocol |

## Documentation Sync

| Artifact | Needed? | Change/evidence | Status |
| --- | --- | --- | --- |
| Current Spec | YES | API Behavior enumeration completed truthfully (conclusion + document download + `created` flag); behavior unchanged from approved D-decisions | DONE |
| ROADMAP / Issue | YES | ROADMAP Handoff gates recorded; Issue #20 checklist updated (authorized) | DONE (delivery update pending) |
| STAGE project/member snapshot | YES | STAGE-63 written; STAGE-64 records REVIEW | DONE |
| API / DATABASE / ARCHITECTURE / TESTING | YES | API.md F010 entry + F009 wording fix; DATABASE.md F010 tables entry; TESTING.md external-teacher protocol concretized; ARCHITECTURE unchanged (no boundary/tech change — module table already covers product-validation ownership) | DONE |
| FRONTEND / UX / UI / DESIGN_SYSTEM | NO | No shared tokens/components changed; region composes documented patterns (verified: no 技术评估/产品验证 sections exist in these docs to extend; F009 followed the same practice) | N/A - no shared-foundation change |
| AGENTS / ADR | NO | No new durable rule or architecture decision (L1 Feature) | N/A - no qualifying decision |

## PR-Ready Summary

### Suggested Title

`feat: add teacher product validation with fixed rubric and version-bound evidence (F010 T0-T5)`

### What Changed

- Backend: new `modules/product_validation/` (`rubric.py` fixed `rubric-r1` schema + deterministic outcome computation, `service.py` assignment/import/conclusion/staleness/status), `api/product_validation.py` router, migration `f010b7c9d1e3` (two additive tables), deletion-cascade extension, and live `product_validation_status` on the alignment, alignment-report, technical-evaluation-report, and delivery-report reads (field name unchanged).
- Web: `lib/api.ts` types/functions/label maps; `product-validation-region.tsx` in the 运行证据 panel (create modal, inline import form with dual validation, rubric hand-out, evidence history, document download, conclusion); live status chips and report lines; E2E journey spec (environment-gated).
- Docs: API/DATABASE/TESTING synced; Spec API enumeration completed; Test Design execution snapshot filled.

### Why

Record the external teacher's rubric evidence as version-bound, deterministic product-validation status reported separately from every technical status, so teacher-usability claims are either supported by bounded evidence or visibly absent (F010 Spec).

### Related Feature, Spec, and Issue

Spec `specs/F010-teacher-product-validation/spec.md`; Issue [#20](https://github.com/MaoyuanYang/LessonCanvas/issues/20); depends on F008 (status surface) and F009 (dataset units + harness), both DONE.

### Tests

Backend 269 passed (48 F010) + ruff clean; web 74/74 + eslint 0 errors + tsc + build clean; E2E TS-013 environment-gated with green substitute coverage and recorded resume condition; TS-014 delivery-time protocol pending owner coordination.

### Integration and Parallel Work

`N/A - no concurrent work items` (F011/F012/F013 unclaimed DRAFT throughout).

### UI Changes

YES — new 产品验证 region (no new tab/token/visual language), live status vocabulary on the F008 status pair and both report surfaces, per approved `ux-ui-f010-r1`.

### Design Changes and ADR

- Design Change summary: `N/A - L1 only; spec API enumeration completed as a documentation-fidelity record (Finding L-3)`
- ADR: `N/A - no architectural decision`
- Named Architecture Decision Authority: `N/A`
- Decision revision: `N/A`
- ADR state: `N/A`

### Breaking Changes, Migration, and Rollback

No breaking change (additive migration; shared field name unchanged with vocabulary extension; one F008 test assertion updated to the extended contract). Rollback: `alembic downgrade` drops the two additive tables; revert restores the prior constant status values.

### Risks and Follow-up

M-1 E2E resume under fault stack; M-2 TS-014 teacher protocol execution before delivery; L-1/L-2 accepted bounded-read notes.

## Delivery Authorization and Status

- Project Definition of Done (DoD): PR opened, feedback resolved, approved and merged by/with the responsible maintainer (adopted delivery mode)
- Explicitly authorized actions: full delivery flow authorized by `YMY / Project Owner` on 2026-09-01 ("交付全部授权，真实老师评审延后"): commit, push, PR, Issue update, merge; TS-014 real-teacher reviews deferred per Spec D9 honest fallback
- Tool/auth available: `gh` authenticated; git available
- Actions actually performed: commit `cbfe6cb`; push; PR [#21](https://github.com/MaoyuanYang/LessonCanvas/pull/21) created (Closes #20); Issue #20 updated; merged as `683172b` (merge commit); Issue auto-closed; main re-verified; DONE records written
- Actions not performed: TS-014 real-review execution (deferred by owner decision — follow-up import pending)
- Links/revisions: PR #21 `683172b`; DONE evidence manifest in the Spec Gate Record
- Delivery state: `DELIVERED`

## `DONE` Input Manifest

| Input | Revision/hash | Gate/status | Evidence/notes |
| --- | --- | --- | --- |
| Current Spec | `76c12f9bea6c` pre-DONE (DONE record appended after) | PASS | Gate Record: DONE |
| Affected Dependency Specs | F009 `38bff6656785`, F008 `0e1e911d1158` at SPEC READY | PASS | Unchanged since the spec gate |
| UX/UI artifact | `ux-ui-f010-r1` / `35fe2b9b1417` | PASS | |
| Test Design | `test-design-f010-r1` / `8f26e15c338d` (incl. execution snapshot + TS-014 deferral disposition) | PASS | |
| Implementation Plan / Tasks | `76fced0843e7` | CURRENT | T0–T5 delivered; T6 disposition recorded (deferred per D9) |
| Related ADR / API / Architecture / Database | API/DATABASE updated in PR #21; ARCHITECTURE unchanged | CURRENT | |
| Related Testing / Frontend / UX / UI / Design System / AGENTS | TESTING updated; others N/A no shared change; AGENTS unchanged | CURRENT | |
| Reviewed diff / implementation revision | `cbfe6cb` (PR #21) | PASS | SF-1/SF-2 fixed with regression coverage |
| Review findings / waivers | this document | PASS | No Critical; M-2 resolved by owner decision (D9 fallback); M-1 resume condition recorded |
| PR/MR or adopted no-PR delivery record | PR #21 merged `683172b` | PASS | |

## `DONE` Checklist

| ID | Checklist item | Result | Evidence |
| --- | --- | --- | --- |
| DR-01 | Spec reflects current behavior | YES | API enumeration completed truthfully; D1–D9 unchanged |
| DR-02 | All Acceptance Criteria satisfied | YES | AC-001..AC-009 automated; AC-010 via its designed fallback branch (owner-deferred real reviews per D9) |
| DR-03 | Core ACs have test/alternative evidence | YES | Traceability table; substitute coverage for TS-013 |
| DR-04 | Necessary focused/regression/broader tests PASS | YES | Backend 269 + ruff; web 74/74 + eslint/tsc/build |
| DR-05 | Required concurrency/performance/UI/E2E checks | YES | Concurrency TS-004; E2E TS-013 environment-gated with green substitute coverage and resume condition (risk-based N/A of the same class F009 recorded) |
| DR-06 | No Critical/flaky test; no Critical finding; High waivers recorded | YES | SF-1/SF-2 fixed; no waivers needed |
| DR-07 | Review complete and Docs synced | YES | review.md; API/DATABASE/TESTING + Spec |
| DR-08 | Design Changes synchronized; L3 ADR requirement | YES | N/A - L1 only; no architectural decision |
| DR-09 | Issue/work item updated | YES | Issue #20 updated (authorized) and auto-closed by merge |
| DR-10 | Confirmed PR standard met | YES | PR #21 opened, no external findings, merged by authorized flow with responsible maintainer authorization |
| DR-11 | DONE input manifest complete | YES | Above |
| DR-12 | No semantic manifest change after prior PASS | YES | First DONE validation |
| DR-13 | Concurrent-work integration / PR feedback rules | YES | N/A - no concurrent work items; no external PR review feedback received before merge |

### UI Completion

| ID | Checklist item | Result | Evidence |
| --- | --- | --- | --- |
| DUC-01 | Complete User Flow and navigation match the approved artifact | YES | Region below 技术评估; create -> import -> outcome -> status surfaces per `ux-ui-f010-r1` |
| DUC-02 | Loading behavior implemented and verified | YES | Skeleton states in region and detail expansion (component tests) |
| DUC-03 | Empty behavior implemented and verified | YES | 「尚未进行产品验证」 empty state test |
| DUC-04 | Error and recovery behavior implemented and verified | YES | All-violation display (client+server), named gaps, stale guidance, requirement error mapping tests |
| DUC-05 | Success behavior and exit | YES | Outcome announcements, status chips, document download journey |
| DUC-06 | Permission/disabled/offline states | YES | Non-owner safe not-found (API tests); desktop-only actions per small-screen rule |
| DUC-07 | Responsive behavior verified | YES | 1024px boundary: read-only chips/outcomes preserved; actions deferred (component tests + useDesktop) |
| DUC-08 | Accessibility requirements verified | YES | Labelled section, aria-expanded disclosures, focus management on validation errors, text+marker statuses, polite status announcements; keyboard operability per component tests |
| DUC-09 | Design System reuse/extension compliant | YES | Reuse table; no new tokens or visual language |
| DUC-10 | Required interaction/UI/E2E tests pass or approved N/A | YES | Component suites green; E2E environment-gated with green substitute coverage and resume condition |

## Final State

- `DONE` Status: `PASS`
- `DONE` input manifest revision/hash: above (spec `76c12f9bea6c` pre-DONE + Gate Record appended)
- Validated delivery revision: PR #21 merge `683172b`
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session 2026-09-01 ("交付全部授权，真实老师评审延后")
- Approval scope: F010 full delivery flow (commit/push/PR/Issue update/merge) with the TS-014 deferral disposition
- Roadmap Status: `DONE`
- If not DONE, exact blocker/unperformed action: none blocking; follow-up residual: import the teacher's real three-unit reviews when available and append evidence (D9)
- Resume from: N/A - terminal; follow-up via the recorded residual
- Final Stage activity state / snapshot revision: `COMPLETE` / STAGE-65

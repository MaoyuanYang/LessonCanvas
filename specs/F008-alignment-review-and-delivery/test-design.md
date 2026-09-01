# Test Design: F008 Alignment Review and Delivery

## Inputs and Environment

- Spec: `specs/F008-alignment-review-and-delivery/spec.md` @ `dc301bba1a83` (`SPEC READY` PASS)
- UX/UI: `specs/F008-alignment-review-and-delivery/ux-ui.md` @ `ux-ui-f008-r1` / `6bca800ac896` (`UI READY` PASS)
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (VCS base `main @ 2b36d73`)
- Environment: existing deterministic harness — docker compose (PostgreSQL/pgvector, Redis, MinIO), FakeModelAdapter for logic, Clerk token fixtures; F008 is model-free by design (D1/D7), so no live-model dependency is introduced; live DeepSeek is not required for any F008 scenario
- Test tooling: pytest (unit/integration/API/concurrency), Vitest + Testing Library (component/interaction), Playwright (E2E + a11y checks)

## Risk Inventory

| Risk | F008 exposure | Coverage |
| --- | --- | --- |
| Findings not deterministic or unexplainable | Coverage computation drifts or hides gaps | TS-001, TS-002, TS-003 |
| False validated status (missing member or unresolved severe treated as validated) | Status logic or override eligibility wrong | TS-002, TS-004, TS-005, TS-009 |
| Override mutates content or escapes audit | Override write path | TS-006, TS-007, TS-012 |
| Stale review presented current | Version change / regeneration recalculation | TS-008 |
| Dishonest delivery (wrong label, mixed-version package, partial success) | Export build path | TS-010, TS-013, TS-014 |
| Package not byte-identical / re-rendered / re-billed | Export artifacts | TS-010 |
| Print report omits label or statuses | Report route/snapshot | TS-011 |
| Cross-account disclosure | New endpoints leak alignment/exports | TS-012 |
| Workspace-shell regression | Tenth view + family-panel links break F003–F007 surfaces | TS-017 |

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 objective relationships + evidence | TS-001, TS-015, TS-016 |
| AC-002 deterministic recomputation, no model call | TS-001, TS-008 |
| AC-003 missing-family severe gap | TS-002 |
| AC-004 failed-validation conflict finding | TS-003 |
| AC-005 validated export blocked / draft available | TS-004 |
| AC-006 gap not overridable | TS-005 |
| AC-007 reasoned override auditable | TS-006 |
| AC-008 withdraw restores finding | TS-007 |
| AC-009 version change makes prior state historical | TS-008 |
| AC-010 validated vs not-evaluated pair | TS-009 |
| AC-011 labelled byte-identical ZIP, idempotent | TS-010, TS-013 |
| AC-012 printable report content | TS-011, TS-016 |
| AC-013 non-disclosure + deletion | TS-012 |

## Test Scenarios

### TS-001: Deterministic coverage computation across all families

- Protects: `AC-001`, `AC-002`
- Risk/type: Rule / Correctness
- Given: a confirmed version pair with a complete current artifact set (in-run complete and, in a second fixture, F007-retained members), plus mixed coverage at objective level (an objective covered by plans+decks+exercises, one covered by plans only, one covered by no lesson)
- When: alignment is computed twice from the same state
- Then: both computations return identical objective-first relationships with per-family verdicts; retained members count as supported with provenance; the uncovered objective shows missing across families; every verdict row carries owning versions and evidence; no model/trace call is recorded during computation (assert trace-events unchanged)
- Level: Unit + Integration/API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Data/fixture/environment: seeded confirmed pair and artifact rows via existing services
- Result/evidence: NOT RUN

### TS-002: Missing family members produce severe gap findings and block validation

- Protects: `AC-003`
- Risk/type: Rule / Boundary
- Given: lessons in scope where one lacks a plan, one lacks a deck, one lacks exercises, one lacks the answer side, and one has all three (each missing case also split in-run-failed vs never-generated)
- When: alignment is computed
- Then: each missing member yields a gap-class severe finding naming lesson, family member, and recovery action; technical package status is incomplete; the complete lesson contributes no finding
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-003: Failed structural/pairing validations surface as conflict-class severe findings

- Protects: `AC-004`
- Risk/type: Rule
- Given: artifacts with recorded failed structural validation (plan/deck) and a failed exercise/answer pairing validation, each otherwise present
- When: alignment is computed
- Then: each yields a conflict-class severe finding naming the disputed validation outcome with evidence links and overridable eligibility marked true; status remains incomplete
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-004: Validated export refused with named blockers while draft remains available

- Protects: `AC-005`
- Risk/type: Error / Honesty
- Given: the state from TS-002/TS-003 (unresolved severe findings)
- When: a validated export is requested, then a draft export
- Then: the validated request returns a requirement error naming each blocking finding and its recovery action; the draft request succeeds and its record/label/package metadata carry 草稿/draft
- Level: API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-005: Gap-class override attempts are refused

- Protects: `AC-006`
- Risk/type: Validation / Rule
- Given: an open gap-class severe finding
- When: an override is submitted for it (also: empty reason, short reason, wrong version pair)
- Then: each attempt returns the requirement/stale error, nothing is written, no audit event claims an override
- Level: API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-006: Override records an auditable decision without mutating content

- Protects: `AC-007`
- Risk/type: Audit / Integrity
- Given: an open conflict-class severe finding with complete artifact rows
- When: the owner records an override with a valid reason (twice with identical payload)
- Then: the decision persists bound to (project, version pair, finding key) with reason, owner identity, and audit event; the duplicate returns the same decision; the evaluated artifact rows, checksums, and validation outcomes are byte-identical before/after; recomputed status no longer blocks on that finding
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-007: Override withdrawal restores the finding

- Protects: `AC-008`
- Risk/type: State transition
- Given: a recorded override on a conflict finding
- When: the owner withdraws it (and a second withdraw is attempted)
- Then: the finding returns open, status recalculates to incomplete, the withdrawal is audited, the second withdraw is a no-op refresh; original override history remains queryable
- Level: API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-008: Version change or regeneration makes prior overrides and labels historical

- Protects: `AC-009`, `AC-002` (recompute part)
- Given: a version pair with overrides and a validated status; then a new confirmed pair and regenerated artifacts (including retained members per F007)
- When: alignment is recomputed and the export history is listed
- Then: findings reflect only the new pair (retained members current per F007 D5); prior overrides are historical and never applied to new-pair findings; older export records stay downloadable bound to their versions/labels and are visibly not current
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-009: Validated status stays separate from product-validation status

- Protects: `AC-010`
- Risk/type: Honesty / Status pair
- Given: a fully satisfied D3 state (all lessons, all three families complete+validated, zero unresolved severe)
- When: alignment is computed
- Then: technical package status is validated and product-validation status is not-evaluated in the same payload; no code path in the module can set a product-validation value other than not-evaluated
- Level: Unit + Integration/API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-010: Export builds a byte-identical labelled ZIP idempotently

- Protects: `AC-011`
- Risk/type: Delivery integrity / Idempotency
- Given: a validated (fixture A) and a draft (fixture B) current state
- When: exports are created and downloaded (and each creation is repeated with an unchanged manifest, including concurrently)
- Then: the ZIP streams through the authorized endpoint with no storage path exposure; member bytes equal the stored objects (checksum compare); package metadata inside the archive carries label, bound versions, and manifest; the repeat/concurrent create returns the same export record and does not rebuild (single storage write observed); draft and validated labels never interchange
- Level: Integration/API/Concurrency
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Data/fixture/environment: MinIO artifacts bucket
- Result/evidence: NOT RUN

### TS-011: Printable report carries versions, label, coverage, findings, and both statuses

- Protects: `AC-012`
- Risk/type: Contract
- Given: a current alignment state with findings and one recorded override, and a historical export's report snapshot
- When: report data is fetched for both
- Then: both contain bound versions, label, objective coverage summary, findings with override records, and the status pair; the snapshot reflects its export-time state, not the current state
- Level: API + Component
- Automation target/path: `apps/backend/tests/test_alignment.py` + `apps/web/…` report component test
- Result/evidence: NOT RUN

### TS-012: Authorization non-disclosure and deletion cascade

- Protects: `AC-013`
- Risk/type: Security / Privacy
- Given: a second teacher account and an unauthenticated caller; and a project with overrides, exports, and package objects
- When: every F008 endpoint is requested cross-workspace/unauthenticated; then the project is deleted
- Then: all requests return the authorization-denied class without existence disclosure; deletion removes override rows, export rows, and package/report objects with no residue
- Level: API + Integration
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-013: Export build failure settles failed without partial success

- Protects: `AC-011` (honest delivery), Spec Error Cases
- Risk/type: Provider failure / Recovery
- Given: an artifact object missing from storage mid-build (injected storage error), and a version-pair switch during build
- When: export creation runs
- Then: the export settles failed with the provider-failure class and retry guidance; no partial ZIP is delivered or downloadable; the version-switch case settles failed (manifest no longer current) rather than a mixed package
- Level: Integration
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-014: Prerequisite and stale-version error paths

- Protects: Spec Error Cases (no confirmed pair; version-pair mismatch on action)
- Risk/type: Error
- Given: a project without a confirmed pair; and an override/export submitted against a superseded pair
- Then: the first returns the requirement error naming the missing gate; the second returns the stale-version class; neither writes anything
- Level: API
- Automation target/path: `apps/backend/tests/test_alignment.py`
- Result/evidence: NOT RUN

### TS-015: Alignment view component states

- Protects: `AC-001`, `AC-005`–`AC-010` (presentation), UX/UI State Matrix
- Risk/type: UI interaction
- Given: mocked alignment payloads (loading, no-pair, full coverage, gaps, conflicts, overridable finding, recorded override, validated, stale history)
- When: the 对齐与交付 view renders each
- Then: status pair always shows both statuses; findings group by severity with correct recovery actions; override action appears only on overridable findings; 交付校验包 disabled with named blockers when unresolved; history rows show version-bound labels; requirement/stale/provider errors map to the designed inline states
- Level: Component
- Automation target/path: `apps/web/…` Vitest + Testing Library
- Result/evidence: NOT RUN

### TS-016: E2E journey — inspect, override, export, print (keyboard + a11y)

- Protects: `AC-001`, `AC-007`, `AC-010`, `AC-011`, `AC-012` end to end
- Risk/type: E2E / Accessibility
- Given: a seeded project on the deterministic stack with a complete package plus one disputed conflict finding
- When: the teacher opens 对齐与交付, expands evidence, records a reasoned override, watches status recalculate to validated with product status 未评估, exports the validated package, downloads it, and opens the print report
- Then: every step is keyboard-operable with correct focus management; the downloaded ZIP contains the labelled metadata; the report renders versions/label/statuses/findings; scripted a11y checks pass
- Level: E2E + Accessibility
- Automation target/path: Playwright journey (fault/deterministic stack; no live model needed by design)
- Result/evidence: NOT RUN

### TS-017: Workspace-shell and prior-surface regression

- Protects: F003–F007 surfaces, tenth-view integration
- Risk/type: Regression
- Given: the workspace with all prior tabs and the new 对齐与交付 tab
- When: prior journeys (generation/deck/exercise/evidence/version-compare) and family-panel completion links run
- Then: prior surfaces behave unchanged; the new tab and family-panel passive link 查看对齐情况 navigate correctly; no prior test regressions
- Level: E2E + full suites
- Automation target/path: existing Playwright journeys + backend/web full suites
- Result/evidence: NOT RUN

## Parallel-feature integration/merge regression

`N/A - no concurrent work items` — F008 is the sole claimed `NEXT` item; single-member repository.

## Automation Feasibility

All scenarios are automatable on the existing deterministic stack. No live-model dependency exists by design (D1/D7); ZIP/report verification uses local MinIO and byte/checksum comparison. Manual residual: visual print-output inspection is limited to automated markup/a11y checks plus one scripted print-route check (recorded in the Execution Evidence Snapshot); residual risk accepted as low because the report reuses semantic markup and token styles.

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core AC verifiable with ≥1 TS | YES | Traceability table: AC-001..AC-013 all mapped |
| TR-02 | Happy Path, Alternative Flows, boundaries | YES | TS-001/002/003/008 boundaries; alternative flows in TS-013/TS-014 |
| TR-03 | Error, Authentication/Security, Regression | YES | TS-004/005/013/014 errors; TS-012 security; TS-017 regression |
| TR-04 | Idempotency/Concurrency/Transaction/Consistency | YES | TS-006/008/010/013 |
| TR-05 | Retry/Timeout/Migration/Compatibility/performance | YES | TS-013 retry/failure; migration is additive (Plan-verified); N/A perf — bounded in-process computation, no new infra |
| TR-06 | UI interaction/state, Accessibility, E2E | YES | TS-015/016/017 |
| TR-07 | Levels/automation targets target observable behavior | YES | API payload/bytes/status assertions; component/E2E assert what users see |
| TR-08 | Environment/data/fixtures available | YES | Existing docker-compose harness, MinIO, seeded services; no live model required |
| TR-09 | Bug branch | N/A - new Feature, no Bug |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open | YES | All scenarios automatable; no Critical Test Questions |
| TR-11 | Concurrent NEXT integration slice | N/A - no concurrent work items |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `dc301bba1a83`) + UI READY manifest (`ux-ui-f008-r1` @ `6bca800ac896`) + this artifact `test-design-f008-r1` @ `f620f9cc763f`
- Evidence checklist result: ALL YES (TR-01..TR-11, with recorded N/A reasons where permitted)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01
- Approval scope: F008 Test Design at `test-design-f008-r1`

## Execution Evidence Snapshot

Recorded 2026-09-01, branch `feature/F008-alignment-review-and-delivery`, deterministic stack (docker compose PostgreSQL/Redis/MinIO; FakeModelAdapter; local MinIO real bytes).

| Scenario | Result | Evidence |
| --- | --- | --- |
| TS-001 deterministic coverage, no model calls | PASS | `tests/test_alignment.py::test_coverage_deterministic_and_validated` (double-compute equality, run-count unchanged) |
| TS-002 missing-family severe gaps | PASS | `test_missing_family_members_block_validation` (missing/in-progress/failed classes) |
| TS-003 failed-validation conflicts | PASS | same test (conflict key with evidence + overridable) + `test_stale_blueprint_conflict_not_overridable` |
| TS-004 validated export blocked, draft available | PASS | `test_validated_export_blocked_draft_allowed` |
| TS-005 gap override refused | PASS | `test_override_lifecycle` (gap/unknown/short reasons 422) |
| TS-006 override auditable, content unchanged, duplicate-safe | PASS | `test_override_lifecycle` + `test_override_stale_version_rejected` |
| TS-007 withdrawal restores finding | PASS | `test_override_lifecycle` (idempotent withdraw) |
| TS-008 version change recomputes, history truthful | PASS | `test_new_version_recomputes_and_histories_exports` |
| TS-009 validated vs not-evaluated pair | PASS | `test_coverage_deterministic_and_validated` + `test_product_status_cannot_leave_not_evaluated` |
| TS-010 byte-identical labelled ZIP, idempotent + concurrent | PASS | `test_export_zip_labelled_byte_identical_and_idempotent` (checksum compare, ThreadPool duplicate converge) |
| TS-011 report contents + snapshot | PASS | `test_report_endpoint_and_generated_at` + export-report assertions in TS-010 test; web halves in Vitest report tests |
| TS-012 non-disclosure + deletion cascade | PASS | `test_cross_workspace_no_disclosure` + `test_deletion_cascades_overrides_and_exports` (package object verified deleted) |
| TS-013 build failure / version switch settle failed | PASS | `test_export_storage_failure_settles_failed` + `test_export_version_switch_during_build_fails` |
| TS-014 prerequisite/stale errors | PASS | `test_alignment_prerequisite_without_pair` + stale case in TS-006 group |
| TS-015 component states incl. override dialog | PASS | Vitest `__tests__/alignment-panel.test.tsx` 6 tests (status pair, gated export, override+withdraw+recalc, blocked-error mapping, prerequisite, print views) |
| TS-016 E2E validated path + keyboard + ZIP + print | PASS | Playwright `e2e/alignment-journeys.spec.ts` TS-016 green 2026-09-01 (alignment view → status pair → validated export → keyboard ZIP download → print report route) |
| TS-017 family-banner link + prior-surface regression | PASS | Playwright TS-017 green; full backend 196/196 + web 57/57 suites green (prior surfaces unchanged) |

Full-suite verification (2026-09-01): backend `uv run pytest` exit-0 (196 passed, incl. 16 alignment tests) + `ruff check` clean; web Vitest 57/57, eslint 0 errors (7 pre-existing e2e warnings), `tsc --noEmit` clean, `next build` clean; E2E fault stack green.

### Recorded deviations and residuals (owner-visible)

- M-1 (E2E environment class, F004 M-1 recurrence): the full scripted-override browser journey (DECK_TOO_LONG revision → conflict → override in the dialog) was attempted five times; the shared planning-interview/blueprint-confirm stage intermittently stalled under environment load (failing point moved between interview, decisions, and exercise regeneration; one attempt reached the final print step). The delivered TS-016 covers the validated browser path end to end; the override browser interaction is covered by component TS-015 (dialog, reason validation, recalculation, withdraw) and backend TS-005/006/007 (full override lifecycle, audit, eligibility). Resume condition: re-run the scripted-override journey under a stable environment and append evidence.
- M-2 (environment note): the local `next dev` server intermittently raised a client-side `SyntaxError: Invalid or unexpected token` on authenticated pages (reproduced with F008 web changes stashed, i.e. pre-existing); E2E was executed against a production `next build && next start` server, which was stable. Not an F008 defect; revisit if it recurs during F009 E2E.
- L-1: the print report's paper output relies on the browser print engine; automated evidence covers route markup, content contract, and a11y semantics, with one scripted in-browser print-path pass (no physical/PDF diff assertion).

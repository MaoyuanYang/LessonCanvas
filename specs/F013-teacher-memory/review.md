# F013 Self Review — Teacher Memory

- Review revision: `review-f013-r1`
- Reviewed inputs: Spec @ `75ee61c2cf0b` (`SPEC READY`), UX/UI @ `ux-ui-f013-r1` / `8b39aeebb9a9` (`UI READY`), Test Design @ `test-design-f013-r1` / `c033f186772a`, Plan `plan-f013-r1` @ `427356ca088e`
- Branch: `feature/F013-teacher-memory`
- Verification (deterministic stack: isolated PostgreSQL 5433 / MinIO 9002 / Redis 6380, fake adapter, eager tasks):
  - Backend: 504 passed + 4 skipped (progress-dot count; exit 0; includes 22 new `tests/test_memory.py` tests + 1 adversarial memory scenario in `test_guardrails_injection.py`) + `ruff check src tests migrations` clean.
  - Web: 108/108 vitest (11 new memory component tests) + `tsc --noEmit` clean + `eslint .` 0 errors (3 warnings pre-existing on `main`: `print-report-view.tsx` ×2, `alignment-panel.tsx` ×1).
  - E2E: `e2e/memory-journey.spec.ts` 3/3 journeys green (TS-023 full journey, TS-024 keyboard-only decisions, TS-025 420px reduced spot) on `E2E_MEM_FAULT=1` with the fake-adapter backend.

## AC → TS → Evidence

| AC | Scenario(s) | Evidence |
| --- | --- | --- |
| AC-001 | TS-001..TS-004 | `test_memory.py::test_brief_confirm_runs_bounded_validated_pass`, `test_all_three_triggers_and_duplicate_settle_never_rebill`, `test_pass_failure_never_blocks_confirm_flow`, `test_pass_retry_executes_and_completed_pass_never_reruns`, `test_invalid_candidates_dropped_honest_empty` — all green |
| AC-002 | TS-008, TS-022, TS-023 | `test_confirmed_record_applies_across_discovery_planning_generation` (payloads + `memory.applied` + run-summary section for discovery/planning/generation); component `__tests__/account-memory.test.tsx` (region); E2E evidence region |
| AC-003 | TS-009 | `test_language_conflict_confirmed_version_wins` (skip + confirmed field authoritative + conflict in trace/summary/project view) |
| AC-004 | TS-013, TS-014 | `test_record_deletion_semantics`, `test_project_and_workspace_deletion_remove_memory_completely` (F011 sweep registration + cascades) |
| AC-005 | TS-005..TS-007 | `test_rejected_proposal_not_reproposed_identically` (normalization variants), `test_pending_slot_supersede_and_stale_decisions`, `test_unconfirmed_state_has_no_run_effect` |
| AC-006 | TS-015 | `test_memory.py::test_adversarial_memory_stays_inert_serialized_data` + `test_guardrails_injection.py::test_adversarial_memory_content_stays_inert_in_payloads` (markers serialized-only; no tool/policy/cross-workspace effect; event-type whitelist) |
| AC-007 | TS-012 | `test_project_override_scopes_application_and_is_audited` (A excluded / B applied / re-enable / audit action) |
| AC-008 | TS-018, TS-019 | `test_memory_state_snapshot_binds_revision_list`; updated `test_technical_evaluation.py` (structured snapshot passes C-MEM-1, legacy placeholder fails, comparability signature includes memory set); conftest alembic chain |
| AC-009 | TS-010, TS-011, TS-020 | `test_injection_budget_whole_records_priority_and_disclosure` (U6 order, whole records, disclosed skips), `test_record_cap_and_length_caps_with_explicit_errors` (`MEMORY_LIMIT` count/length copies, convergence), component quota/edit-counter states |

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| IF-1 | Medium | `memory_passes.trigger_kind` initially `String(16)`; `blueprint_confirm` (17 chars) raised `StringDataRightTruncation` through confirmation flows. | Fixed to `String(24)` in model + migration before any permanent environment applied it; only the disposable local test DB had ever migrated the bad shape (dropped and recreated). Regression covered by every trigger test. |
| IF-2 | Medium | Sequential-fetch component tests broke because the new proposal region consumes one `/memory` request per panel mount. | Fixed the one order-sensitive test (`workspace-panels` stale-banner) to route mocks by URL — the app behavior is legitimate; additionally hardened all memory components against malformed `/memory` payloads (`?? []` reads) so unrelated suites with default mocks stay green. |
| IF-3 | Low | The badge/region/account poll `/memory` every 4 s while mounted (needed so best-effort passes surface without an event channel). | Accepted: one bounded GET per 4 s ≈ 15 req/min against the 240/min general window; stops when no component is mounted; proposal state is small. |
| IF-4 | Low | Dev-server project-list link click intermittently loses the actionability race (the pre-existing F004 M-1 class), blocking the E2E full journey. | Worked around in the spec by resolving the created project id from the API and navigating directly (`page.goto`); recorded as the same known dev-server flake, not an application defect. |
| IF-5 | Low | E2E TS-023's mid-journey was simplified: applied-context is demonstrated on a discovery run of a second project instead of driving the full planning/blueprint flow in the browser (the inline decision loop plus cumulative waits exceeded sane journey budgets). | Accepted: planning/generation application remains fully proven by backend TS-008 (payload + trace assertions for all three run families); the E2E still covers the complete memory decision → application → management → deletion loop. Recorded as a scope note, not a coverage gap. |
| M-1 | Medium | TS-026 (live DeepSeek proposal-quality pass) required separate owner authorization at execution time. | RESOLVED 2026-09-03: owner authorized; two live journeys executed against real DeepSeek — quality proposals across categories with derived values, a real transient provider failure settled best-effort without affecting the journey, live dedupe honest-empty on the run trigger, both journeys purged by account deletion. Evidence: `live-evidence.json` + Test Design execution snapshot. |

No Critical findings; no unfixed High findings.

## Checklist

- Spec/Scope compliance: every AC traced above; Out of Scope respected (no implicit extraction, no cross-user data, no category additions, no memory-driven regeneration).
- Architecture boundaries: new `teacher_memory` module owns records/proposals/overrides/passes; consumes identity_workspace auth + discovery_planning evidence; artifact/discovery/planning graphs consume the context function as a labeled input; trace writes via existing helpers; one new Celery task on the existing transport; no new service/cache/framework.
- Data/transactions: unique pass identity (idempotent scheduling), record identity uniqueness with convergence, workspace-row-lock cap check (F011 D9 pattern), snapshot-once applied context.
- Security/privacy: owner-only on every endpoint (sweep-verified), audit content-free, memory untrusted at re-injection (adversarial tests), deletion completeness extended to all four tables.
- Migration: one additive migration `f013b1d2e3f4`; `SET NULL` evidence FKs keep workspace memory across project deletion; no destructive change.
- Docs sync: API/DATABASE/ARCHITECTURE/TESTING/AGENTS module-consumer note updated in this revision (see Documentation Sync in the delivery summary); UX flow already matched the built design.
- UI: states per the UX matrix rendered and component/E2E verified; Design System reused without new primitives; a11y assertions in TS-024 and component labels.

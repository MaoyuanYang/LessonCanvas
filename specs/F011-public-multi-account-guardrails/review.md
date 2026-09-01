# Feature Review: F011 Public Multi-Account Guardrails

- Work item: [GitHub Issue #22](https://github.com/MaoyuanYang/LessonCanvas/issues/22)
- Branch: `feature/F011-public-multi-account-guardrails` (from `main @ 683172b`)
- Review date: 2026-09-01
- Reviewer: implementation self-review (ZCode feature-dev session); owner decision points recorded interactively

## Spec Compliance

All eleven ACs implemented and verified; traceability maintained in `test-design.md`.

| AC | Evidence |
| --- | --- |
| AC-001 sweep | `test_guardrails_isolation.py`: inventory-driven (71 openapi paths), cross-account + unauthenticated, safe-envelope assertions |
| AC-002 limits | `test_guardrails_rate.py` (windows, per-workspace keys, reset, nested expensive), `test_guardrails_upload_policy.py` (daily volume), `test_guardrails_stream_cap.py` (SSE cap) |
| AC-003 admission | `test_guardrails_concurrency.py` (third-run 409 with active ids, duplicate convergence, recovery after settle) |
| AC-004 injection | `test_guardrails_injection.py` + `adversarial_datasets/` (governed, checksummed, fail-closed); gates/cross-visibility/tool dispatch assertions |
| AC-005 uploads | sniffing mismatch classes, oversize-before-buffer, zip-bomb docx (crafted central directory), pdf page cap, entry-count guard, student-data evasion outcomes |
| AC-006 deletion | `test_guardrails_deletion.py` (checkpoint rows, completeness verification, visible partial + repair, account purge ledger) + `test_guardrails_worker_fastfail.py` (immediate terminal settle; transient retry control) |
| AC-007 audit | `download.*` audits on five endpoints, `GET /account/audit` cursor-bounded, disclosure copy, D4(b) content-free ledger survives; account component tests |
| AC-008 quota races | concurrent project creates exactly 5; concurrent uploads exactly 10; workspace resolution race adopted-winner |
| AC-009 dependency/secret | `uv audit` 0 findings; `pnpm audit` 0 after workspace overrides; tracked-tree credential scan clean; `.env` ignored (verified) |
| AC-010 journey | `test_guardrails_multiaccount_journey.py`: 5 concurrent workspaces, isolation, idempotency, bounded spend, mid-flow deletion leaves nothing |
| AC-011 surfaces | account page sections + `guardrailFeedback` mapping + small-screen gating (component tests; E2E env-gated) |

## Findings and Fixes (implementation-time, all fixed with tests)

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| IF-1 | High (latent F001 defect) | `sources.content_type` column was VARCHAR(64); the OOXML content type is 71 characters — every `.docx` API upload would have failed with a 500. Exposed by the first docx upload hardening test. | Column widened to 128 in `f011e2f4a5b6` with downgrade; regression covered by the docx path tests. |
| IF-2 | High (race) | `resolve_workspace` check-then-insert raced under concurrent first requests (12 parallel creates → unique-violation 500s). Same F001 check-then-insert class as the count quotas. | IntegrityError path adopts the concurrent winner (PostgreSQL unique-index waiting guarantees the winner has committed); covered by the concurrent-create test. |
| IF-3 | High (deletion repair defect) | First repair attempt kept deleting DB rows even when an object delete failed, losing the object key — the orphan became permanently unrepairable while verification correctly refused to complete. | Metadata-only `deletion_residuals` ledger records failed keys; a re-issued delete repairs them first, then re-verifies; residual rows clear on completion. Covered by the partial→repair tests. |
| IF-4 | Medium (test honesty) | The initial SSE-cap test used `client.get` on a never-terminating stream (hang) and an early sweep asserted denial on workspace-self surfaces. | Rewritten: registry-saturation + real API 429 + terminating-stream release; sweep distinguishes own-data surfaces and excludes the destructive `DELETE /account`. |

No Critical findings remain. No High findings remain unfixed.

## Bug Branch (F006 M-2 / F004 M-2 worker fast-fail)

The recorded live reproduction (`specs/F006-layered-run-evidence/review.md` M-2: project deleted at `generating` 4/6 → `StaleDataError` → two 180 s-delayed retries) is honored with a deterministic surrogate per TQ-004: `settle_vanished_run` settles `StaleDataError`-class and run-row-missing errors immediately as terminal `missing_run`; `_run_row_missing` returns False when existence cannot be proven (connection blip), keeping the bounded-retry path; the negative control proves `ProviderTransientError` still re-raises for retry. Residual: the exact live interleaving is not replayed in CI (would require a live model mid-run deletion); the shared code path and the F006 evidence bound the risk.

## Verification Evidence

```text
Backend:  cd apps/backend && uv run pytest        454 passed, 1 skipped (env-gated sweep skip), ruff clean
Web:      corepack pnpm web:test                 83/83 passed; eslint 0 errors (7 pre-existing warnings); tsc clean; build clean
Audit:    uv audit → 0 findings (91 packages); pnpm audit --prod → 0 findings (overrides: postcss >=8.5.18, sharp >=0.35.0)
Secrets:  credential-pattern scan over tracked files → no matches; only .env.example placeholders tracked
E2E:      guardrails.spec.ts environment-gated (CLERK_E2E=1) per repo precedent; substitute coverage green
```

## Residuals (owner-visible)

| ID | Severity | Residual | Disposition |
| --- | --- | --- | --- |
| M-1 | Medium (environment) | TS-018 authenticated E2E not executed in this environment (Clerk dev-instance instability class, F004 M-1/F010 TS-013 precedent). | Substitute coverage green (component tests for every account/limit/delete-failed surface); resume by running `corepack pnpm --filter web test:e2e` under stable auth and appending evidence to the Test Design execution snapshot. |
| M-2 | Low (documented assumption) | SSE stream cap uses an in-process registry (Spec D1 single-process deployment assumption). | Documented in `sse_registry.py` and the Spec; revisit only with measured multi-process evidence before F012 deployment. |
| L-1 | Low (accepted residual) | Student-data screening false negative: spaced/split identifier forms evade the regex screen (F001 TQ-003 close-out records the boundary). | Recorded in `test_student_data_evasion_outcomes_recorded`; mitigated by the upload policy boundary, teacher rights acknowledgement, and the teacher review loop. |
| L-2 | Low (by design) | Rate counters count rejected attempts; a saturated window cannot be drained by retrying. | Intentional (bounded abuse profile); window reset is deterministic and returned to the caller. |
| L-3 | Low (watch) | pnpm workspace overrides raise postcss/sharp above Next.js's own pins. | Build + full web suite verified on the overridden versions; re-verify at the next Next.js upgrade. |

## Documentation Sync

- `docs/API.md`: F011 guardrail API resolution (limits, admission, usage/audit reads, upload hardening, deletion semantics).
- `docs/DATABASE.md`: F011 migration resolution (rate counters, retained ledger, residual ledger, column widening, checkpoint cascade); audit-retention open item closed (D4(b)); hosted-store item re-scoped to F012.
- `docs/TESTING.md`: adversarial corpus governance pattern + guardrail suite inventory + dependency evidence.
- `README.md`/`AGENTS.md`: unchanged (no command or durable-rule change; the overrides live in the existing workspace file).
- Spec API enumeration and AC table match the implementation truthfully; no acceptance was lowered.

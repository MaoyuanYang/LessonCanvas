# F012 Review Record

- Review ID: `review-f012-r3` (FULL — T1–T11a complete incl. T8/T9 deployed verification; awaiting delivery authorization)
- Reviewed revision: branch `feature/F012-deployed-portfolio-proof` working tree, 2026-09-02
- Inputs: Spec (ADR-0006 revised, revalidated PASS), UX/UI @ `ux-ui-f012-r2`, Test Design @ `test-design-f012-r2`, Plan `plan-f012-r2`

## Self Review Findings (T1–T7 + ADR-0006 slice)

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| IF-1 | Medium | `tests/test_guardrails_deletion.py::ensure_checkpoint_tables` created thread_id-only stub checkpoint tables (`CREATE TABLE IF NOT EXISTS`), leaving a wrong schema behind in the test database that breaks any later `PostgresSaver.setup()` user with `UndefinedColumn`. Latent F011 test-suite defect surfaced by TS-011. | FIXED: the helper now runs the authoritative `PostgresSaver.setup()` schema; the stub-row insertion uses schema-valid rows; lifecycle tests added (`tests/test_checkpointer_lifecycle.py`). |
| IF-2 | Low | Sample-read relaxation is threaded explicitly per safe-GET route rather than method introspection; a future GET endpoint added without `allow_sample_read=True` will simply stay owner-only (fail-closed). | ACCEPTED by design: fail-closed drift direction; the F011 inventory sweep keeps non-disclosure invariant. |
| IF-3 | Low | `deploy.replicas: 1` in compose is documentation of the D8 single-process constraint; plain `docker compose` does not enforce replicas. | ACCEPTED: uvicorn default workers=1 is the actual enforcement; constraint documented in ARCHITECTURE.md and compose comment; scale-out requires re-verification per Spec D8. |
| IF-4 | Low | Web build bakes `NEXT_PUBLIC_API_BASE_URL` at build time; changing the LAN address requires a rebuild. | ACCEPTED: deploy.sh rebuilds; deploy.env.example documents the value; noted in README. |
| IF-5 | Low (ADR-0006 slice) | `POST /auth/guest-token` is unauthenticated; the F011 inventory sweep initially flagged it as a violation. | RESOLVED: endpoint added to the sweep's explicit `EXCLUDED` set with justification; disclosure/no-row-creation behavior covered directly by `test_guest_token.py` (TS-016). |
| IF-6 | Low (ADR-0006 slice) | After account purge, any later authorized call by the same subject find-or-creates a fresh empty workspace. | ACCEPTED inherent to subject-keyed identity (pre-existing behavior, unchanged); test ordering documents it. |
| IF-7 | Low (ADR-0006 slice) | Concurrent first-load queries could each mint a guest token (N browsers-in-one). | FIXED in `lib/auth.ts`: shared in-flight promise dedupe; pinned by `__tests__/auth.test.tsx`. |
| IF-8 | **High** (T8 deployed) | `PostgresSaver.setup()` first-use DDL (`CREATE INDEX CONCURRENTLY`) deadlocked in the multi-process deployed topology (api + worker + one-off seeds): requests hung indefinitely on discovery start; observed live in `pg_stat_activity`. This is the concrete B-001/T7 deployed-topology defect. | FIXED: new `lessoncanvas.checkpointer_setup` module runs serially in the api and worker entrypoints (after `alembic upgrade head`) with `lock_timeout=15s` + 6 bounded retries; deadlocked sessions cleared; live journey TS-029 passes afterwards. T7 verdict upgraded: defect found + fixed + re-verified. |
| IF-9 | Low (T9 deployed) | Workspace tabs nav (`flex` without wrap) overflowed the 420px viewport (page-level horizontal scroll on `/sample`; pre-existing shared component first exercised on small screens by the sample shell). | FIXED: `flex-wrap` on the nav; deployed re-verified `scrollW == clientW` at 420px; `/projects`, `/account` unaffected-clean. |
| IF-10 | Low (T8 build) | Web image build initially failed two ways: host `node_modules` overlaying the image context, and the pnpm-workspace standalone layout (`standalone/apps/web/server.js` + symlinked root `node_modules`). | FIXED: root `.dockerignore`; runtime stage copies the full standalone tree and runs `node apps/web/server.js`. |
| IF-11 | Low (T8 seed) | One-shot `seed_sample.py` in-container runs did not exit: the eager pipeline's PostgresSaver `ConnectionPool` keeps a non-daemon thread alive. | FIXED: explicit flush + hard exit with a documented comment; deployed seed runs exit 0. |

## Verification Snapshot (2026-09-02, deterministic environment)

- Backend: `uv run pytest` — 477 passed, 4 skipped (guest-token sweep pair now sanctioned-skip; env-gated E2E unchanged); `ruff check src tests migrations` clean. Migration `f012a7c9d2e4` (subject rename + constraint/index rename) applied and exercised.
- Web: `corepack pnpm web:test` — 15 files / 97 tests; `web:typecheck` clean; `web:lint` 0 errors (3 pre-existing warnings).
- E2E (real backend + web, guest-token bootstrap, no login): `public.spec.ts` 4/4; `guardrails.spec.ts` 1/1; generation journeys TS-024 (keyboard full flow incl. download) and TS-025 pass on the fake-adapter stack; TS-026 passed in batch but its fault-injection flavor and TS-028's small-cap flavor require the documented F003 fault backend (unchanged by ADR-0006; re-verified at T8).
- Seed script (pre-change) seeded once and re-ran idempotent on the dev stack.
- Checkpointer (TS-011): lifecycle verification correct (setup idempotent; checkpoints persist across saver instances); deployed-topology investigation found the IF-8 multi-process first-use deadlock and fixed it (entrypoint pre-setup); live journey re-verified.

## Deployed Verification (T8/T9, 2026-09-02 — see deployment-evidence.md)

Full chain executed on the owner machine (LAN 192.168.9.101): build → migrate (+ checkpointer pre-setup) → start → health → smoke PASS; sample seeded + idempotency proven (twice + after redeploy); live DeepSeek recovery journey TS-029 PASS (51.7s, single bounded run); deletion completeness all-zero with content-free ledger surviving; single-process API verified; F011 D10 constraints re-verified on the deployed stores; teardown → clean redeploy → re-seed PASS; accessibility + 420px spot PASS (after IF-9 fix); deployed public/guardrails E2E 5/5.

## Remaining Before DONE

- Delivery: commit/push/PR (each requires separate owner authorization per AGENTS).

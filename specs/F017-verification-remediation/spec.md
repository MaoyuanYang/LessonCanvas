# F017 — Verification Remediation (2026-09-06 pass)

- Spec Status: `SPEC READY`
- Roadmap Status: `REVIEW`
- Work type: documentation / infrastructure / hygiene remediation of the findings recorded in `docs/VERIFICATION.md` (2026-09-06 verification pass). No product behavior changes.
- Change level: L1 per item (see decisions); no ADR required — no module boundary, technology choice, or source-of-truth change.

## Goal

Turn every actionable finding of the 2026-09-06 verification pass (`docs/VERIFICATION.md`, findings 1–9; finding 10 is informational and needs no work) into a repaired, verified state, so the documents and the deployment tooling match reality and the documented promises hold.

## Acceptance Criteria

1. **AC-1 (finding 1)**: `infra/docker-compose.yml` gives postgres/redis/minio `restart: unless-stopped` (same policy the `app`-profile services already use), so a host reboot no longer leaves the deployed API crash-looping on missing infra; README/AGENTS infra-start lines mention auto-restart.
2. **AC-2 (finding 2)**: README (dev quickstart) and `docs/TESTING.md` (environment notes) document that on a machine that also runs the deployed stack, infra services must be started with `docker compose -f infra/docker-compose.yml --env-file infra/deploy.env up -d`, and why the plain form silently recreates postgres/minio with fallback dev credentials; the local untracked `apps/backend/.env` is refreshed to the deployed-stack credentials (Phase-2 §5.2.5 owner-side item) so `uv run pytest` runs bare again, and the TESTING note is updated accordingly.
3. **AC-3 (finding 3)**: a deterministic CI workflow (`.github/workflows/ci.yml`) runs the documented gates — backend `ruff` + `pytest` against pgvector/MinIO service containers with the fake adapter, web `test`/`lint`/`typecheck`/`build` — with no live-model work and no secrets; `docs/TESTING.md`, `README.md`, and `AGENTS.md` reference it so the CI statements are true.
4. **AC-4 (finding 4)**: `docs/FRONTEND.md` no longer claims React Hook Form + Zod; the F001 library record is corrected to what shipped (hand-rolled controlled forms), with the correction dated.
5. **AC-5 (finding 5)**: `specs/F001-grounded-confirmed-brief/spec.md` and `specs/F011-public-multi-account-guardrails/spec.md` headers read `Roadmap Status: DONE`.
6. **AC-6 (finding 6)**: `STAGE.md` is reconciled to a new snapshot revision reflecting F001–F016 DONE with current suite counts and the deployed-stack state.
7. **AC-7 (finding 7)**: README's `deploy.sh` one-liner names the actual six-step chain.
8. **AC-8 (finding 8)**: `apps/web/s2.txt` is deleted from the worktree.
9. **AC-9 (finding 9)**: the Celery worker run command appears in the README and `docs/TESTING.md` command blocks alongside AGENTS.

## Decisions

- Remediation is tracked as one roadmap work item (F017) with this brief change record — one observable outcome per finding, no unresolved user-owned questions; no per-item specs or plans (skill scaling rule).
- AC-1 uses `restart: unless-stopped` (not `always`): it matches the app-profile policy, survives daemon/host restarts, and still honors an explicit `docker compose stop`.
- AC-2 fixes the hazard by documentation rather than removing the compose credential fallbacks: the fallback is required by the documented fresh-clone dev path, and compose cannot fail closed on "deploy.env exists but was not passed". The stale local `apps/backend/.env` is refreshed (untracked, machine-local) because Phase-2 already recorded that refresh as the intended owner-side fix that removes the pytest override dance. Enabling change in `tests/conftest.py`: an explicitly exported `LESSONCANVAS_DATABASE_URL` is honored verbatim (CI / overrides, unchanged); otherwise the test URL is derived from the effective settings (shell env or `apps/backend/.env`) with only the database name swapped onto `lessoncanvas_test` — previously the conftest hardcoded the dev-only password into an env var that outranked `.env`, so a bare `uv run pytest` could not use refreshed credentials. Fresh clones without `.env` keep the exact previous defaults.
- AC-3 adds CI (rather than rewording docs to drop CI) because the documents already describe deterministic CI as an intended environment, and the deterministic gates are exactly the local commands; live-model evaluation stays out per the documented separation (AGENTS build-and-test rules). No secrets: fake adapter + dev-only service credentials.
- Verification evidence is a fresh full local run of the documented gates after the changes (the CI workflow itself is validated by config sanity plus the identical local commands it wraps).

## Test Design

No new product tests — no behavior changed. Verification = the existing documented suites re-run green after the changes:

- `uv run pytest` (bare, post-`.env` refresh and conftest derivation) and `uv run ruff check src tests migrations` — expect 622 passed + 4 skipped / clean.
- `corepack pnpm web:test` / `web:lint` / `web:typecheck` / `web:build` — expect 122/122, 0 errors (3 known warnings), clean, exit 0.
- `docker compose -f infra/docker-compose.yml config` parses and shows the restart policies; the live infra containers pick up the policy (recreate with `--env-file infra/deploy.env`).
- `.github/workflows/ci.yml` parses as valid YAML and its steps mirror the documented commands exactly.

## Plan

Single batch (docs + config + hygiene in one change record): AC-1 → AC-9 in dependency order (compose + CI first, then docs, then hygiene), then the full verification above, then DONE record + Roadmap sync.

## Gate Record: REVIEW (2026-09-06)

Implementation complete in the worktree (uncommitted — commit/push/PR need separate owner authorization per AGENTS.md). Every AC verified:

- AC-1: `infra/docker-compose.yml` postgres/redis/minio now `restart: unless-stopped`; live containers recreated with the policy and healthy; README/AGENTS mention auto-restart.
- AC-2: README Start section + TESTING.md Services line + AGENTS Start line document the `--env-file infra/deploy.env` requirement and why; local untracked `apps/backend/.env` refreshed (DATABASE_URL/S3 secret/DeepSeek key, mode 600); `tests/conftest.py` now honors an explicit `LESSONCANVAS_DATABASE_URL` verbatim and otherwise derives the test URL from effective settings with only the DB name swapped to `lessoncanvas_test`; bare `uv run pytest` verified.
- AC-3: `.github/workflows/ci.yml` added (backend ruff+pytest on pgvector+MinIO service containers, web test/lint/typecheck/build; no secrets, no live model, fake adapter); README Test section, AGENTS Build and Test block, TESTING.md Environments + Commands reference it.
- AC-4: `docs/FRONTEND.md` F001 library record corrected with a dated correction note.
- AC-5: F001/F011 spec headers read `Roadmap Status: DONE`.
- AC-6: `STAGE.md` reconciled to `STAGE-84`.
- AC-7: README/TESTING/AGENTS `deploy.sh` one-liners name the six-step chain.
- AC-8: `apps/web/s2.txt` deleted.
- AC-9: Celery worker command present in README Build, TESTING.md Commands, and AGENTS (all three kept in sync).

Verification evidence (2026-09-06, this session): bare `uv run pytest` **622 passed + 4 skipped, exit 0**; `ruff` clean; Vitest **122/122**; `tsc` clean; ESLint **0 errors, 3 pre-existing warnings**; `web:build` exit 0; `docker compose config` valid; CI YAML parses and mirrors the exact local commands that passed; deployed smoke (`smoke.sh`) green after the container recreate. (One intermediate bare run showed 1 failed + 1 error caused by recreating postgres/minio containers while the suite was running — a session-inflicted timing collision, not a regression; the clean re-run is 622+4.)

Residuals: none from the finding list; finding 10 was informational (orphan :3000 container already gone). F010 real-teacher evidence and the public-exposure deployment feature remain the standing owner-decision items recorded in `docs/VERIFICATION.md` (Not Exercised) — outside F017 scope.

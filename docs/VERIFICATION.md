# Verification Report

Verification pass of 2026-09-06, from commit `b818b15` (main, clean worktree), executed by
the `project-verify` skill with owner-approved scope: full deterministic suites, full
fault-stack E2E set, deployed-stack restore + read-only verification, and one real-DeepSeek
live journey. Documents read: `README.md`, `AGENTS.md`, `docs/PRODUCT.md`, `ARCHITECTURE.md`,
`TESTING.md`, `DATABASE.md`, `API.md`, `FRONTEND.md`, `UX.md`, `UI.md`, `DESIGN_SYSTEM.md`,
`specs/ROADMAP.md`, and the specs/evidence of all sixteen DONE features (F001–F016).

Result labels: **Verified** — executable evidence exists and passes. **Broken** — evidence
exists and shows the promise is false. **Unverified** — no executable evidence could be
produced in this pass.

## Verified Promises

| Promise (source) | Evidence | Result |
| --- | --- | --- |
| Backend suite passes (`README.md:80`, `TESTING.md:69`) | `uv run pytest` with deploy.env credential overrides against isolated `lessoncanvas_test`: **622 passed + 4 skipped, exit 0** — identical to the Phase-2 baseline (see Finding 2 for a first-run 281-failure environment incident) | Verified |
| Backend lint clean (`README.md:84`) | `uv run ruff check src tests migrations` — all checks passed | Verified |
| Web component tests (`README.md:85`) | `corepack pnpm web:test` — **122/122**, 18 files | Verified |
| Web typecheck (`README.md:87`) | `corepack pnpm web:typecheck` — exit 0 | Verified |
| Web lint (`README.md:86`) | `corepack pnpm web:lint` — 0 errors, 3 pre-existing warnings | Verified |
| Web production build (`README.md:76`) | `corepack pnpm web:build` — exit 0 | Verified |
| Dependency audits clean (`TESTING.md:61`) | `uv audit` — no vulnerabilities (107 packages); `corepack pnpm audit` — no vulnerabilities (workspace overrides active) | Verified |
| Tracked-tree credential scan clean (`TESTING.md:61`) | Only `.env.example` files tracked; `deploy.env`/`.env` untracked; key-pattern grep over tracked files clean; the one deploy.env value found in `specs/PHASE2-retrospective.md` is the LAN URL `LESSONCANVAS_WEB_API_BASE_URL`, not a credential | Verified |
| Documented migrations exist (`docs/DATABASE.md:76-89`) | All 14 documented revision ids present in `apps/backend/migrations/versions/` (21 files total); `lessoncanvas_test`/`lessoncanvas_e2e` both upgrade to head cleanly | Verified |
| Roadmap: all 16 features DONE (`specs/ROADMAP.md:25-42`) | Every delivery merge SHA (PRs #2–#33) confirmed in main history; each spec carries its DONE Gate Record | Verified |
| Per-feature acceptance evidence (F001–F016 specs) | Spec ACs → `review.md` evidence tables → `test-design.md` execution snapshots → on-disk suites (run in this pass) all align; committed evidence artifacts present and internally consistent: F009 (`live-evidence.json` 64 KB, `worker-recovery-evidence.json`), F012 (`deployment-evidence.md`, 14/14 PASS rows), F013–F016 (`live-evidence.json` + live runners) | Verified |
| API surface matches `docs/API.md` | Deployed OpenAPI: 82 paths covering every documented family (auth, sample, brief/blueprint, generation ×3, evidence, impact/versions, alignment/delivery, technical/product evaluation, memory, account usage/audit, sources/analyze); legacy `GET /projects/{id}/trace` absent (removed as documented) | Verified |
| Modules match `docs/ARCHITECTURE.md` | All nine documented modules exist under `apps/backend/src/lessoncanvas/modules/` | Verified |
| Deployed stack healthy and reviewer-reachable (`README.md:62`, F012) | After restore: all six services `(healthy)`; `smoke.sh` passed (`/health` → `{"status":"ok","database":"ok"}`, web 200); `POST /auth/guest-token` issues a workspace; `GET /sample` returns the seeded project (作品集示例：Travelling Around); evidence inventory shows all five run kinds; web `/sample` renders (HTTP 200) — but the stack was **down at pass start** (Finding 1) | Verified (with Finding 1) |
| F010 honest product-validation split (`docs/PRODUCT.md`, F010) | Deployed sample `GET /product-validation` → `overall_status: not_evaluated` with the bounded-conclusion text, separate from technical evaluation | Verified (capability; real-teacher evidence remains absent — see Not Exercised) |
| Fault injection impossible in production configs (`TESTING.md:61`) | `apps/backend/src/lessoncanvas/adapters/model.py:247` raises unless `model_adapter == "fake"` | Verified |
| Fault-stack E2E families (`TESTING.md:85`) | All 15 gated families + 3 TS-028 cap-exhaustion journeys + deployed public/guardrails, fresh fake-API + `next dev` per family on ports 8010/3100 per the documented method: **32 passed, 0 failed, 10 live-gated skipped** | Verified |
| Live-model journey (`TESTING.md:40`) | TS-029 through the deployed stack (real DeepSeek + real Celery worker + real MinIO): **1 passed (1.3m)** — leave/reconnect/reload recovery, DOCX download, project cleanup; parity with the Phase-2 record | Verified |
| Deterministic/live separation (`TESTING.md:83`) | pytest conftest forces fake adapter + eager tasks; all live journeys env-gated and skipped by default (10 skipped in this pass) | Verified |

## Findings

| # | Finding | Evidence | Affected document / spec | Severity | Recommended next work |
| --- | --- | --- | --- | --- | --- |
| 1 | The deployed portfolio stack was **down when verification began**: postgres/redis/minio `Exited (0)` ~3 h earlier, `infra-api-1` crash-looping (`failed to resolve host 'postgres'`), worker restart-looping, web healthy but isolated on :3002. The F012 promise of a standing, reviewer-reachable stack did not hold at that moment. Recovered during this pass with documented commands; all services healthy again. Why the infra containers stopped is not recorded (clean exits). | `docker ps -a` + `docker logs infra-api-1` at pass start; recovery sequence in this report | F012 spec D-series; `README.md:62` | High | Owner-side: record/automate the stop-start habit (e.g. host reboot behavior, `restart: unless-stopped` covers app profile but infra services were explicitly stopped) or add an uptime watchdog note to the demo workflow |
| 2 | The documented dev-start command silently recreates infra containers with **fallback credentials**: `docker compose -f infra/docker-compose.yml up -d` (`README.md:45`, `AGENTS.md:49`, `TESTING.md:74`) does not load `infra/deploy.env`. In this pass it recreated MinIO with `MINIO_ROOT_PASSWORD=lessoncanvas_dev_only` while the deployed api/worker still hold the real deploy.env password — deployed S3 writes break silently (healthcheck stays green), and the documented pytest run fails wholesale (first run: **281 failed** on `SignatureDoesNotMatch`/MinIO) until containers are recreated with `--env-file infra/deploy.env` (the deploy.sh form). Postgres is unaffected in practice (persisted volume keeps the real password). | `/tmp` pytest logs run 1 (281 failed) vs run 2 (622+4) after `docker compose --env-file infra/deploy.env up -d postgres minio redis`; compose interpolation defaults in `infra/docker-compose.yml:6,33` | `README.md:45`, `AGENTS.md:49`, `docs/TESTING.md:74` | High | project-dev: document the interaction (on machines with the deployed stack, start infra services with `--env-file infra/deploy.env`), or remove the credential fallbacks once a deployed env exists so misconfiguration fails closed |
| 3 | CI does not exist, but documents speak in CI terms: `docs/TESTING.md:49` ("Environments: local, CI, …"), `TESTING.md:57` ("never as a CI gate"), `AGENTS.md:76`. No `.github/` or other CI config has ever existed in the repo. All quality gates are local/manual. | Repo has no `.github/` directory; `git log --all -- .github` empty | `docs/TESTING.md`, `AGENTS.md` | Medium | Either add the deterministic CI workflow (pytest/ruff/vitest/lint/tsc on push) or reword docs to "local gates" so the promise matches reality |
| 4 | `docs/FRONTEND.md:85` records F001's frontend library selection as "React Hook Form + Zod (forms/validation)", but neither package exists in `apps/web/package.json`; forms are hand-rolled controlled components. The documented decision drifted silently during implementation. | `grep -i zod apps/web/package.json` empty; `docs/FRONTEND.md:85` | `docs/FRONTEND.md` | Medium | project-dev documentation sync: correct the F001 library record (or record the superseding decision) |
| 5 | Two spec headers contradict the authoritative Roadmap: `specs/F001-grounded-confirmed-brief/spec.md:4` and `specs/F011-public-multi-account-guardrails/spec.md:4` still read `Roadmap Status: NEXT` while ROADMAP and their own DONE Gate Records say DONE (F002+ headers are correct). | Header lines vs `specs/ROADMAP.md` feature map | F001/F011 specs | Low | project-dev: flip both headers to `DONE` |
| 6 | `STAGE.md` is stale at STAGE-83 (pre-F014; snapshot says F001–F013 with 515+4 backend counts vs current 622+4). Already flagged in PHASE2-retrospective §4.3; still unreconciled. | `STAGE.md` header vs `README.md:37-39` | `STAGE.md` | Low | Reconcile at the next session that owns the file |
| 7 | `README.md:55` describes `deploy.sh` as "build -> migrate -> start -> smoke"; the executed chain is six steps (build → start with entrypoint migration → health-wait → embedding backfill → source-analysis backfill → smoke). | `infra/scripts/deploy.sh` steps vs README line | `README.md` | Low | Update the one-line description to match the six-step chain |
| 8 | `apps/web/s2.txt` is a committed Playwright accessibility-tree YAML snapshot (F004-era debugging leftover, tracked since `e425379`). | `git log --oneline -1 -- apps/web/s2.txt`; file content | repo hygiene | Low | Remove the file |
| 9 | The Celery worker run command (`uv run celery -A lessoncanvas.worker.celery_app worker`) appears only in `AGENTS.md:57`; README and TESTING.md omit it, though `TESTING.md:87` requires the three command blocks to change together. | Command-block comparison across the three documents | `README.md`, `docs/TESTING.md` | Low | Add the worker command to the README/TESTING command blocks |
| 10 | Positive delta: the orphaned pre-F013 web container on host port :3000 (PHASE2-retrospective §4.2) no longer exists; the deployed web is cleanly on :3002 via `LESSONCANVAS_WEB_PORT`. | `docker ps -a` shows only the six compose services | — | Low (informational) | None — residual §4.2 can be closed in the next retrospective |

No product-code defects were found: every behavioral promise that could be executed in
this pass held, and the two High findings are operational/documentation failures, not
product failures.

## Not Exercised

| Promise | Why not exercised this pass | What would check it |
| --- | --- | --- |
| F010 real-teacher rubric evaluation evidence | Owner-decision residual carried since Phase 1: external teacher reviews were never produced/imported; runtime honestly shows 未评估 | Produce and import the teacher evidence per the F010 Test Design snapshot-append procedure |
| Live E2E families beyond TS-029 (deck/exercise/evidence/regeneration `E2E_*_LIVE`, 10 skipped tests) | Live gates intentionally excluded except the one owner-approved journey; each costs real DeepSeek tokens | Run each gated live family against the deployed stack as in Phase-2 close-out |
| F013–F016 live runners (memory proposal passes, tool-loop live probe, specialist live journey + F009 six-pass re-baseline) | Same cost boundary; committed evidence files verified present and internally consistent instead | Re-run the respective `specs/F01x-*/live-runner.py` with owner authorization |
| `deploy.sh` full six-step rebuild chain | Owner chose restore + verify (no rebuild); the chain was validated read-only via smoke + F012 evidence | Owner-authorized `infra/scripts/deploy.sh` execution |
| `seed_sample.py` idempotent re-run | Sample verified present and readable; re-seeding unnecessary | Run the documented seed command on a fresh stack |
| Public cloud/region/internet exposure (F012 D1) | Documented as an open residual; explicitly out of scope | A future deployment feature |

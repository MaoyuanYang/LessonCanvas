# Phase-2 Retrospective

| Field | Value |
| --- | --- |
| Scope | Holistic close-out of the complete two-phase system: layered full-stack re-verification (Phase 1 F001–F013 + Phase 2 F014–F016), delivery-completeness and evidence audit, open-residual inventory, documentation-sync check |
| Date | 2026-09-04 |
| Executed by | Agent (ZCode) under `YMY / Project Owner` instruction; owner pre-approved the layered plan including the deployed rebuild and one live-model journey. `deploy.sh` itself was executed by the owner in their own terminal (see §1 environment note) and its log verified by the agent |
| Baseline compared against | F016 delivery verification on `main` @ `f096042` merge / `962db21` (backend 622 passed + 4 skipped + ruff clean; web 122/122 + tsc clean + eslint 0 errors) |
| Working tree at review time | `main` @ `962db21`, clean at start; review fixes left uncommitted pending owner authorization |

## 1. Verification Method and Environment

Layered verification, cheapest-first, mirroring `docs/TESTING.md` and the Phase-1 close-out:

1. **Deterministic suites** — backend `uv run pytest` + `uv run ruff check`; web Vitest + ESLint + `tsc --noEmit` + `next build`; plus `uv audit`, `pnpm audit`, and a tracked-tree credential-pattern scan (F011 precedent).
2. **Fault-stack E2E** — fake-adapter API instances (eager tasks, `LESSONCANVAS_MODEL_ADAPTER=fake`) against the isolated `lessoncanvas_e2e` database and dedicated MinIO buckets (`lessoncanvas-{sources,artifacts}-e2e`), Playwright chromium, serial workers, web served from `next dev` on free ports (API 8010/8011/8012/8013, web 3100/3101/3102/3103), a fresh fake instance before every gated family (one-shot fault-marker contract), and separately configured small-cap instances for the three TS-028 cap-exhaustion journeys.
3. **Deployed stack** — `infra/scripts/deploy.sh` full six-step chain, `smoke.sh`, idempotency re-runs of the source-analysis backfill and sample seeding, deployed public/guardrails E2E.
4. **Live model** — one representative live journey (TS-029) through the freshly rebuilt deployed stack (real DeepSeek + real Celery worker).

Environment notes:

- The F012-era deployed stack was still running on the default ports at review start; PostgreSQL/Redis/MinIO belong to it, so all local runs used `infra/deploy.env` credentials while touching only the isolated `lessoncanvas_test` / `lessoncanvas_e2e` databases (F016 pattern; `apps/backend/.env` remains stale against the deployed stack).
- The docker group membership lost 2026-09-01 (F016 record) was restored during this review (`docker:x:983:ymy`). The agent's own session process tree carries `NoNewPrivs=1` and cannot elevate or change groups (sudo/su/sg all refused), so the rebuild chain was executed by the owner in their terminal (`sg docker -c 'bash infra/scripts/deploy.sh'`, log at `/tmp/lessoncanvas-deploy-phase2.log`) and verified externally by the agent (log, `/health`, OpenAPI surface, backfill re-runs, deployed E2E).
- Deployed web serves on host port 3002 (`LESSONCANVAS_WEB_PORT` in deploy.env); the API bakes `http://192.168.9.101:8000` into the web image. Deployed E2E used `http://localhost:3002` as the browser origin (CORS-allowed) against the deployed API.

## 2. Verification Results

| Layer | Command / Gate | Result | vs Delivery Baseline |
| --- | --- | --- | --- |
| Backend unit/integration/API-contract | `uv run pytest` (deploy.env overrides, `lessoncanvas_test`) | **622 passed + 4 skipped**, exit 0 | Identical (622+4) |
| Backend lint | `uv run ruff check src tests migrations` | **All checks passed** | Identical |
| Web component tests | `corepack pnpm web:test` | **122/122** (18 files) | Identical |
| Web lint | `corepack pnpm web:lint` | **0 errors, 3 warnings** (pre-existing unused-var warnings) | Identical |
| Web typecheck | `corepack pnpm web:typecheck` | **Clean** | Identical |
| Web production build | `corepack pnpm web:build` | **Success** (default env) | Identical |
| Dependency audit | `uv audit` / `pnpm audit` | **0 known vulnerabilities** (106 backend packages; workspace overrides active) | Consistent with F011 record |
| Credential scan | tracked-tree pattern scan (`sk-…`, key literals, private-key blocks) | **No matches** | Consistent |
| E2E public + guardrails (ungated, fake stack) | `public.spec.ts` + `guardrails.spec.ts`, serial | **5/5** | Consistent |
| E2E generation fault (`E2E_GEN_FAULT=1`) | TS-024/025/026 | **3/3** (14.0s; fresh instance) | Consistent |
| E2E deck fault (`E2E_DECK_FAULT=1`) | TS-024/025/026(deck) | **3/3** (17.4s; fresh instance) | Consistent |
| E2E exercise fault (`E2E_EXERCISE_FAULT=1`) | TS-024/025/026(exercise) | **3/3** (18.7s; fresh instance) | Consistent |
| E2E regeneration fault (`E2E_REGEN_FAULT=1`) | TS-014 + TS-016 | **2/2** (15.2s) | Consistent |
| E2E evidence fault (`E2E_EVID_FAULT=1`) | TS-020a/TS-020/TS-022 | **3/3** (14.2s) | Consistent |
| E2E alignment fault (`E2E_ALIGN_FAULT=1`) | TS-016 + TS-017 | **2/2** (13.9s) | Consistent |
| E2E evaluation fault (`E2E_EVAL_FAULT=1`) | evaluation + product-validation specs | **2/2** (8.6s) | Consistent |
| E2E memory fault (`E2E_MEM_FAULT=1`) | TS-023/TS-024/TS-025 | **3/3** (55.9s) | Consistent |
| E2E retrieval (`E2E_RETRIEVAL=1`, F014) | TS-025(retrieval) | **1/1** (35.9s) | Consistent with F014 record |
| E2E tool-loop (`E2E_TOOL_LOOP=1`, F015) | TS-020(tool) | **1/1** (34.9s) | Consistent with F015 record |
| E2E specialist stages (`E2E_SPECIALIST_STAGES=1`, F016) | TS-021 | **1/1** (36.0s) | Consistent with F016 record |
| E2E cap exhaustion, plans | TS-028, dedicated instance (cap 17: floor `MAX_MODEL_CALLS_PER_RUN=17`, zeroed formula) | **1/1** (6.9s) | **First post-F016 execution under the formula-cap regime** (see §4.1) |
| E2E cap exhaustion, decks | TS-028(deck), dedicated instance (cap 2: `MAX_MODEL_CALLS_PER_DECK_RUN=2`, zeroed formula) | **1/1** (7.1s) | First post-F016 execution; deck journey completes plans on the same instance first |
| E2E cap exhaustion, exercises | TS-028(exercise), dedicated instance (cap 2) | **1/1** (6.9s) | First post-F016 execution |
| Deployed stack | `deploy.sh` [1/6]–[6/6] | **Full chain PASS** (owner-executed, log verified); first real deployment of F013–F016 code; migrations via api entrypoint; all six services healthy | New: Phase-2 code now actually deployed |
| Embedding backfill (F014, step 4/6) | in-container | `embedded=0 failed=0 hashes_filled=0` (all embeddings already present — idempotent no-op) | Consistent with F014 design |
| Source-analysis backfill (F016, step 5/6) | in-container, then local re-run | **14 analyzed, 0 failed** on first run (real bounded one-call-per-source analyses of pre-F016 sources); re-run **0 analyzed, 14 skipped** — idempotent | New: F016 backfill executed real work and is idempotent |
| Sample seeding | `scripts/seed_sample.py` against deployed DB | **Idempotent** (`already_present: true`) | Consistent |
| Deployed E2E | public + guardrails against deployed web :3002 / API :8000 | **5/5** (934ms) | Consistent |
| Live model | TS-029 generation live journey through the rebuilt deployed stack (real DeepSeek + real worker) | **1/1 (1.5m)** — leave/reconnect/reload restored authoritative progress; journey cleans up its project | Consistent with F012/F016 live records; now under the full Phase-2 stage set |

**Aggregate: 32 local fault-stack journeys + 5 deployed + 1 live = 38 journeys green, 0 failed, 0 flakes observed** (13 live-gated browser tests intentionally skipped in fault stacks per the deterministic/live separation). Live-model cost: one 6-lesson planning + generation run plus its memory-proposal triggers (≈$0.01–0.05, within the recorded F009 per-unit range); the journey deletes its project on cleanup, so the per-run cost record is intentionally purged with the workspace (user-owned trace boundary).

## 3. Delivery Completeness (F001–F016)

- All sixteen Features are `DONE` in `specs/ROADMAP.md` with Gate records binding artifact revisions; PRs #2–#33 merged; every delivery re-verified on `main` at its time.
- Phase-2 evidence files verified present: F014 `live-evidence.json` (2026-09-03), F015 `live-evidence.json` (2026-09-04), F016 `live-evidence.json` (2026-09-04, real-DeepSeek specialist journey + full F009 six-pass re-baseline under the new stage-set signature).
- Code-level debt markers: zero `TODO/FIXME/HACK/XXX` matches in `apps/backend/src`, `apps/backend/tests`, `apps/backend/migrations`, and `apps/web` source.
- ADRs 0001–0007 all `Accepted`, none superseded.
- The deployed stack now runs the same code as `main` (verified by the `/memory` endpoint family and both F016 backfill steps executing in-container).

## 4. Findings From This Review

**No product code defects were found.** All findings below are documentation or harness-level.

### 4.1 The documented TS-028 small-cap configuration was stale under F016 formula caps — FIXED (documentation)

`docs/TESTING.md` still instructed cap-exhaustion instances with `LESSONCANVAS_MAX_MODEL_CALLS_PER_RUN=3`, `..._PER_DECK_RUN=1`, `..._PER_EXERCISE_RUN=1`. Under F016, per-run caps are `max(family floor, per-lesson formula + slack)` (`run_orchestration/caps.py`): those settings only raise the floor, and the 6-lesson journey unit needs 18 plan stage calls, so `floor=3, formula=5×6+2=32` yields cap 32 — the journey would complete without ever exhausting. The three TS-028 journeys had never been re-run under the F016 stage set until this review. **Fix:** the operational note now documents the verified working configuration — zero the formula (`LESSONCANVAS_MODEL_CALL_CAP_*_PER_LESSON=0`, `LESSONCANVAS_MODEL_CALL_CAP_SLACK=0`) and set the family floor below the full-run stage count but at or above the planning-run budget (plans floor 17 → cap 17 < 18, exhausting at the lesson-6 review; decks/exercises floor 2 → lesson 1 completes then exhausts). All three journeys pass under it (§2). The planning caveat matters because the discovery run checks the raw `max_model_calls_per_run` setting (`discovery_planning/graph.py`), so the plans floor cannot be lowered arbitrarily.

### 4.2 Deployed-stack hygiene: an orphaned F012-era web container still listens on host port 3000

`deploy.env` maps the current web to host port 3002, but port 3000 also serves HTTP 200 from an older web container that survived the rebuild (it no longer matches the current compose mapping). It serves a stale image and may bake an outdated API origin. Owner-side cleanup candidate: remove the orphaned container (the agent session cannot run docker, §1). Not a product defect; recorded so the portfolio does not accidentally demo through the stale port.

### 4.3 `STAGE.md` is stale at STAGE-83 (pre-F014)

`STAGE.md` still records F013 as the latest milestone (`main @ 66a0b6c`, reconciled 2026-09-03). It is a session-coordination artifact of the feature-dev workflow rather than a document owned by the Documentation Rules; it was deliberately **not** rewritten by this review to avoid corrupting its revision/hash-guard conventions. Recorded as a small follow-up for the next feature-dev/onboard session that owns the file.

### 4.4 Harness lessons (environment/tooling, not product)

- Sourcing `infra/deploy.env` with bash mangles the JSON `LESSONCANVAS_CORS_ALLOWED_ORIGINS` value (quote removal), which surfaces as a pydantic `SettingsError` at collection. Extract only the needed scalars (e.g. `grep | cut`) instead of `source`ing the file.
- Piping `pytest` through `tail` swallows its exit code; capture the log to a file and echo `$?` explicitly.
- Killing the `pnpm dev` wrapper leaves the `next dev` node child running (four stray dev servers survived the orchestrator's cleanup). Kill by process pattern, and verify with `pgrep` afterwards.

## 5. Open Residual Inventory (Phase-2 close-out list)

### 5.1 Owner-decision items (carried from Phase-1 close-out, unchanged)

1. **F010 real-teacher review import** — the external teacher's rubric reviews have never been produced/imported; runtime honestly shows 未评估. Import path and snapshot-append procedure are specified in the F010 Test Design.
2. **Public cloud/region/domain/TLS exposure deployment Feature** — the sole named follow-up Feature (F012 D1 residual); hosted object-store deletion guarantees also fold in here.
3. **Zod-vs-hand-written-interfaces DTO convention** (F006 M-3, echoed F007 L-3) — still deferred.

### 5.2 Small engineering/owner-side follow-ups

4. ~~Docker group membership~~ — **restored 2026-09-04 during this review** (owner action); recorded here because the agent session itself cannot elevate (`NoNewPrivs`), so any in-session docker need must go through the owner's terminal.
5. `apps/backend/.env` credentials remain stale against the deployed stack (owner-side refresh candidate; all verification used deploy.env overrides successfully).
6. Remove the orphaned pre-F013 web container on host port 3000 (§4.2).
7. `STAGE.md` stale at STAGE-83 (§4.3); reconcile at the next session that owns the file.
8. F009 M-3 — deck/exercise graphs still use the legacy truncated-JSON classification (carried from Phase-1).
9. E2E helper re-render race hardening remains open (carried; no flake observed in this pass — all 38 journeys first-try green under `next dev`).

### 5.3 Accepted constraints to keep disclosing (no action)

- Single-process API by design (in-process SSE registry); scale-out must re-verify (F011 M-2).
- Student-data screening evasion boundary (F001 TQ-3 / F011 L-1).
- Print/report output relies on the browser engine (F008 L-1).
- Rate counters count rejected attempts (F011 L-2, by design).
- pnpm workspace overrides raise postcss/sharp above Next.js pins; re-verify at the next Next.js upgrade (F011 L-3).

## 6. Honest Validation Status (Phase-2 close)

- **Technical portfolio validation**: evidenced and reproducible — F009 live six-pass re-baseline under the full Phase-2 signature (`retrieval_mode` + `tool_mode` + `stage_set`, F016 delivery), and this review's four-layer re-verification of the assembled two-phase system including the first real deployment of Phase-2 code and a live end-to-end journey through it.
- **Teacher product validation**: **capability delivered, evaluation not complete** — unchanged from Phase-1 close-out. The rubric/import workflow works and is tested, but no real-teacher evidence exists yet; the runtime continues to display 未评估 rather than claiming success. Both statuses remain separately visible.

## 7. Documentation Sync Check and Fixes Applied

Checked `README.md`, `docs/` (incl. `TESTING.md`, `PRODUCT.md`), ADRs 0001–0007, `specs/ROADMAP.md`, and `STAGE.md` against the F016-DONE + both-phases-complete state. Three stale spots found and fixed in this review (no product code changes):

1. `README.md` "Current Stage" — still described Phase 1 only ("all thirteen Features F001–F013"). **Fixed**: now records F001–F016 across both phases, the Phase-2 close-out retrospective, and "none remaining in either Feature Map".
2. `specs/ROADMAP.md` Handoff — heading still read "Current: F016 DONE". **Fixed**: demoted to "Previous" and a new "Current: Phase-2 close-out complete" section added summarizing this review.
3. `docs/TESTING.md` E2E operational notes — TS-028 small-cap instance configuration stale under F016 formula caps (§4.1). **Fixed** with the verified working configuration.

`STAGE.md` staleness is recorded (§4.3) rather than fixed, by the ownership reasoning given there. `docs/PRODUCT.md` open items re-checked: no Phase-2 staleness (the F009/F010 items were already resolved at Phase-1 close-out; the cloud-deployment item remains correctly `PARTIALLY RESOLVED`).

## 8. Overall Conclusion

The two-phase system is delivered, internally consistent, and now actually deployed: every deterministic suite matches the F016 baseline exactly, all 15 fault-stack E2E suites (including the three Phase-2 gates and the three cap-exhaustion journeys re-baselined under the F016 formula-cap regime) plus the deployed public/guardrails journeys are green with zero flakes, the deploy chain rebuilt the stack on current `main` with both idempotent backfills behaving as designed (14 real source analyses backfilled), and a live DeepSeek journey through the rebuilt stack recovers authoritative progress across leave/reconnect/reload. No product defects were found; the review's three fixes are documentation-level and are left uncommitted in the working tree pending owner authorization. The genuine gaps remain the ones the project names honestly: no real-teacher product-validation evidence yet, no public-internet deployment, and a short recorded list of owner-side and small engineering follow-ups (§5).

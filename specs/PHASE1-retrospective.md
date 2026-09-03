# Phase-1 Retrospective

| Field | Value |
| --- | --- |
| Scope | Holistic Phase-1 close-out review: full-stack re-verification of the delivered system (F001–F013), delivery-completeness and evidence audit, open-residual inventory, documentation-sync check |
| Date | 2026-09-03 |
| Executed by | Agent (ZCode) under `YMY / Project Owner` instruction; live-model and deployment actions pre-authorized in the approved review plan |
| Baseline compared against | F013 delivery verification on `main` @ `93ae3ac` (backend 515 passed + 4 skipped + ruff clean; web 108/108 + tsc clean + eslint 0 errors) |
| Working tree at review time | `main` @ `93ae3ac`, clean |

## 1. Verification Method and Environment

Layered verification, cheapest-first, mirroring `docs/TESTING.md`:

1. **Deterministic suites** — backend `uv run pytest` + `uv run ruff check`; web Vitest + ESLint + `tsc --noEmit` + `next build`.
2. **Fault-stack E2E** — fake-adapter API instances (eager tasks, `LESSONCANVAS_MODEL_ADAPTER=fake`) against an isolated `lessoncanvas_e2e` database and dedicated MinIO buckets, Playwright chromium, serial workers, web served from `next dev` (matching the recorded F013 execution profile).
3. **Deployed stack** — `infra/scripts/deploy.sh` full chain, `smoke.sh`, idempotent sample seeding, deployed public/guardrails E2E.
4. **Live model** — one representative live journey (TS-029) through the freshly deployed stack (real DeepSeek + real Celery Worker).

Environment notes: the F012 deployed stack was already running and healthy; PostgreSQL/Redis/MinIO on the default dev ports belong to that stack, so the deterministic suite and the E2E instances ran with the deployed-stack credentials from `infra/deploy.env` (test code touches only the separate `lessoncanvas_test` / `lessoncanvas_e2e` databases). The deployed stack was rebuilt by `deploy.sh` during layer 3; volumes were preserved (no teardown).

## 2. Verification Results

| Layer | Command / Gate | Result | vs Delivery Baseline |
| --- | --- | --- | --- |
| Backend unit/integration/API-contract | `uv run pytest` | **515 passed + 4 skipped**, exit 0 | Identical (515+4) |
| Backend lint | `uv run ruff check src tests migrations` | **All checks passed** | Identical |
| Web component tests | `corepack pnpm web:test` | **108/108** (16 files) | Identical |
| Web lint | `corepack pnpm web:lint` | **0 errors, 3 warnings** (pre-existing unused-var warnings) | Identical |
| Web typecheck | `corepack pnpm web:typecheck` | **Clean** | Identical |
| Web production build | `corepack pnpm web:build` | **Success** (default env) | Identical |
| E2E public + guardrails (ungated) | production build, then deployed stack | **5/5** | Consistent with F012/F013 records |
| E2E generation fault (`E2E_GEN_FAULT=1`) | TS-024/025/026 + TS-028 (small-cap instance) | **4/4** (TS-026 on fresh instance; TS-028 with `LESSONCANVAS_MAX_MODEL_CALLS_PER_RUN=3`) | Consistent |
| E2E deck fault (`E2E_DECK_FAULT=1`) | TS-024/025/026 + TS-028 (deck-cap instance) | **4/4** (TS-026 on first retry) | Consistent |
| E2E exercise fault (`E2E_EXERCISE_FAULT=1`) | TS-024/025/026 + TS-028 (exercise-cap instance) | **4/4** (TS-024 first retry; TS-026 third solo retry) | Consistent |
| E2E regeneration fault (`E2E_REGEN_FAULT=1`) | TS-014 + TS-016 | **2/2** (TS-016 first retry) | Consistent |
| E2E evidence fault (`E2E_EVID_FAULT=1`) | TS-020a/TS-020/TS-022 | **3/3** | Consistent |
| E2E alignment fault (`E2E_ALIGN_FAULT=1`) | TS-016 + TS-017 | **2/2** (TS-017 first retry) | **F008 M-1 resume condition discharged** |
| E2E evaluation fault (`E2E_EVAL_FAULT=1`) | TS-016 (evaluation) + TS-013 (product validation) | evaluation **1/1** (discharges F009 TS-016 resume condition); product-validation TS-013 exposed two latent defects on first true execution — **both fixed in this review; journey green after fix (see §4.1)** | New finding, fixed |
| E2E memory fault (`E2E_MEM_FAULT=1`) | TS-023/TS-024/TS-025 | **3/3** | Identical |
| Deployed stack | `deploy.sh` → health → `smoke.sh` | **Full chain PASS**; api `/health` ok, web HTTP 200 | Consistent with F012 |
| Sample seeding | `scripts/seed_sample.py` (fake adapter + eager) | **Idempotent** (`already_present: true`) | Consistent |
| Deployed E2E | public + guardrails against the deployed web | **5/5** | Consistent |
| Live model | TS-029 generation live journey through the deployed stack (real DeepSeek + real worker) | **1/1 (45.9s)** — interview → brief → blueprint → generation with leave/reconnect/reload restoring authoritative progress | Consistent with F012 TS-029 record |

**E2E aggregate: 28 of 29 attempted journeys green in the review pass; the 29th (F010 TS-013) passed after the fixes below, making it 29 of 29.** (Retry protocol per §4.3.) Live-model cost: one full unit journey; per-unit cost bounded by the recorded F009 live range ($0.0097–$0.0141 per pass). The journey deletes its project on cleanup, so the per-run cost record is intentionally purged with the workspace (user-owned trace boundary, by design).

## 3. Delivery Completeness (F001–F013)

- All thirteen Features are `DONE` in `specs/ROADMAP.md` with Gate records binding artifact revisions; PRs #2–#27 merged; every delivery re-verified on `main` at its time.
- Evidence files verified present: F009 `live-evidence.json` + `worker-recovery-evidence.json` (six live passes: 5 pass / 1 honest fail; real-worker stop/restart resume), F012 `deployment-evidence.md` (14-step operational record), F013 `live-evidence.json` (live proposal quality, dedupe, account-deletion purge).
- **F010 product-validation evidence does not exist** — the honest D9 fallback branch: real-teacher rubric reviews were deferred by the owner; runtime truthfully shows 未评估 until assignments receive imported evidence. This is the largest owner-visible residual (§5.1).
- Code-level debt markers: zero `TODO/FIXME/HACK/XXX` matches in `apps/backend/src`, `apps/backend/tests`, `apps/backend/migrations`, and `apps/web` source.
- ADRs 0001–0006 all `Accepted`, none superseded.

## 4. Findings From This Review (New)

### 4.1 F010 TS-013 E2E journey contained two latent defects (never-run journey) — FIXED in this review

`apps/web/e2e/product-validation-journeys.spec.ts` resolved the assignment row with `getByRole("button").filter({ hasText: "环游世界（英文输出）" }).first()`. Two buttons match: the technical-evaluation result row (above, in DOM order) and the product-validation assignment row. `.first()` clicked the **technical** row, so the expected `绑定包：简报版本` detail never became visible and the journey could not pass as written. The journey was recorded as environment-blocked at F010 delivery (substitute coverage green: backend TS-001..TS-009, component TS-011/TS-012) and had never actually executed until this review.

**Fix 1 (test script):** the locator is now additionally filtered by `待证据`, uniquely scoping it to the assignment row.

**Fix 2 (product, real UI staleness defect):** with the locator fixed, the journey advanced and exposed a second latent bug — `AssignmentRow`'s detail query used the key `["product-validation-detail", id]`, which does not share the `["product-validation", projectId]` prefix that the evidence-import mutation invalidates, so an already-expanded assignment detail kept showing the pre-import state (`尚未导入量表证据`) after a successful import until a manual reload. The detail query key is now nested as `["product-validation", projectId, "detail", assignment.id]` so the existing invalidations refresh it. After both fixes the full journey passes (assign → rubric hand-out → import with one severe finding → honest 失败 outcome → separate technical/product statuses).

### 4.2 Deleting a project that never wrote artifacts could fail with `NoSuchBucket` (500) — FIXED in this review

During E2E cleanup, `DELETE /projects/{id}` returned 500: `delete_project_cascade` → `_verify_project_removed` lists the sources bucket prefix, but with **zero uploads ever made the bucket has not been created yet** (buckets are created lazily on first write), and `list_prefix` raised `NoSuchBucket`. The backend suite never hit this because its deletion tests upload sources first. **Fix:** `StorageAdapter.list_prefix` now treats a never-created bucket as holding no objects (narrow `ClientError` code `NoSuchBucket` → empty list; anything else still raises). Two regression tests added in `apps/backend/tests/test_deletion.py`: adapter-level (`test_list_prefix_reports_never_created_bucket_as_empty`) and API-level with an absent bucket (`test_project_deletion_with_no_uploads_succeeds_when_bucket_absent`).

### 4.3 E2E helper re-render race class is real, load-sensitive, and documented

`confirmedBlueprint`'s answer fill/save and the lesson-title override race against continuous panel re-renders (planning narration streaming plus the F013 memory-proposal polling). Observed behavior this run:

- The race is intermittent and **more likely on a production build (`next start`) than on `next dev`** — all green recorded executions used `next dev`; the same journeys flaked on `next start` and then passed on `next dev` (generation TS-026: 24–26s when the race is won vs 300–420s timeout when lost). This is the documented F004 M-1 / F013 IF-4 class, now with a sharper characterization.
- The `TRANSIENT_FAIL` scripting contract is **one-shot per fake-API process per key** (`FakeModelAdapter._transient_failures` is an in-process class-level counter; plan/deck/exercise keys are kind-scoped but the plan-phase key is shared by the generation/deck/exercise TS-026 journeys). Re-running a TS-026 journey against a used instance silently produces a full-success run and a false failure. Each such suite needs a freshly started fake instance.
- Serial workers (`--workers=1`) remain required; a parallel run of a single spec file reproduced failures.

**Follow-up:** harden the fill/save helpers (event-level wait for the saved revision rather than re-fill loops), and document the fresh-instance requirement next to the fault gates in `docs/TESTING.md`.

### 4.4 Harness lessons (environment, not product)

- Running several `next dev` servers from the same `apps/web` directory contaminates `NEXT_PUBLIC_*` inlining through the shared `.next` cache — a web instance silently targets another API origin. One web server at a time (or separate build caches) is required; the "dual-instance" E2E pattern means **web+API pairs**, not just multiple API instances.
- The deployed web build bakes `NEXT_PUBLIC_API_BASE_URL` at image build; deployed-stack E2E must use the deployed web origin and the deployed API origin consistently.

### 4.5 Historically blocked journeys — resume conditions discharged

- F008 M-1 (scripted-override alignment journey): **passed** (alignment TS-016).
- F009 TS-016 (evaluation browser journey): **passed**.
- F010 TS-013: **defects found and fixed in this review; journey green** (§4.1).

## 5. Open Residual Inventory (Phase-1 close-out list)

### 5.1 Owner-decision items

1. **F010 real-teacher review import** — the external teacher's three-unit rubric reviews have never been produced/imported; runtime honestly shows 未评估. Import path and snapshot-append procedure are specified in the F010 Test Design.
2. **Public cloud/region/domain/TLS exposure deployment Feature** — the sole named follow-up Feature (F012 D1 residual); hosted object-store deletion guarantees also fold in here (`docs/DATABASE.md`).
3. **Zod-vs-hand-written-interfaces DTO convention** (F006 M-3, echoed F007 L-3) — cross-Feature decision deferred since F006 and never taken.

### 5.2 Small engineering follow-ups

4. ~~F010 TS-013 E2E locator fix~~ — **fixed in this review** (§4.1), including the detail-refresh staleness fix.
5. ~~Deletion `NoSuchBucket` edge~~ — **fixed in this review** (§4.2) with two regression tests.
6. F009 M-3 — deck/exercise graphs still use the legacy truncated-JSON classification (only the lesson-plan graph received the SF-1 fix); recorded as a candidate follow-up.
7. E2E helper hardening remains open (event-level waits for the blueprint fill/save instead of re-fill loops); the operational documentation landed in this review (`docs/TESTING.md` E2E operational notes: serial workers, fresh fake instance per TS-026-family suite, web+API pairing for cap journeys, single `next dev` per app directory, dev-vs-prod-build race characterization).

### 5.3 Accepted constraints to keep disclosing (no action)

- Single-process API by design (in-process SSE registry); scale-out must re-verify (F011 M-2).
- Student-data screening evasion boundary (F001 TQ-003 / F011 L-1).
- Print/report output relies on the browser engine (F008 L-1).
- Rate counters count rejected attempts (F011 L-2, by design).
- pnpm workspace overrides raise postcss/sharp above Next.js pins; re-verify at the next Next.js upgrade (F011 L-3).
- F009 live evaluation passes used in-process eager execution; real-worker behavior is evidenced separately by the stop/restart recovery demonstration (recorded scope note).

### 5.4 Post-Phase-1 revisit triggers (recorded, unprioritized)

- Auto-cascade regeneration after confirmed intent changes (F007 D2, rejected pending teacher-cost evidence).
- Multi-tier exercise sets (F005 D9).
- Human-teacher keyboard review beyond scripted passes (F003/F006 recommendation).
- DESIGN_SYSTEM typography-family and exact semantic-color selection items.

## 6. Honest Validation Status (Phase-1 close)

- **Technical portfolio validation**: evidenced and reproducible — F009 six live passes (5 pass / 1 honest fail kept explicit), worker stop/restart recovery, concurrency/idempotency/fault-injection suites green, and this review's full-stack re-verification (§2).
- **Teacher product validation**: **capability delivered, evaluation not complete** — the rubric/import workflow (F010) works and is tested, but no real-teacher evidence exists yet; the runtime continues to display 未评估 rather than claiming success. Both statuses must remain separately visible (AGENTS "Repeated Pitfalls").

## 7. Documentation Sync Check and Fixes Applied

Checked `README.md`, `docs/` (9 files), ADRs 0001–0006, and `specs/ROADMAP.md` for staleness against the F013 DONE state. Three stale spots found and fixed in this review (no code changes):

1. `README.md` "Current Stage" — still described pre-F009 state and listed F008 as next actionable. **Fixed**: now records F001–F013 all `DONE`, this retrospective, and the sole follow-up candidate.
2. `specs/ROADMAP.md` Handoff — heading still read "Current: F013 NEXT" while the actual F013 DONE record had been appended under "Roadmap Risks". **Fixed**: section renamed to "Previous: F013 DONE", the delivery/DONE entries moved into it, and "Roadmap Risks" restored to risk-only content.
3. `docs/PRODUCT.md` Open Items — one entry still `[UNKNOWN, NON_BLOCKING]` about rubric wording and unit topics although F009/F010 resolved both. **Fixed**: marked `[RESOLVED, 2026-09-03]` with references.

Remaining doc-level notes (left unchanged, judged accurate): `docs/UX.md` two `[UNKNOWN, NON_BLOCKING]` items (small-screen boundary; teacher validation of the information architecture) and `docs/DESIGN_SYSTEM.md` two `[RECOMMENDED]` revisit items are open by design; `docs/ARCHITECTURE.md` correctly keeps the cloud-deployment item `[PARTIALLY RESOLVED]`.

## 8. Overall Conclusion

Phase 1 is delivered and internally consistent: every deterministic suite matches its delivery baseline exactly (after this review's fixes: backend 517 passed + 4 skipped, web 108/108 + tsc clean), the deployed stack rebuilds and smokes green from `main`, the live model path still works end to end, and every previously environment-blocked journey now passes — F010 TS-013 after fixing the two latent defects its first true execution exposed. The genuine gaps are the ones the project has already named honestly: no real-teacher product-validation evidence yet, no public-internet deployment, and a short list of small engineering follow-ups recorded above. All code fixes from this review are uncommitted in the working tree pending owner authorization.

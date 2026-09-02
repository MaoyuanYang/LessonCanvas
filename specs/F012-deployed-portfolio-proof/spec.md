# F012: Deployed Portfolio Proof

- Spec Status: `DONE`
- Roadmap Status: `DONE`
- Priority: `P0`
- Owner: `YMY / Project Owner` (driving `ZCode feature-dev` session, A-012)
- Work item: [GitHub Issue #24](https://github.com/MaoyuanYang/LessonCanvas/issues/24) — bound 2026-09-02 (authorized); work-status authority
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F009` (DONE; reproducible technical evidence harness), `F011` (DONE; public multi-account guardrails, provider constraint set D10, residuals M-1/M-2); routed residual from F001/B-001: Postgres LangGraph checkpointer investigation
- Last Updated: 2026-09-02

## Gate Record: SPEC READY

- Status: `PASS` (revalidated)
- Revalidation: 2026-09-02, `YMY / Project Owner` approved via interactive session together with ADR-0006 `Accepted` (question-form "批准，开始实施"); revision @ `5edfc9352c1e` (D2/D9 revised, D11/D12 added, flows/ACs updated); checklist re-run 11/11 YES on the revised revision
- Prior record (STALE):
- Validation time: 2026-09-02
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-02 (question-form answers selecting D1 "本地全栈容器化为终点", D2 "局域网访问就行", D3 "样例+自助受限生成", D4 "纳入 F012"; D5–D10 resolved from repository evidence and confirmed together with the explicit SPEC READY approval; Issue #24 creation separately authorized), scope: F012 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-010, Greenfield lifecycle with OBSERVED baseline inventory retained above, no unresolved conflicts, no Critical Open Question OPEN/DEFERRED)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F012-deployed-portfolio-proof/spec.md` @ (this file, final working-tree hash recorded in `STAGE.md` Gate Snapshot)
  - `specs/F009-technical-portfolio-evaluation/spec.md` @ `38bff6656785`
  - `specs/F010-teacher-product-validation/spec.md` @ `80de720ec874`
  - `specs/F011-public-multi-account-guardrails/spec.md` @ `e4425d0a2556`
  - `AGENTS.md` @ `f68a2ee15654`
  - `specs/ROADMAP.md` @ `15cac6f9d5d9`
  - `docs/API.md` @ `6f6712059e7f`
  - `docs/DATABASE.md` @ `8683d91a9d88`
  - `docs/ARCHITECTURE.md` @ `9d26a7199d19`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/TESTING.md` @ `c300110fce4d`
  - `docs/UX.md` @ `abd0ced09605`

## Gate Record: DONE

- Status: `PASS`
- Validation time: 2026-09-02
- Delivery: PR [#25](https://github.com/MaoyuanYang/LessonCanvas/pull/25) merged as `c6c7b53` (commit `dd04e72` + docs `d56a7ca`; full delivery flow authorized by `YMY / Project Owner` 2026-09-02: commit, push, PR, merge, DONE record, Issue close). Main re-verified after merge: backend 477 passed + 4 skipped + ruff clean; web 97 tests + tsc clean + lint 0 errors; deployed LAN stack healthy (`http://192.168.9.101:3002`).
- DONE evidence manifest: `deployment-evidence.md` (14 executed rows, all PASS: deploy chain/migrate/smoke, idempotent seeding ×3 incl. post-redeploy, live DeepSeek recovery journey TS-029, deletion completeness all-zero + retained ledger, SSE single-process, F011 D10 recheck, teardown/redeploy, accessibility + 420px spot, deployed E2E 5/5); review `review-f012-r3` (IF-1..IF-11 all fixed or accepted with rationale); ADR-0006 `Accepted`; Gates revalidated after the L3 design change (SPEC/UI/TEST DESIGN r2).
- Documentation sync: README, AGENTS, docs/API, ARCHITECTURE, DATABASE, TESTING, UX, PRODUCT, ADR-0006 + index, ROADMAP/STAGE; historical F001/F011 records immutable.

## Baseline Evidence (Preflight Inventory, 2026-09-02)

All items are `OBSERVED` from code, compose files, env examples, and Specs at `main @ 6cf265a` unless labeled otherwise.

- `infra/docker-compose.yml` runs only infrastructure (PostgreSQL 16 + pgvector, Redis 7, MinIO) with dev-only credentials and healthchecks; Next.js Web, FastAPI application, and Celery Worker run as local processes (`uv run uvicorn`, `corepack pnpm web:dev`, `celery worker`) — no application container images or full-stack deployment chain exist.
- Backend and web configuration is environment-driven (`apps/backend/.env.example`, `apps/web/.env.example`): database/Redis/MinIO endpoints, model adapter settings, application token secret (ADR-0006 removed the Clerk keys). `.env` files are git-ignored; only examples are tracked.
- The complete protected workflow (brief → blueprint → plans/decks/exercises → evidence → regeneration → alignment/export → validation) is delivered F001–F010 with 454 backend tests and 83 web tests passing at F011 DONE; run recovery, fault injection, and reproducible technical evaluation exist as the F009 harness; public guardrails (PostgreSQL-authoritative limits, quotas, deletion completeness incl. checkpoints, audit) exist per F011.
- F011 D10 recorded the verifiable provider constraint set (identity: Clerk; object storage: S3-compatible private objects with proven delete reachability; model: DeepSeek via single adapter; local reference stack MinIO + Clerk + DeepSeek) and routes actual deployment verification to F012.
- F011 M-2: the per-workspace SSE stream cap uses an in-process registry valid only under a single-process web deployment assumption (`sse_registry.py`); must be re-checked for the deployed topology.
- F011 M-1: authenticated guardrails E2E is env-gated and not yet appended to CI evidence; resumable when stable auth is available.
- F001/B-001 residual routed to F012: investigate Postgres LangGraph checkpointer behavior (checkpoint tables are keyed by `thread_id` = discovery run id; F011 D5 already added their deletion to cascades, but the saver's operational behavior in the deployed topology is uninvestigated).
- F010 D9: product validation is recorded as an independent passed/failed/not-complete status; F012 must display it honestly alongside technical status (never infer usability from deployment).
- No synthetic sample project, public entry page, deployment/smoke scripts, or release-evidence records exist.

## Design Change Record (2026-09-02, L3 — ADR-0006)

- Change: remove managed identity (Clerk) for the MVP; no login/logout; identity becomes application-issued anonymous workspace tokens (`POST /auth/guest-token`, HS256, random subject per browser). Owner decision: `YMY / Project Owner`, 2026-09-02 (interactive: "浏览器匿名工作区", "迁移改名为 subject", "并入 F012").
- Authority: ADR-0006 `Accepted` 2026-09-02. Supersedes the identity items of F001 D1 and F011 D10 for current and future behavior; historical Feature records stay immutable.
- Gate impact: `SPEC READY` @ `8c033df6a4e6`, `UI READY` @ `ux-ui-f012-r1`, `TEST DESIGN READY` @ `test-design-f012-r1` marked `STALE` by this change; revalidated below after revision.

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Deployment boundary (DONE definition) | F012 DONE = complete local full-stack containerized deployment: Next.js Web, FastAPI application, and Celery Worker become containerized services alongside the existing PostgreSQL/pgvector, Redis, and MinIO compose services, with a documented and really-executed chain: build → migrate → start → health/smoke → recovery verification. Public cloud provider selection, region deployment, and internet exposure are explicitly out of scope and deferred to a follow-up Feature. | `YMY / Project Owner`, 2026-09-02 (interactive confirmation, "本地全栈容器化为终点") |
| D2 | Reviewer access model | LAN access: the deployed instance binds to the owner machine's LAN interface so a portfolio reviewer on the same network reaches the public entry directly; F011 guardrails remain fully active. No internet exposure or tunnel in this Feature. [REVISED 2026-09-02, ADR-0006] There is no login: each browser obtains an application-issued anonymous workspace token (`POST /auth/guest-token`) automatically; the former Clerk allowed-origin prerequisite is removed. | `YMY / Project Owner`, 2026-09-02 (interactive confirmation, "局域网访问就行"; revised with ADR-0006 approval) |
| D3 | Sample and reviewer generation experience | Synthetic sample + self-service bounded generation: the deployment seeds one synthetic complete sample project (brief, blueprint, all three artifact families, layered evidence, alignment/export state, validation status — synthetic data only, never a real teacher's trace) that any authenticated reviewer can inspect read-only; reviewers may additionally self-register and run real bounded generation under the existing F011 limit set unchanged (240/120 req/min, 2 concurrent runs, 6 SSE streams, 200 MB/day uploads, workspace quotas). | `YMY / Project Owner`, 2026-09-02 (interactive confirmation, "样例+自助受限生成") |
| D4 | F001/B-001 checkpointer residual | Included in F012: investigate and verify Postgres LangGraph checkpointer behavior in the deployed topology (checkpoint write/settle behavior, connection lifecycle, interaction with run recovery and deletion cascades); outcome is either a verified-correct record or a documented fix, never a silent assumption. | `YMY / Project Owner`, 2026-09-02 (interactive confirmation, "纳入 F012") |
| D5 | Required deployment/release evidence set | One governed evidence record (delivery-record pattern, not business truth) capturing actually-executed commands and outputs for: image build, deterministic test pass, migration, stack start, health/smoke, representative journey incl. recovery (reusing the F009 harness scope in the deployed environment), deletion completeness spot-check, and teardown/restart. Placeholders are never recorded as executed; each entry binds command, date, and outcome. Rollback evidence = documented stack teardown + redeploy from clean state (no production data exists to protect). | Resolved from evidence; confirmed with Spec approval 2026-09-02 |
| D6 | Availability and startup behavior | No SLA claim of any kind. The compose deployment declares restart policies and healthchecks for every service; cold-start behavior (first model call latency, worker warm-up) is documented as known behavior; the public entry shows service-unavailable states honestly via existing error surfaces. | Resolved from evidence; confirmed with Spec approval 2026-09-02 |
| D7 | Status publishing without private data | Technical Phase-1 status and product-validation status reuse the existing F009/F010 evidence and status surfaces unchanged (separate, honest, version-bound); no private trace, evaluation detail, or teacher content is republished. The public entry links to reproducible repository verification (README/docs evidence chain), never to private runs. | Resolved from evidence; confirmed with Spec approval 2026-09-02 |
| D8 | SSE single-process assumption (F011 M-2) | The deployed topology runs exactly one Web/API container process (replicas: 1, documented in deployment docs), keeping the in-process SSE registry assumption valid; the deployment evidence records this constraint explicitly so any future scale-out must first re-verify F011 M-2. Worker concurrency stays Celery-owned and unaffected. | Resolved from evidence; confirmed with Spec approval 2026-09-02 |
| D9 | Provider constraint verification (F011 D10 handoff) | The deployed provider set equals the verified reference stack (DeepSeek single model adapter, MinIO private object storage, PostgreSQL/Redis local). [REVISED 2026-09-02, ADR-0006] Identity is no longer an external provider: it is the application-issued subject token (D11), so the identity constraint reduces to token verification correctness in deployment. Each remaining F011 D10 constraint (deletion reachability per store, private-object access, disclosure wording) is re-verified against the deployed configuration and recorded in the deployment evidence; no new provider is introduced in this Feature. | Resolved from evidence; confirmed with Spec approval 2026-09-02; revised with ADR-0006 approval |
| D10 | Synthetic sample ownership and refresh | The sample is owned application seed data generated by a versioned seeding script from the governed synthetic corpus pattern (F009 governance: manifest, checksums, revision id); it is created at deployment/seed time, marked synthetic in metadata, owned by a designated demo workspace, and never mixed into any real teacher's workspace. Staleness is acceptable and visible (version-bound states render as-is); no background refresh job is added. | Resolved from evidence; confirmed with Spec approval 2026-09-02 |
| D11 | Identity without login (ADR-0006) | Application-issued anonymous workspace tokens: `POST /auth/guest-token` mints an HS256 token with a fresh random subject (30-day expiry) signed by the application secret; the web stores it in `localStorage`, attaches it as the existing `Authorization: Bearer` header, and auto-issues on first use. Each browser is one isolated workspace; all F011 ownership/quota/isolation/deletion behavior is preserved on the subject key. No login/logout UI, no password storage, no account recovery; losing the token starts a new empty workspace (accepted for the MVP demo). The endpoint is unauthenticated, creates no rows, discloses nothing, and joins the F011 inventory-driven unauthenticated sweep. | `YMY / Project Owner`, 2026-09-02 (ADR-0006 approval; interactive "浏览器匿名工作区") |
| D12 | Workspace subject column rename | The Clerk-era `clerk_user_id` columns (`workspaces`, `account_deletion_events`) are renamed to `subject` via one Alembic migration (unique constraint and index rebuilt under new names); all call sites follow. Schema and model language match the identity mechanism of D11. | `YMY / Project Owner`, 2026-09-02 (interactive "迁移改名为 subject") |

## Goal

Make the complete protected LessonCanvas workflow and its technical evidence independently inspectable in a really-deployed local full-stack environment — reachable on the LAN, protected by F011 guardrails, seeded with a safe synthetic sample, and backed by honestly-recorded deployment and recovery evidence.

## Business Value

The portfolio demonstrates operational reality: a reviewer on the LAN can sign in, run or inspect the core journey, observe recovery and validation status, and compare the deployment claim with reproducible project verification — converting repository claims into observable release evidence without any real teacher's private data.

## User Story

As a portfolio reviewer on the owner's LAN, I want to access the protected deployed demonstration and its reproducible evidence, so that I can evaluate the Agent application beyond screenshots, code descriptions, or a prerecorded happy path.

## Scope

- Full-stack containerization: Dockerfiles and compose services for Next.js Web, FastAPI application, and Celery Worker alongside the existing PostgreSQL/pgvector, Redis, and MinIO services, with healthchecks, restart policies, and environment-driven configuration (D1, D6).
- Documented, really-executed deployment chain and evidence record: build, deterministic tests, migration, start, health/smoke, representative journey with recovery, deletion spot-check, teardown/restart (D5).
- LAN reviewer access with F011 guardrails active and no login: anonymous workspace tokens per browser (D11); public entry explains the product/evidence boundary (D2, D7).
- Synthetic complete sample project seeded from governed synthetic data, inspectable read-only by authenticated reviewers (D3, D10).
- Reviewer self-service bounded real generation under the unchanged F011 limit set in the deployed environment (D3).
- Deployment-topology verification obligations: SSE single-process constraint recorded and honored (D8); F011 D10 provider constraints re-verified against the deployed configuration (D9).
- Postgres LangGraph checkpointer investigation with a verified outcome or documented fix (D4).
- Honest separate technical and product-validation status display and links to reproducible repository verification (D7).

## Out of Scope

- Public cloud provider selection, region deployment, internet exposure, domain, TLS certificates, CDN, multi-region, active-active, Kubernetes, enterprise SLA, or production school rollout (D1; follow-up Feature).
- Anonymous unlimited generation, payment, subscription, or user billing (DRAFT rule).
- Republishing a real teacher's private run as a portfolio sample; any cross-workspace reuse of teacher content (D10).
- Claiming teacher usability when the independent product-validation threshold fails or is incomplete (F010 D9 rule, restated).
- Redesigning runtime boundaries, quotas, run/version contracts, or any owning module's truth (deployment and verification only).
- New infrastructure authority: deployment automation and evidence records are not a business Source of Truth (DRAFT rule; AGENTS).
- Performance benchmarking or capacity sizing beyond recovery-correctness verification (TESTING.md).
- The F011 M-1 env-gated E2E remains env-gated; F012 may append its evidence opportunistically but does not own un-gating it.

## Actors / Preconditions

- Actors: the portfolio reviewer (anonymous workspace token per browser, on the owner's LAN); the workspace owner (teacher) using bounded real generation; the operator (owner of the deployment environment) running build/deploy/evidence scripts.
- Preconditions: F001–F011 behavior present at `main`; Docker environment available on the owner machine; application token secret configured via environment (D11); model provider credentials configured via environment; governed synthetic corpus available for seeding.

## Main Flow

1. The operator builds and starts the full stack with the documented deployment chain; health and smoke checks pass and are recorded (D1, D5).
2. A reviewer on the LAN opens the public entry, understands the product/evidence boundary, and receives an anonymous workspace token automatically (D2, D11); no sign-in screen exists.
3. The reviewer inspects the synthetic complete sample project — brief, blueprint, artifacts, layered evidence, alignment, export, validation status — read-only (D3, D10), or self-registers and runs bounded real generation within F011 limits (D3).
4. The reviewer observes provider-failure and recovery behavior through the existing run surfaces (accurate progress, return-to-work, no duplicate model work), verified in the deployed environment by the F009-scope recovery evidence (D5).
5. The release/status view reports technical and product-validation outcomes honestly and separately, and links to reproducible repository verification (D7).

## Alternative Flows

- Service starting/unavailable: healthchecks and restart policies govern startup; the entry surface shows existing honest unavailable states (D6); no fabricated readiness.
- Missing/invalid workspace token: in-app `AUTH_REQUIRED` honest states; the web auto-issues a guest token on first use (D11).
- Quota/rate reached during reviewer generation: existing F011 denial surfaces with `retry_after` and account usage visibility; no hidden queued work.
- Provider failure mid-run: existing provider/transient taxonomy and bounded retry; leave-and-return shows accurate run state; retries reuse idempotent runs without double billing (F003/F007 semantics, verified deployed).
- Sample absent or stale: seeding is idempotent; version-bound states render as-is with visible staleness; no silent regeneration (D10).
- Deletion in the deployed environment: existing F011 cascades (rows, checkpoints, objects, audit ledger per D4-retention) verified by a deployed spot-check (D5).

## Business Rules / Invariants

- Deployment automation, compose topology, and evidence records never become business Source of Truth; PostgreSQL ownership/version/run truth is unchanged (AGENTS).
- All F011 guardrails, isolation, and non-disclosure behavior remain fully active in the deployed environment; deployment does not weaken any limit, audit, or deletion guarantee.
- Portfolio samples are synthetic under the current privacy decision; private teacher projects remain owner-only and deletable; nothing private is republished (D7, D10).
- Real commands and operational claims are documented only after they execute successfully; placeholders are never replaced with invented commands (DRAFT rule; D5).
- Technical Phase-1 completion requires the deployed representative workflow to prove approved core technical evidence and pass guardrail, accessibility spot-check, and recovery checks; missing evidence, isolation failure, duplicate model work on retry, or failed injected recovery prevents technical completion.
- Product validation remains an independent outcome; an honest technical release may coexist with failed or not-complete product validation, and teacher-usability claims remain prohibited without a product-validation pass.
- No availability or SLA claim beyond documented restart/health behavior (D6).

## State Transitions

- Deployment lifecycle: `built → migrated → started → healthy (smoke passed) → evidence recorded`; any failure leaves the stack down or partially healthy with the failure recorded; teardown returns to `built` for redeploy.
- Sample lifecycle: `absent → seeded (version-bound) → stale (visible, still inspectable)`; no automatic refresh (D10).
- Run/artifact/validation states reuse the existing F001–F010 state machines unchanged; deployment adds no new business states.

## Data Changes

- No new business tables or columns are expected; deployment configuration and seeding are additive infrastructure. If the checkpointer investigation (D4) requires a data-level fix, it enters through a normal migration with Documentation Sync.
- Seeded sample data lives in the existing schema owned by a designated demo workspace, marked synthetic in existing metadata fields; it is deletable by normal account/project deletion.

## API Behavior

- No new public API surface is required for deployment or inspection; existing health endpoint (`GET /health`) and F009/F010 status/evidence surfaces serve the release view (D7).
- Smoke checks use existing health/readiness behavior; no private or secret information is exposed by deployment or evidence records (D5, D7).

## Error Cases

- Build/migration/start failure: deployment chain stops, failure recorded in evidence; stack left in the failed state with documented recovery (fix + rerun).
- LAN origin rejected by identity provider: recorded as a deployment prerequisite failure (owner configures allowed origin), not an application defect.
- Smoke or recovery verification failure in the deployed environment: deployment evidence records the failure; technical completion claim withheld (no fabricated pass).
- Reviewer quota denial, provider failure, partial deletion: existing F011/F003 taxonomy surfaces unchanged.

## Idempotency / Concurrency / Transaction / Consistency

- Deployment and seeding scripts are idempotent (re-run converges; seeding creates the sample once per version).
- Run idempotency, retry-without-double-billing, and concurrency limits are the existing F003/F007/F011 behavior, verified — not changed — in the deployed environment.
- The Web/API deployment is single-process by design (D8); this constraint is documented and re-verified before any future scale-out.

## Security / Privacy / Authorization

- Managed identity gates every path except health; F011 isolation, non-disclosure, and audit behavior is active in the deployed environment (verified by spot-check evidence).
- Secrets live only in untracked environment files / deployment environment; evidence records never contain credentials, tokens, private content, or teacher data (D5, D7).
- The synthetic sample contains no real teacher or student data and is screened by the same untrusted-input rules.

## Non-functional

- Observability: existing run/trace/audit surfaces; deployment evidence record is the operational record (D5).
- Startup: restart policies + healthchecks per service; cold-start behavior documented (D6).
- Cost: reviewer generation is bounded by F011 limits; model spend during verification is bounded by the representative journey scope (D3, D5).

## Acceptance Criteria

- `AC-001` Given the owner machine with Docker, when the operator runs the documented deployment chain, then the full stack (Web, API, Worker, PostgreSQL/pgvector, Redis, MinIO) builds, migrates, starts, and passes health/smoke checks, with each really-executed step recorded in the deployment evidence.
- `AC-002` Given a reviewer browser on the LAN, when they open the deployed public entry, then they can inspect the synthetic complete sample project — brief, blueprint, all three artifact families, layered evidence, alignment and export state, validation status — read-only, with version-bound states rendered honestly.
- `AC-003` Given a self-registered reviewer in the deployed environment, when they run real generation up to the F011 limits, then denials, usage visibility, and recovery behave exactly per F011 (limits unchanged, no hidden queued work).
- `AC-004` Given a provider or Worker failure during a representative deployed run, when the reviewer leaves and returns, then the deployed system shows accurate progress and resumes without duplicate model work or lost valid artifacts, evidenced by the F009-scope recovery check executed in the deployed environment.
- `AC-005` Given the release/status view in the deployed environment, when technical and product evidence differ, then both outcomes remain explicit and independent, and no teacher-usability claim is made without a product-validation pass.
- `AC-006` Given project and account deletion in the deployed environment, when cleanup completes, then governed private data and complete traces are removed across PostgreSQL (including checkpoints), object storage, and the audit ledger per the F011 D4 retention rule, verified by a deployed spot-check.
- `AC-007` Given the repository documentation after delivery, when a reviewer follows the documented deployment and verification commands, then every command is real, synchronized with the repository, and sufficient to verify the documented stage, with the evidence record binding command, date, and outcome.
- `AC-008` Given the deployed topology, then the single-process Web/API constraint required by the SSE registry is satisfied and documented, and each F011 D10 provider constraint is re-verified against the deployed configuration and recorded.
- `AC-009` Given the routed F001/B-001 residual, when the Postgres LangGraph checkpointer investigation completes, then the outcome is a verified-correct record or a documented fix with tests — never a silent assumption.
- `AC-010` Given the deployed entry and core flows, then keyboard-operable core flows and the reduced small-screen experience pass a recorded spot verification, consistent with the documented WCAG 2.2 AA scope.

## Open Questions

- [ ] `NON-CRITICAL` Exact Docker image strategy details (multi-stage layout, base images, layer caching) — reversible Implementation Plan choice. Owner: Implementation Plan. Status: `OPEN` (permitted; does not change requirements).
- [ ] `NON-CRITICAL` Whether the F011 M-1 env-gated E2E is opportunistically appended during deployed verification. Owner: `YMY / Project Owner`. Status: `OPEN`.

All Critical questions from the DRAFT Spec are resolved in the Decision Log (D1–D10); none remain `OPEN` or `DEFERRED`.

## Deliberately Deferred Detail

- Cloud provider selection, region, domain, TLS, and internet exposure (follow-up Feature per D1).
- DTOs and concrete request/response schemas beyond existing surfaces (none new expected).
- Pixel-level UI, complete Test Design (separate artifact).
- Image build internals, CI/CD product choice, and deployment minutiae (Implementation Plan).

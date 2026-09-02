# Feature Test Design: F012 Deployed Portfolio Proof

## Metadata

- Spec/Issue: `specs/F012-deployed-portfolio-proof/spec.md` / [GitHub Issue #24](https://github.com/MaoyuanYang/LessonCanvas/issues/24)
- Validated inputs: Spec (ADR-0006 revised revision, 2026-09-02), UX/UI @ `ux-ui-f012-r2` (`UI READY` revalidation, 2026-09-02)
- Test Design revision: `test-design-f012-r2` (r1 marked STALE by the 2026-09-02 ADR-0006 Design Change; this revision removes the sign-in flow and adds guest-token coverage)
- Coverage scope: risk-based scope confirmed by `YMY / Project Owner` on 2026-09-02 (interactive selection "风险导向范围": functional, error/partial-failure/recovery, auth/permission, regression, smoke, accessibility spot-check — executed against the deployed environment; excluded: performance benchmarking and concurrency/load stress `N/A - F011 behavior unchanged; TESTING.md forbids benchmarks as evidence`, fuzz `N/A - F011 adversarial corpus already covers unchanged input surfaces`)
- Environments: (a) deterministic developer stack for unit/integration additions (compose infra + process app + fake adapter, existing pattern); (b) the deployed full-stack container environment (D1) for deployment-chain, smoke, journey, recovery, deletion, and accessibility evidence; live model only for the bounded representative journey evidence where the fake adapter cannot demonstrate provider-failure reality
- `TEST DESIGN READY` Status: `PASS` (see Gate Record)

## Risk Register and Scenario Selection

| Risk / behavior | Impact | Scenario(s) |
| --- | --- | --- |
| Deployment chain fails or is partly fabricated (placeholders recorded as executed) | False operational claim; AC-001/AC-007 broken | TS-001, TS-002 |
| Sample leaks into reviewer ownership or reviewers can mutate sample | Sample integrity, isolation breach | TS-004, TS-005 |
| Sample missing/stale renders dishonestly or blocks the reviewer journey | Reviewer cannot inspect; AC-002 broken | TS-004, TS-006 |
| Deployed recovery duplicates model work or loses artifacts | Core invariant broken in deployment | TS-007 |
| Deletion incomplete in deployed topology (rows/checkpoints/objects/ledger) | Privacy violation | TS-008 |
| Statuses conflated (technical vs product) or usability claimed | Honesty violation | TS-009 |
| Guest-token issuance discloses data or bypasses isolation (ADR-0006 D11) | Unauthenticated surface abuse | TS-005, TS-016 |
| SSE registry assumption broken by topology | F011 M-2 guardrail silently invalid | TS-010 |
| Checkpointer misbehavior in deployed topology (B-001 residual) | Recovery/truth defect | TS-011 |
| Provider constraint unverified against deployed config | F011 D10 handoff unmet | TS-012 |
| Landing/entry dishonesty (availability, boundary) | Portfolio credibility | TS-003 |
| Reviewer self-service generation exceeds/under-reports limits in deployment | Guardrail drift | TS-013 |
| Existing suites regress under containerization | Completed features broken | TS-014 |
| Core flows not keyboard-operable / reduced screen broken in deployment | Accessibility claim false | TS-015 |

Happy Path: TS-001/TS-004; Alternative/boundary: TS-006/TS-013; Error/security: TS-005/TS-008; Recovery: TS-007/TS-008; Concurrency: `N/A - user scope decision (风险导向, 2026-09-02); F011 limits unchanged and re-verified only for accuracy (TS-013), not under load`; Migration: TS-001 (deployed chain runs migrations); Performance: `N/A - user scope decision (风险导向, 2026-09-02); no performance requirement`; Visual regression: `N/A - no new visual language; landing section verified by component tests (TS-003)`; i18n: `N/A - zh-Hans inline copy per repo convention, asserted in unit tests`.

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 | TS-001, TS-002 |
| AC-002 | TS-004, TS-006 |
| ADR-0006 token mechanism | TS-016 |
| AC-003 | TS-013 |
| AC-004 | TS-007 |
| AC-005 | TS-009 |
| AC-006 | TS-008 |
| AC-007 | TS-002 |
| AC-008 | TS-010, TS-012 |
| AC-009 | TS-011 |
| AC-010 | TS-015 |
| Regression of completed features | TS-014 |

## Scenarios

### TS-001: Full-stack deployment chain executes and records honestly

- Protects: AC-001 (build → migrate → start → health/smoke)
- Risk/type: Deployment functional / Smoke
- Given: the owner machine with Docker and the documented deployment entry (compose full stack, Web/API/Worker images)
- When: the operator runs the documented chain from clean state
- Then: every service reaches healthy, migrations apply, `GET /health` and the smoke script pass, and the evidence record binds each really-executed command, date, and outcome; a deliberately broken step (e.g., bad env) is recorded as failure, never as pass
- Level: Deployment / Operational script
- Automation target/path: `infra/` deployment scripts + `infra/scripts/smoke` (or established equivalent) + evidence record under `specs/F012-deployed-portfolio-proof/deployment-evidence.md`
- Data/fixture/environment: deployed full-stack environment (D1); secrets via untracked env
- Result/evidence: NOT RUN

### TS-002: Teardown/redeploy idempotency and evidence completeness

- Protects: AC-001, AC-007 (restart from clean state; real synchronized commands)
- Risk/type: Recovery / Regression of deployment
- Given: a healthy deployed stack
- When: the stack is torn down and redeployed from clean state (volumes reset), and the seeding script is re-run twice
- Then: redeploy reaches healthy again, seeding is idempotent (one sample per version), and the documented commands in README/docs match the actually-executed chain
- Level: Deployment / Operational script
- Automation target/path: deployment scripts + evidence record
- Result/evidence: NOT RUN

### TS-003: Landing portfolio-review section honesty

- Protects: AC-005, AC-007 (boundary, availability, verification links)
- Risk/type: Functional UI / Unit
- Given: the landing page
- When: rendered signed-out and signed-in, with the API reachable and unreachable
- Then: the review section states the synthetic-sample + bounded-generation boundary, links `/sample` and repository verification, shows no SLA claim, and the unavailable state renders the honest Alert rather than fabricated readiness
- Level: Web unit/component
- Automation target/path: `apps/web/__tests__/` (landing component tests, existing pattern)
- Result/evidence: NOT RUN

### TS-004: Sample read-only journey renders all tabs honestly

- Protects: AC-002 (inspection journey)
- Risk/type: Functional / Happy path
- Given: the deployed environment with the seeded sample (fresh and stale variants)
- When: an authenticated reviewer opens `/sample` and traverses every tab
- Then: all ten workspace tabs render sample data with version bindings and stale banners as-is, write affordances are suppressed with the persistent read-only notice, and the F009/F010 status regions are reachable and independent
- Level: Web E2E (deployed or deterministic stack) + unit tests for write suppression
- Automation target/path: `apps/web/__tests__/` (sample shell tests) + `apps/web/e2e/` journey extension
- Result/evidence: NOT RUN

### TS-005: Sample authorization boundary

- Protects: AC-002, AC-003 (reviewers cannot mutate the sample; server-enforced)
- Risk/type: Authorization / Security
- Given: the deployed environment, a reviewer browser (guest workspace token, ADR-0006 D11), and the sample project id
- When: the reviewer attempts write operations against the sample (confirm, generate, upload, delete) directly via API and via any suppressed UI path
- Then: every write is rejected server-side with the existing authorization error class; a tokenless request still receives `AUTH_REQUIRED` (no redirect — no login exists); the sample never appears in any reviewer's project list
- Level: API / Contract integration
- Automation target/path: `apps/backend/tests/` (sample access-rule tests)
- Result/evidence: NOT RUN

### TS-006: Sample missing/stale states

- Protects: AC-002 (honest sample states)
- Risk/type: Alternative flow / Empty-error
- Given: deployment without seeding (or seed failure) and a stale seeded sample
- When: `/sample` is opened
- Then: missing sample shows the "示例项目暂不可用" EmptyState with reload; stale sample renders stale banners as-is without silent regeneration or fabricated freshness
- Level: Web unit + deterministic-stack integration
- Automation target/path: `apps/web/__tests__/`
- Result/evidence: NOT RUN

### TS-007: Deployed recovery without duplicate model work

- Protects: AC-004 (leave-and-return resume)
- Risk/type: Error/Partial failure/Recovery
- Given: a representative run in the deployed environment with fault injection per the F009 harness scope
- When: a provider/Worker failure interrupts the run and the user leaves and returns
- Then: progress is accurate on return, the run resumes/reuses idempotently, and model-call totals prove no duplicate billing; traces keep the failure and recovery events
- Level: Deployed operational verification (scripted, F009 harness scope)
- Automation target/path: F009 harness invoked against the deployed environment + evidence record
- Result/evidence: NOT RUN

### TS-008: Deployed deletion completeness spot-check

- Protects: AC-006 (cross-service removal)
- Risk/type: Security/Privacy / Recovery
- Given: the deployed environment with a populated project and account
- When: project deletion and then account deletion complete
- Then: no residual owned rows in governed PostgreSQL tables (including LangGraph checkpoints), no objects under the workspace/project prefixes in MinIO, and the F011 D4 content-free retained ledger is the only survivor; partial failures stay visible and repairable
- Level: Deployed verification script (extends F011 D5 verification tooling)
- Automation target/path: deletion-verification script + evidence record
- Result/evidence: NOT RUN

### TS-009: Independent status display in deployment

- Protects: AC-005 (separate honest outcomes)
- Risk/type: Functional / Honesty invariant
- Given: the deployed environment with differing technical and product-validation outcomes (synthetic sample data)
- When: the reviewer opens the sample evidence/status surfaces and the landing links
- Then: technical and product-validation statuses render as separate passed/failed/not-complete outcomes, no usability claim appears without a product pass, and no private evaluation detail is exposed
- Level: Web unit + deployed inspection
- Automation target/path: `apps/web/__tests__/` (existing status-region tests rerun; deployed spot evidence)
- Result/evidence: NOT RUN

### TS-010: Single-process SSE constraint satisfied and documented

- Protects: AC-008 (F011 M-2 re-check)
- Risk/type: Deployment topology verification
- Given: the deployed stack configuration
- When: the deployment runs and concurrent SSE streams are opened in the deployed environment
- Then: the Web/API container runs exactly one process (replicas: 1, documented), the per-workspace SSE cap enforces correctly in deployment, and the constraint is recorded in deployment docs so scale-out must re-verify F011 M-2
- Level: Deployed verification + docs check
- Automation target/path: SSE-cap integration (existing) + deployed evidence record + docs assertion
- Result/evidence: NOT RUN

### TS-011: Postgres LangGraph checkpointer investigation (B-001)

- Protects: AC-009 (verified outcome or documented fix)
- Risk/type: Routed residual investigation / Recovery
- Given: the deployed topology and discovery runs with interruption
- When: checkpoint write/settle behavior is exercised across run lifecycle, recovery, and deletion cascade
- Then: behavior is verified-correct (recorded with evidence) or a defect is fixed with a regression test; no silent assumption remains
- Level: Backend integration + deployed verification
- Automation target/path: `apps/backend/tests/` (checkpointer lifecycle tests as investigation outcome dictates)
- Result/evidence: NOT RUN

### TS-012: F011 D10 provider constraints re-verified in deployment

- Protects: AC-008 (constraint handoff)
- Risk/type: Security/Privacy verification
- Given: the deployed configuration (application token secret, MinIO, DeepSeek adapter, PostgreSQL/Redis; identity is application-issued per ADR-0006)
- When: each D10 constraint (per-store deletion reachability, private-object access, disclosure wording) is checked against the deployed config
- Then: every constraint holds and is recorded in the deployment evidence; any violation blocks the technical-completion claim
- Level: Deployed verification script/checklist
- Automation target/path: evidence record + existing F011 verification tooling
- Result/evidence: NOT RUN

### TS-013: Reviewer self-service generation under unchanged limits in deployment

- Protects: AC-003 (bounded real generation)
- Risk/type: Boundary / Regression of guardrails
- Given: a self-registered reviewer in the deployed environment
- When: real generation runs within and at the F011 limits (rate, concurrency, uploads, quotas)
- Then: within-limit work succeeds; at-limit denials return the existing taxonomy with `retry_after`/usage visibility; limits are numerically unchanged from F011
- Level: Deployed journey (scripted, fake-or-live adapter per step)
- Automation target/path: existing F011 limit tests rerun + deployed journey evidence
- Result/evidence: NOT RUN

### TS-014: Existing suites green in/after containerization

- Protects: all ACs (no regression)
- Risk/type: Regression
- Given: the containerization changes (Dockerfiles, compose, env wiring, seeding)
- When: backend pytest + ruff and web vitest + tsc + lint run on the delivered revision
- Then: all pass (env-gated skips unchanged); no existing behavior altered by packaging
- Level: Full deterministic suites
- Automation target/path: existing suites (`apps/backend`, `apps/web`)
- Result/evidence: NOT RUN

### TS-015: Accessibility and reduced-screen spot check in deployment

- Protects: AC-010 (WCAG 2.2 AA spot scope)
- Risk/type: Accessibility verification
- Given: the deployed instance and the documented core flows (landing → sample tabs; no sign-in exists)
- When: operated keyboard-only and at reduced small-screen width
- Then: keyboard-only completes the flow with visible focus; reduced screen renders the canonical reduced experience; result recorded as deployed spot evidence (manual or scripted per Implementation Plan)
- Level: Deployed spot verification
- Automation target/path: evidence record (+ existing e2e patterns where scriptable)
- Result/evidence: NOT RUN

### TS-016: Anonymous guest workspace token (ADR-0006 D11)

- Protects: D11 (identity without login)
- Risk/type: Authorization / Security of the new unauthenticated surface
- Given: the deterministic stack and `POST /auth/guest-token`
- When: tokens are issued repeatedly, verified, and used; and the endpoint is exercised by the F011 inventory sweep (no token)
- Then: each token carries a unique random subject and verifies through the existing verifier; issuance creates no workspace row (the workspace appears only on first authorized use); responses disclose nothing (no other workspace subjects, no internals); every other route still rejects tokenless callers with `AUTH_REQUIRED`; token loss starts a fresh empty workspace
- Level: API / Contract integration
- Automation target/path: `apps/backend/tests/test_guest_token.py` (auto-joins `test_guardrails_isolation.py` inventory sweep)
- Result/evidence: NOT RUN

## Test Questions

- TQ-001 `RESOLVED`: Live-model need — the bounded representative journey (TS-007) may need the live adapter for provider-failure realism; the F009 harness already proves fault injection works with the fake adapter, so live use is bounded to the journey evidence and does not gate deterministic suites.
- TQ-002 `RESOLVED`: Deployment evidence as test evidence — the evidence record (Spec D5) is the operational record, not business truth; TS rows bind to it without duplicating content.
- TQ-003 `NON-CRITICAL OPEN`: TS-015 manual vs scripted split — Implementation Plan choice; if manual, the evidence record holds the checklist result.

## Gate Record: TEST DESIGN READY

- Status: `PASS` (revalidated)
- Revalidation: 2026-09-02, `YMY / Project Owner` approved via interactive session together with ADR-0006 (question-form "批准，开始实施"); revision @ `test-design-f012-r2` / `ff71c903386f` (TS-005/TS-012/TS-015 revised, TS-016 added); Plan `plan-f012-r2` valid
- Prior record (STALE):
- Validation time: 2026-09-02
- Decision Authority: `YMY / Project Owner` — coverage scope confirmed interactively on 2026-09-02 ("风险导向范围"); scenario set and this Gate approved in the same session as the Plan review
- Checklist: coverage scope confirmed; every AC mapped (AC-001..AC-010 -> TS-001..TS-015); every selected family covered by ≥1 TS; excluded families carry `N/A` reasons; no Critical Test Question OPEN/DEFERRED
- Input manifest: Spec @ `8c033df6a4e6`; UX/UI @ `36d3aa65cfaa`; `docs/TESTING.md` @ `c300110fce4d`; `AGENTS.md` @ `f68a2ee15654`; concurrent work items: none (A-012 sole claimant; F013 unclaimed)

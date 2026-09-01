# Feature Test Design: F011 Public Multi-Account Guardrails

## Metadata

- Spec/Issue: `specs/F011-public-multi-account-guardrails/spec.md` / [GitHub Issue #22](https://github.com/MaoyuanYang/LessonCanvas/issues/22)
- Validated inputs: Spec @ `d27deee5bfc8` (`SPEC READY` PASS), UX/UI @ `ux-ui-f011-r1` / `ab827a69abd6` (`UI READY` PASS)
- Test Design revision: `test-design-f011-r1` (this document, first revision)
- Environments: deterministic stack (compose services, fake adapter, eager-or-real worker as before) for TS-001..TS-014, TS-016..TS-019; scripted bounded journey TS-015 on the deterministic stack; live provider not required (limits/faults scriptable); authenticated E2E environment-gated per repo precedent
- `TEST DESIGN READY` Status: `PASS`

## Risk Register and Scenario Selection

| Risk / behavior | Impact | Scenario(s) |
| --- | --- | --- |
| Cross-account disclosure on any path | Private content/existence leak | TS-001 |
| Unbounded requests / model spend | Public demo abuse and cost | TS-002, TS-003 |
| Concurrent-run overshoot / duplicate billing | Cost and state inconsistency | TS-004 |
| Prompt/document injection via sources or metadata | Policy/tool/gate bypass | TS-005, TS-006 |
| Malicious or oversized uploads | Resource exhaustion, unsafe parsing | TS-007 |
| Student-data screening false negatives | Identifiable-data acceptance | TS-008 |
| Incomplete deletion (checkpoints, objects) / silent partial states | Privacy violation, undeletable traces | TS-009, TS-011 |
| Worker retry storm on vanished runs (F006 M-2) | Delayed settlement, noise | TS-010 |
| Unaudited sensitive access / undisclosed retention | Non-verifiable operator claims | TS-012 |
| Quota check-then-insert race (F001 residual) | Cap overshoot | TS-013 |
| Dependency/secret exposure | Known-vulnerable supply chain or leaked credentials | TS-014 |
| Limits/isolation under concurrent multi-account load | Systemic failure only visible under load | TS-015 |
| Limit/usage/deletion UI ambiguity | Teacher cannot recover or trust states | TS-016, TS-017, TS-018 |
| Regression of existing journeys under new limits | Completed features break | TS-019 |

Happy Path: TS-009/TS-012 complete paths; Alternative/boundary: TS-002/003/004/007/013; Error/security: TS-001/005/006/008/014; Recovery: TS-009/010/011; Concurrency: TS-004/013/015; Migration: TS-019 (suites auto-upgrade migrations); Performance/capacity: `N/A - no performance requirement; TS-015 is invariant evidence, not a benchmark (Spec D11)`; Visual regression: `N/A - no new visual language; compositions verified by component tests`.

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 | TS-001 |
| AC-002 | TS-002, TS-003 |
| AC-003 | TS-004 |
| AC-004 | TS-005, TS-006 |
| AC-005 | TS-007, TS-008 |
| AC-006 | TS-009, TS-010, TS-011 |
| AC-007 | TS-012 |
| AC-008 | TS-013 |
| AC-009 | TS-014 |
| AC-010 | TS-015 |
| AC-011 | TS-016, TS-017, TS-018 |

## Scenarios

### TS-001: Endpoint-inventory cross-account and unauthenticated sweep

- Protects: AC-001 (system-wide non-disclosure)
- Risk/type: Authorization sweep / Security
- Given: the mounted-route inventory (17 routers; every object-bearing route enumerated from the app, including download and SSE endpoints), two workspaces with populated resources
- When: every inventory route is exercised by the wrong owner and by no token, with both valid-shaped and foreign ids
- Then: every attempt returns the authorization-not-found class indistinguishable in shape and timing-relevant fields from a random-UUID 404, with no content, metadata, existence hints, or storage locations in the body
- Level: API / Contract (parametrized integration)
- Automation target/path: `apps/backend/tests/test_guardrails_isolation.py` (inventory-driven parametrization; route list derives from the app to prevent drift)
- Data/fixture/environment: deterministic stack; two populated teacher workspaces (existing fixture pattern)
- Result/evidence: NOT RUN

### TS-002: Request-rate window enforcement and recovery

- Protects: AC-002 (rate limits before spend)
- Risk/type: Abuse control / Boundary + Recovery
- Given: a workspace under the D2 relaxed limits (general 240/min, expensive writes 120/min), fake adapter with a call counter
- When: requests exceed the window rate on a read and on an expensive start (limit configured low for test speed via env override)
- Then: exactly the limit succeeds inside one window; excess receive the quota/rate error naming the limit with `retry_after` consistent with the fixed window; after the window boundary, requests succeed again without any manual reset; model-call counter never increases for rejected expensive starts
- Level: API + Unit (window arithmetic)
- Automation target/path: `apps/backend/tests/test_guardrails_rate.py`
- Data/fixture/environment: deterministic stack; low limit override; parallel workspaces do not collide (per-workspace keys)
- Result/evidence: NOT RUN

### TS-003: SSE concurrency and daily upload-volume caps

- Protects: AC-002 (remaining D2 limits)
- Risk/type: Resource boundary
- Given: D2 limits (6 concurrent SSE streams, 200 MB/day uploads) with low test overrides
- When: a 7th concurrent stream connects; uploads exceed the daily volume
- Then: the 7th stream is rejected with the named limit and retry guidance; over-volume uploads receive the quota error before any storage write; both recover at window/day boundary; existing streams unaffected
- Level: API / Integration
- Automation target/path: `apps/backend/tests/test_guardrails_rate.py` (stream cap), `test_guardrails_upload_policy.py` (volume cap)
- Data/fixture/environment: deterministic stack; small synthetic files
- Result/evidence: NOT RUN

### TS-004: Concurrent-run admission and idempotent convergence

- Protects: AC-003
- Risk/type: Concurrency / Idempotency
- Given: a confirmed pair with two active family runs (cap 2)
- When: a third family start is attempted; concurrently, the same start payload is submitted twice for one family; after one run settles, the blocked start is retried
- Then: the third start is rejected with the active-run pointer set; concurrent duplicates converge on one run (existing identity constraint preserved); the post-settle retry succeeds through idempotency with total model calls bounded to the runs actually executed
- Level: API / Concurrency (parallel requests)
- Automation target/path: `apps/backend/tests/test_guardrails_concurrency.py`
- Data/fixture/environment: deterministic stack; fake adapter
- Result/evidence: NOT RUN

### TS-005: Adversarial source corpus — injection and malicious metadata (D8 classes 1–2, 4)

- Protects: AC-004
- Risk/type: Prompt/document injection / Security
- Given: the versioned adversarial corpus (in-repo, checksummed; governance per the F009 dataset pattern) — injection-instruction documents, malicious filenames/metadata, and student-data-evasion samples
- When: corpus entries are uploaded, parsed, screened, and flow into a scripted planning run (fake adapter)
- Then: no entry alters tool selection, system policy, confirmation/validation gates, quota decisions, or cross-workspace visibility; screenable entries are rejected with precise source-policy errors; processed entries' prompts show the content confined to data position; every outcome is observable in traces or rejection records
- Level: Integration (+ Unit for screening fixtures)
- Automation target/path: `apps/backend/tests/test_guardrails_injection.py`; corpus ships at `apps/backend/src/lessoncanvas/adversarial_datasets/` with manifest (governance rule mirrors F009: load fails closed)
- Data/fixture/environment: deterministic stack; fake adapter
- Result/evidence: NOT RUN

### TS-006: Tool-metadata and output-field injection inertness (D8 classes 5–6)

- Protects: AC-004
- Risk/type: MCP metadata / inert rendering / Security
- Given: hostile text embedded in tool-description positions, model outputs containing UI/script payloads, and hostile F010 import fields (rubric notes, filenames)
- When: tool dispatch executes, and outputs/imported fields render in the workspace UI
- Then: dispatch remains exact-name with no dynamic grants; hostile payloads render as inert text in every surface (extending F006 D6 coverage to F010 import fields); no markup interpretation, storage escape, or policy effect
- Level: Integration (backend) + Component (web)
- Automation target/path: `apps/backend/tests/test_guardrails_tool_metadata.py`; `apps/web/__tests__/inert-rendering.test.tsx` (extension)
- Data/fixture/environment: deterministic stack; existing component harness
- Result/evidence: NOT RUN

### TS-007: Upload hardening — mismatch, oversize, decompression bombs

- Protects: AC-005 (first half)
- Risk/type: File-policy boundary / Resource safety
- Given: files with extension/content mismatch (magic-byte sniffing), oversize payloads, and zip-bomb-shaped docx containers
- When: submitted through the source and evidence-document upload paths
- Then: each is rejected at the policy boundary with the precise file-policy error; oversize is detected before full buffering; bomb extraction stays within bounded resources (no unbounded memory/CPU); nothing persists on rejection
- Level: API / Integration
- Automation target/path: `apps/backend/tests/test_guardrails_upload_policy.py`
- Data/fixture/environment: deterministic stack; tiny crafted fixtures (in-repo, no real malware)
- Result/evidence: NOT RUN

### TS-008: Student-data evasion corpus and residual risk record (F001 TQ-003 close-out)

- Protects: AC-005 (second half); F001 TQ-003
- Risk/type: Screening false negatives / Privacy
- Given: synthetic evasion-pattern samples (encoding tricks, split identifiers, mixed-language forms)
- When: screened
- Then: outcomes are recorded per sample; caught samples reject; false negatives are enumerated into the documented residual-risk record with the existing teacher-review-loop mitigation; no sample persists when rejected
- Level: Unit / Integration (screening layer) + recorded evidence
- Automation target/path: `apps/backend/tests/test_guardrails_screening.py`; residual recorded in `review.md`
- Data/fixture/environment: deterministic
- Result/evidence: NOT RUN

### TS-009: Deletion completeness incl. LangGraph checkpoints, verification and repair

- Protects: AC-006 (deletion completeness; Spec D5)
- Risk/type: Deletion / Transaction / Recovery
- Given: a project with discovery+planning runs (checkpoint rows exist for its thread ids), sources with objects, artifacts in both buckets, exports, evaluations, product-validation evidence
- When: the project is deleted; then in a fault variant an object delete fails
- Then: all governed rows including checkpoint tables are gone (per-thread verification), both buckets empty under the prefixes, the completeness check reports zero residuals; in the fault variant the project stays `deleting` with the named store, and a re-issued delete repairs to complete; reconciliation records contain ids/keys/status only
- Level: Integration (+ fault injection at the storage adapter)
- Automation target/path: `apps/backend/tests/test_guardrails_deletion.py` (extends `test_deletion.py` patterns)
- Data/fixture/environment: deterministic stack; real MinIO
- Result/evidence: NOT RUN

### TS-010: Worker fast-fail on vanished runs (Bug branch; F006 M-2 reproduction)

- Protects: AC-006 (Spec D6); F004 M-2 / F006 M-2 routed residual
- Risk/type: Bug regression / Run-teardown consistency
- Given: existing reproduction evidence (`specs/F006-layered-run-evidence/review.md` M-2: project deleted at `generating` 4/6 → `StaleDataError` on the in-flight update → two 180 s-delayed retries before terminal)
- When: a run's owning project/rows vanish mid-execution (deterministic setup: rows removed under the worker), and the worker's next lesson update hits the vanished-run class
- Then: the worker settles the terminal missing-run outcome immediately — zero delayed retries — and the settle is recorded in the run/trace records; transient provider failures still use bounded retries (negative control)
- Level: Integration (deterministic vanished-run harness; no live model needed)
- Automation target/path: `apps/backend/tests/test_guardrails_worker_fastfail.py`
- Data/fixture/environment: deterministic stack; eager or solo worker
- Result/evidence: NOT RUN (reproduction evidence exists from F006 live run; deterministic surrogate per Bug-branch rules with residual noted if the exact live race cannot be fully replayed)

### TS-011: Source/account deletion partial states and repair

- Protects: AC-006 (visible partial + repair)
- Risk/type: Partial failure / Recovery
- Given: a source whose object delete fails; an account whose cascade leaves a named store residual; the existing Clerk-failure path
- When: each failure occurs and the owner inspects and retries
- Then: the source shows the visible deletion-unresolved state with retry that converges; account deletion reports `purge_failed` with the named store and `重试修复` converges to purged; Clerk-only failure keeps its existing separate handling; retained post-deletion data matches D4(b) exactly (content-free security ledger rows only)
- Level: API / Integration
- Automation target/path: `apps/backend/tests/test_guardrails_deletion.py`
- Data/fixture/environment: deterministic stack; storage fault injection
- Result/evidence: NOT RUN

### TS-012: Download audit, audit list API, disclosure surface, D4(b) retention

- Protects: AC-007
- Risk/type: Auditability / Privacy
- Given: downloads (plans, decks, exercises, exports, evidence documents), deletions, imports performed by the owner
- When: the owner reads `GET /account/audit`; then deletes the account
- Then: every sensitive action appears as an audit event (kind + target id + time, no payloads); the list is cursor-bounded and workspace-scoped; the disclosure copy renders (component test); after account deletion the workspace audit rows are gone and only the D4(b) content-free ledger rows remain (action kind, timestamp, workspace id; verifiably no content fields)
- Level: API + Component
- Automation target/path: `apps/backend/tests/test_guardrails_audit.py`; `apps/web/__tests__/account-page.test.tsx`
- Data/fixture/environment: deterministic stack
- Result/evidence: NOT RUN

### TS-013: Count-quota atomicity under concurrent creates (F001 residual)

- Protects: AC-008
- Risk/type: Concurrency / Transaction
- Given: a workspace at projects-cap boundary (5) and a project at sources-cap boundary (10)
- When: N parallel creates race the cap on each
- Then: exactly the cap succeeds; every loser receives the quota error; no overshoot rows exist
- Level: Concurrency / Integration
- Automation target/path: `apps/backend/tests/test_guardrails_quota_atomicity.py`
- Data/fixture/environment: deterministic stack; parallel sessions/threads
- Result/evidence: NOT RUN

### TS-014: Dependency audit and secret-handling evidence

- Protects: AC-009
- Risk/type: Supply chain / Credential hygiene
- Given: the repository lockfiles and tracked tree
- When: `uv audit` and `pnpm audit` run (or the documented fallback when unavailable), and a credential-pattern scan runs over tracked files (tool or documented grep fallback) plus the existing ignored-env verification
- Then: outputs and dispositions are recorded as delivery evidence (fix or accepted-risk with reason per finding); no credential patterns exist in tracked files; `.env` remains ignored; error bodies/logs carry no secrets (spot assertions in TS-001/TS-002 responses)
- Level: Scripted evidence (not a pytest gate; recorded in `review.md` delivery evidence)
- Automation target/path: commands recorded in the Implementation Plan; evidence appended to `review.md`
- Data/fixture/environment: local tooling; documented fallback per Spec D11
- Result/evidence: NOT RUN

### TS-015: Bounded multi-account scripted journey

- Protects: AC-010
- Risk/type: Concurrency / Isolation-under-load (invariant evidence, not a benchmark)
- Given: N=5 scripted workspaces on the deterministic stack with lowered-but-proportional limits
- When: all drive the core flow concurrently (create project, upload sources, scripted answers, brief confirm, blueprint confirm, family starts) up to and beyond the limits, including duplicate submissions and a mid-flow deletion
- Then: no workspace ever observes another's content or existence; every limit behaves per D2 with accurate recovery; duplicates converge idempotently; total model calls equal the computed bound of admitted runs; the mid-flow deletion settles completely per TS-009 semantics
- Level: E2E-class orchestrated integration (API level; browser not required for the invariants)
- Automation target/path: `apps/backend/tests/test_guardrails_multiaccount_journey.py`
- Data/fixture/environment: deterministic stack; fake adapter
- Result/evidence: NOT RUN

### TS-016: Account page — usage, disclosure, audit UI (D-ACCTREGION/D-USAGE/D-DISCLOSE/D-AUDITLIST)

- Protects: AC-011 (account surfaces)
- Risk/type: UI state coverage / Accessibility
- Given: the mocked usage/audit/deletion APIs
- When: the account page renders each state (usage loaded/loading/error, audit collapsed/empty/loaded/paginating/error, disclosure static, small-screen)
- Then: every D-USAGE limit row shows current/max with reset information; audit list discloses progressively and paginates; disclosure copy visible; below 1024px the compact summary + desktop gate behave per D-SMALL; keyboard pass covers section order, expand/paginate; a11y assertions (labels, no color-alone)
- Level: Component / Interaction + Accessibility
- Automation target/path: `apps/web/__tests__/account-page.test.tsx`
- Data/fixture/environment: existing Vitest harness
- Result/evidence: NOT RUN

### TS-017: In-flow limit feedback (D-LIMITERR/D-DELEXT states)

- Protects: AC-002/AC-003/AC-006/AC-011 presentation
- Risk/type: UI error mapping / Recovery
- Given: mocked 429 (named limit + `retry_after`), admission rejection (active-run pointer), deletion partial states
- When: each surfaces in the owning component (start control, stream region, project/source rows)
- Then: rate alert shows the countdown text and usage link with retry disabled while saturated; admission shows disabled-with-reason + pointer; deletion-partial shows the named store + repair action; focus moves to the limit alert; all text+marker, no vague toast
- Level: Component / Interaction
- Automation target/path: `apps/web/__tests__/limit-feedback.test.tsx` (+ extensions to generation/deck/exercise panel tests)
- Data/fixture/environment: existing harness
- Result/evidence: NOT RUN

### TS-018: Account and guardrails E2E journey (authenticated, environment-gated)

- Protects: AC-011 end-to-end; AC-002/AC-006 user-visible paths
- Risk/type: E2E / Recovery
- Given: the authenticated E2E stack (real Clerk sign-in; repo precedent for env-gating)
- When: the teacher opens 账号与数据 (usage/disclosure/audit), triggers one in-flow limit state with a lowered test limit, deletes a fixture project to complete, and observes partial→repair on a scripted fault
- Then: the journey completes with every state truthful; recovery paths reachable
- Level: E2E (Playwright)
- Automation target/path: `apps/web/e2e/guardrails.spec.ts`; gated by `CLERK_E2E=1` with green substitute coverage (TS-016/TS-017) and a recorded resume condition when the environment blocks (F009 TS-016 / F010 TS-013 class)
- Data/fixture/environment: authenticated E2E stack
- Result/evidence: NOT RUN

### TS-019: Existing-suite regression under the new limits

- Protects: all prior Features' behavior; Spec non-regression
- Risk/type: Regression / Migration
- Given: the full backend and web suites with F011 enforcement active (per-workspace keys; defaults unchanged for single-workspace flows)
- When: the complete suites and migrations run (tests auto-upgrade)
- Then: all existing tests pass unchanged in behavior (suite fixtures either stay within defaults or override limits via env); the new migrations apply cleanly; E2E existing specs unaffected (per-workspace keys prevent cross-test collisions)
- Level: Regression (full suites)
- Automation target/path: existing `uv run pytest`, `corepack pnpm web:test`, existing E2E suites
- Data/fixture/environment: standard stacks
- Result/evidence: NOT RUN

## Scenario Selection Notes

- UIQ/D-derived states all covered: usage (TS-016), in-flow denials (TS-017), audit/disclosure (TS-016), deletion partial/repair (TS-011 backend, TS-016/017 UI, TS-018 E2E).
- Teacher memory: `N/A - F013 not implemented; binding rule recorded in Spec D8` (F013 must add its own cases per docs/TESTING.md).
- Load testing beyond invariants: `N/A - Spec D11 scopes TS-015 to invariant evidence; capacity benchmarking is out of scope`.
- Live-model evidence: `N/A - all F011 behaviors are scriptable on the fake adapter; no provider-dependent assertion exists`.

## Test Questions

| ID | Question | Severity | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Do per-workspace rate keys keep parallel test suites from colliding, and can limits be env-overridden for test speed? | Non-critical | Implementation assignee | Yes per design: keys are workspace-scoped; settings gain test overrides (existing `settings.py` env pattern); TS-002/003 use low overrides; suites otherwise run within defaults | RESOLVED |
| TQ-002 | Is authenticated E2E reliably available (historic Clerk dev-instance instability)? | Non-critical | Implementation assignee | Environment-gated with green substitute coverage and recorded resume condition, exactly the F009 TS-016 / F010 TS-013 pattern | RESOLVED |
| TQ-003 | Are `uv audit`/`pnpm audit` available in the verification environment? | Non-critical | Implementation assignee | Spec D11 permits a documented tool-availability fallback; evidence records whichever ran plus dispositions | RESOLVED |
| TQ-004 | Can the F006 M-2 live race be replayed deterministically for TS-010? | Non-critical | Implementation assignee | Deterministic vanished-run surrogate (rows removed under the worker) exercises the same code path; the F006 live reproduction remains the recorded original evidence; residual (if the exact interleaving differs) is noted per Bug-branch surrogate rules | RESOLVED |

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` verifiable with ≥1 `TS-*` | YES | AC-001..AC-011 all mapped (traceability table) |
| TR-02 | Happy Path, Alternative Flows, boundaries covered | YES | TS-009/012 complete paths; TS-002/003/004/007/013 boundaries and alternatives |
| TR-03 | Error, Auth/Security, Regression covered | YES | TS-001/005/006/008/014 security; TS-019 regression |
| TR-04 | Idempotency, Concurrency, Transaction, Consistency covered | YES | TS-004 (admission + duplicate convergence), TS-009 (deletion transaction/repair), TS-013 (quota race), TS-015 (multi-account) |
| TR-05 | Retry/timeout, migration/compat, performance covered or N/A | YES | TS-010 (retry semantics change), TS-019 (migration via auto-upgrade); performance N/A with reason (invariant-only per D11) |
| TR-06 | UI interaction/state, Accessibility, E2E per risk | YES | TS-016/017 component + a11y; TS-018 E2E (environment-gated with substitute) |
| TR-07 | Levels and automation targets appropriate | YES | All scenarios assert observable API/UI/DB/storage outcomes; TS-014 is recorded scripted evidence by design |
| TR-08 | Environment, data, fixtures, dependencies available | YES | Deterministic stack + in-repo adversarial corpus (F009 governance pattern) + env overrides; TQ-001..TQ-004 resolved |
| TR-09 | Bug reproduction/regression or confirmed surrogate | YES | TS-010 carries the recorded F006 M-2 reproduction + deterministic surrogate + residual rule (TQ-004) |
| TR-10 | No Critical Requirement unverifiable; no Critical Test Question open/deferred | YES | All TQs resolved, none Critical |
| TR-11 | Concurrent work-item integration slice or justified N/A | YES | `N/A - no concurrent work items` (F012/F013 remain DRAFT and unclaimed; STAGE verified 2026-09-01) |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec @ `d27deee5bfc8` (SPEC READY PASS) + UX/UI @ `ux-ui-f011-r1` / `ab827a69abd6` (UI READY PASS, owner-ratified) + `docs/TESTING.md` @ `445044b32bbb` + this artifact `test-design-f011-r1` (hash recorded in `STAGE.md` Gate Snapshot)
- Evidence checklist result: ALL YES (TR-01..TR-11)
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE (TQ-001..TQ-004 resolved, none Critical)
- Validated Spec revision: `d27deee5bfc8`
- Validated Test Design revision: `test-design-f011-r1` @ (hash recorded in `STAGE.md` Gate Snapshot)
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive question-form session, 2026-09-01 ("批准" for test-design-f011-r1; simultaneous "追认" of the UI READY record)
- Approval scope: F011 Test Design at `test-design-f011-r1`

## Execution Evidence Snapshot (2026-09-01)

| TS | Result / evidence |
| --- | --- |
| TS-001 | PASS — 71 openapi-derived inventory paths; cross-account + unauthenticated sweeps green (safe envelope only; workspace-self GETs assert no foreign content; destructive DELETE /account excluded with recorded reason) |
| TS-002 | PASS — general window (240/min), nested expensive window (120/min), per-workspace keys, deterministic reset (`test_guardrails_rate.py`) |
| TS-003 | PASS — SSE cap (registry saturation + real 429 + release on terminating stream) and daily upload volume (200 MB/day, per-workspace) |
| TS-004 | PASS — third family run 409 RUN_ADMISSION with active ids; duplicate convergence (identity constraint); recovery after settle; concurrent duplicates → one run |
| TS-005 | PASS — 4 prompt-injection + malicious-filename corpus entries processed through the real boundary; gates, cross-visibility, and tool dispatch unaffected; injection text confined to serialized trace data |
| TS-006 | PASS — exact-name tool dispatch against hostile metadata; inert rendering asserted via existing F006 D6 surfaces extended to F010 import fields (sniff/type checks in upload-policy suite) |
| TS-007 | PASS — extension/content mismatch classes, oversize before buffering, crafted zip-bomb docx (500 MB declared, tiny fixture), pdf page cap, entry-count guard |
| TS-008 | PASS — contiguous identifier caught (`STUDENT_DATA` rejection); spaced/split identifier false negative recorded as L-1 residual (F001 TQ-003 close-out) |
| TS-009 | PASS — checkpoint rows deleted with the project; governed-table + both-bucket verification; visible `deleting` state with named store; idempotent repair converges |
| TS-010 | PASS — StaleDataError and run-row-missing classes settle terminal `missing_run` immediately (no Celery retry); ProviderTransientError negative control keeps bounded retry; deterministic surrogate per TQ-004 (live F006 evidence remains the original reproduction) |
| TS-011 | PASS — source delete-failure visible (`delete_failed`, HTTP 200 body) and repairable; account purge keeps only the content-free D4(b) ledger |
| TS-012 | PASS — download audits on all five endpoints; `GET /account/audit` bounded + `before` cursor; ledger survives account deletion content-free |
| TS-013 | PASS — concurrent creates exactly at caps (projects 5, sources 10); workspace-resolution race adopts the winner |
| TS-014 | PASS (recorded evidence) — `uv audit` 0 findings; `pnpm audit --prod` 0 findings via workspace overrides (postcss >=8.5.18, sharp >=0.35.0, build+suite re-verified); tracked-tree credential scan clean; `.env` ignored |
| TS-015 | PASS — 5 concurrent workspaces: isolation, limit truth, idempotency, bounded spend (one run each within cap), mid-flow deletion leaves nothing |
| TS-016 | PASS — account sections render every limit, disclosure copy, audit disclosure + list, small-screen deferral (component tests incl. a11y semantics: labelled sections, aria-expanded toggle) |
| TS-017 | PASS — `guardrailFeedback` mapping (rate/upload/admission) with recovery wording; delete-failed hint with repair action |
| TS-018 | ENVIRONMENT-GATED — `e2e/guardrails.spec.ts` behind CLERK_E2E=1 (M-1 residual; resume condition in review.md); substitute coverage TS-016/TS-017 green |
| TS-019 | PASS — full suites green with guardrails active (454 backend + 83 web; migrations auto-upgrade; per-workspace keys prevent cross-test collisions) |

Execution profile: deterministic stack (fake adapter, eager tasks, compose services, real MinIO) throughout; live-model run not required by any F011 assertion.

Implementation-found defects fixed with tests before review: IF-1 content_type width (latent F001), IF-2 workspace-resolution race, IF-3 unrepairable deletion orphan, IF-4 test-harness honesty fixes — see review.md.

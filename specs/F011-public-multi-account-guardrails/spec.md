# F011: Public Multi-Account Guardrails

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #22](https://github.com/MaoyuanYang/LessonCanvas/issues/22) — bound 2026-09-01 (authorized); work-status authority
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F009` (DONE), which transitively supplies every core resource, complete trace, evaluation, export, and failure path for system-wide verification; `F010` (DONE) supplies the product-validation surfaces in scope for non-disclosure checks
- Last Updated: 2026-09-01

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-01
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-01 (question-form answers selecting D2 "更宽松" relaxed limit set, D3 "无角色+披露", D4 "保留无内容台账 (b)", D6 "纳入" fast-fail inclusion; D1/D5/D7–D11 resolved from repository evidence and confirmed together with this approval; Issue #22 creation separately authorized), scope: F011 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-011, Greenfield N/A for AS-IS row with the OBSERVED baseline inventory retained above, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F011-public-multi-account-guardrails/spec.md` @ (this file, final working-tree hash recorded in `STAGE.md` Gate Snapshot)
  - `specs/F009-technical-portfolio-evaluation/spec.md` @ `38bff6656785`
  - `specs/F010-teacher-product-validation/spec.md` @ `80de720ec874`
  - `AGENTS.md` @ `f68a2ee15654`
  - `specs/ROADMAP.md` @ (pre-READY projection, hash recorded in `STAGE.md` Gate Snapshot)
  - `docs/API.md` @ `75b1ba8665bc`
  - `docs/DATABASE.md` @ `eb1d83709f8a`
  - `docs/ARCHITECTURE.md` @ `9d26a7199d19`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/TESTING.md` @ `445044b32bbb`

## Baseline Evidence (Preflight Inventory, 2026-09-01)

All items are `OBSERVED` from code, tests, migrations, and docs at `main @ 683172b` unless labeled otherwise. This section records AS-IS facts the Feature verifies or hardens; it is not the standard.

- Ownership: every mounted API router (17 routers, ~60 endpoints) resolves a workspace from a verified token and checks project/source ownership per request; only `GET /health` is unauthenticated. Cross-account non-disclosure (404 indistinguishable from random UUID) is already covered by `teacher_b` negative cases in 13 backend test files.
- Quotas enforced today: projects per workspace (5), planning runs per workspace (50), model calls per run (20, snapshotted per run), deck/exercise run caps, sources per project (10), upload bytes (20 MB), evidence narration per workspace (50, `QuotaCounter`). Project- and source-count quotas are check-then-insert and can overshoot under true concurrency (F001 review Low finding).
- No request-rate limiting and no per-workspace concurrent-run limit exist anywhere (backend and worker); Redis is broker/result backend only.
- Upload validation is filename-extension based (`.pdf/.docx/.txt/.md`), whole-file buffered in memory, no content sniffing, no malware scanning, no decompression-bomb guard.
- Untrusted-input posture: teacher text and source-derived fields enter prompts via JSON serialization; model output passes structural validation before persistence; UI renders payloads inert (F006 D6); internal tools are static MCP-compatible definitions with exact-name dispatch and no dynamic tool granting. No pgvector/embedding retrieval exists (`pgvector` dependency unused).
- Deletion: synchronous project cascade across PostgreSQL rows and both storage buckets with per-object failure capture, `deleting` status + retry, audit rows; account cascade loops projects, then deletes `AuditEvent` rows and the workspace, records `AccountDeletionEvent`, then calls the Clerk user-deletion API. LangGraph checkpoint tables (`thread_id` = discovery run id, PostgresSaver) are NOT covered by any cascade; source delete swallows object-delete failures; no orphan verification/repair job exists.
- Audit: `audit_events` records create/delete/export/validation-import actions; artifact and evidence-document downloads are not audited; no operator/staff access path exists in the application (F006 D9 deferred operator design here).
- Credentials: `.env` files are git-ignored (only `.env.example` tracked); infra compose uses dev-only credentials; no developer-facing content logging exists in backend source; `TraceEvent.payload_json` intentionally persists full prompts/responses as owner-visible evidence (ADR-0003).
- Routed residuals with reproduction evidence: F006 M-2 / F004 M-2 worker `StaleDataError` fast-fail; F001 TQ-003 student-data false negatives; F003 D3 cost-bound assumption; F001/F002 deferred load verification; F001 D3/D11 hosted-store constraints.

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Rate/concurrency limit architecture | PostgreSQL is the single quota/rate truth (AGENTS architecture constraints; API.md quota rule). Add application-level enforcement inside the existing FastAPI boundary: fixed-window request counters and run-state-based concurrency checks in PostgreSQL using the established `QuotaCounter` pattern and conditional SQL, applied via one shared dependency/middleware. No new framework, gateway dependency, Redis-based truth, or second service; provider/infra limits remain defense in depth only. | Resolved from evidence; confirmed with Spec approval 2026-09-01 |
| D2 | Public-demo limit values and reset behavior | Relaxed set confirmed: (a) API request rate per workspace: fixed 60-second window, 240 requests/min general + 120/min for expensive write starts; (b) concurrent active generation runs per workspace: 2 across plans/decks/exercises combined (queued-not-started behavior decided in UI branch); (c) concurrent SSE streams per workspace: 6; (d) upload volume per workspace per day: 200 MB across source + evidence uploads. Reset: window boundaries are deterministic and returned to the caller (`retry_after` seconds); no manual reset, no per-run caps change. All limits are visible in the account usage surface (UI branch). | `YMY / Project Owner`, 2026-09-01 (interactive confirmation, "更宽松") |
| D3 | Operator access model | No in-app operator role or content-reading path exists or is added; the account page carries an explicit operator-access disclosure (who can reach which store, for what purpose, via which managed console) composing the existing account page pattern; infrastructure/operator access stays on managed-provider consoles as defense in depth (PRODUCT.md open-item recommendation). Sensitive application actions (downloads, deletions, imports) become auditable per D7 so the disclosure is verifiable. | `YMY / Project Owner`, 2026-09-01 (interactive confirmation, "无角色+披露") |
| D4 | Audit evidence vs account deletion | Option (b): workspace `AuditEvent` rows are still deleted with the account, and a minimal content-free retained security ledger survives account deletion — action kind, timestamp, workspace id only; never prompts, filenames, titles, or traces — disclosed in the privacy statement, satisfying the DRAFT's "audit evidence remains after content deletion" without a second content corpus, bounded to deletion/download/security events. | `YMY / Project Owner`, 2026-09-01 (interactive confirmation, "保留无内容台账 (b)") |
| D5 | Deletion completeness and reconciliation | Fix the checkpoint gap: project/account cascade additionally deletes LangGraph checkpoint rows for the project's discovery runs (tables keyed by `thread_id` = run id) inside the same transaction. Add post-cascade completeness verification and repair: after the transactional cascade, verify no residual owned rows across governed PostgreSQL tables and no residual objects under the workspace/project key prefixes in both buckets; residual findings are recorded in a metadata-only ledger (ids, keys, status — never content) and a re-issued delete/repair converges them. Source delete stops swallowing object failures: a failed object delete marks the source row deleting-failed-equivalent state visible in the existing sources surface and remains repairable. Account deletion keeps its existing Clerk step and records final status. | Resolved from evidence; confirmed with Spec approval 2026-09-01 |
| D6 | Worker fast-fail on vanished runs (F006 M-2 / F004 M-2) | Included: worker execution treats the already-reproduced vanished-run/stale-update class (project deleted or run superseded mid-flight) as an immediate settled outcome (`missing_run`-equivalent terminal state already used today) instead of two 180 s-delayed retries; bounded retries remain for transient provider failures. Reproduction evidence: `specs/F006-layered-run-evidence/review.md` M-2. | `YMY / Project Owner`, 2026-09-01 (interactive confirmation, "纳入"; requested by F006 routing) |
| D7 | Audit coverage extension | Audit events gain artifact/evidence-document download actions (target type + id only, no content) so every authorized private-object access is inspectable by the owner; the account surface exposes the owner-readable audit list behind progressive disclosure. Retention follows D4. | Resolved from evidence; confirmed with Spec approval 2026-09-01 |
| D8 | Adversarial verification corpus and injection scenarios | Ship an in-repo, versioned, self-authored synthetic adversarial corpus (the F009 dataset governance pattern: manifest, checksums, revision id, license-dedicated) covering: (1) source-document prompt injection attempting policy change, tool invocation, gate bypass, and cross-workspace exfiltration instructions; (2) malicious filenames/metadata (path traversal, control characters, homoglyphs, overlong names); (3) malformed containers (zip-bomb-shaped docx, corrupt pdf/txt/md); (4) student-data screening-evasion attempts (F001 TQ-003 revisit: synthetic evasion patterns with recorded residual risk); (5) MCP-tool-metadata injection (definitions carry hostile description text; dispatch stays exact-name and grant-free); (6) model-output and imported-evidence field injection against inert UI rendering (F006 D6 extended to F010 import fields). Assertions: no scenario alters tool selection, system policy, confirmation/validation gates, quota decisions, or cross-workspace visibility; containment is visible in the run trace. Teacher memory does not exist in Phase 1 (`F013` DRAFT): recorded `N/A - F013 must add its own injection cases per docs/TESTING.md risk map before its memory surfaces ship`. | Resolved from evidence; confirmed with Spec approval 2026-09-01 |
| D9 | Count-quota atomicity (F001 residual) | Count-based quotas (projects per workspace, sources per project) become race-safe: enforcement moves to a database-level guard (transactional recount under the existing unique/row-lock patterns, or an equivalent constraint-backed mechanism chosen by the Implementation Plan) so concurrent creates at the cap yield exactly the cap, never an overshoot. Behavior stays 429 with the existing quota error shape. | Resolved from evidence; confirmed with Spec approval 2026-09-01 |
| D10 | Provider constraint set vs deployment selection | F011 documents the verifiable constraint set for identity, object storage, model provider, and deletion guarantees (per-store deletion reachability, private-object access, region/data-residency wording for the disclosure surface) and verifies each constraint against the local reference stack (MinIO + Clerk + DeepSeek). Actual cloud provider selection and region deployment belong to `F012` (its DRAFT depends on F011 for exactly this); F011 does not select providers or deploy anything. | Resolved from evidence; confirmed with Spec approval 2026-09-01 |
| D11 | Load/concurrency verification and dependency checks | The F001/F002 deferred load verification lands as a bounded scripted multi-account journey (deterministic stack, fake adapter): N synthetic workspaces drive the core flow concurrently up to and beyond D2 limits, asserting isolation, limit accuracy, idempotency, and bounded model-call totals — invariant evidence, not a performance benchmark (TESTING.md concurrency layer rule). Dependency security: recorded `uv audit` + `pnpm audit` evidence (or documented tool-availability fallback) with a fix-or-accepted-risk disposition per finding; secret handling verified (no credentials in tracked files, `.env` ignored, no tokens in error bodies/logs). | Resolved from evidence; confirmed with Spec approval 2026-09-01 |

## Goal

Make public multi-account use of the completed LessonCanvas workflow bounded and defensible: verify and harden system-wide owner isolation, per-user cost/abuse limits, untrusted-input containment, authorized object access, disclosed and audited operational access, and complete, repairable deletion — with every denial and recovery path honest and non-disclosing.

## Business Value

Public demo use becomes evidence-backed engineering rather than an unsafe exposure: teachers get explicit privacy, limit, denial, deletion, and recovery behavior across every completed resource, and the portfolio's security claims become falsifiable (PRODUCT.md Security success criterion).

## User Story

As an individual teacher using the public demo, I want my sources, intent, runs, traces, evaluations, and files isolated, limited transparently, and deletable completely, so that I can use the demo without exposing my work or hitting ambiguous walls.

## Scope

- System-wide owner-isolation verification: an endpoint-inventory-driven adversarial sweep proving non-disclosure on every application and object path (AC basis in D8 corpus + scripted sweep).
- Visible per-user limits (D2) enforced authoritatively before expensive work (D1), with accurate recovery paths and an account usage surface.
- Adversarial source/document/prompt-injection containment evidence from the versioned corpus (D8), including student-data evasion (D8.4) and MCP metadata (D8.5).
- Upload hardening: content-type consistency checking, streaming/bounded-size handling, decompression-bomb guards (extends D8.3 hardening into policy).
- Audit extension to private-object downloads (D7) and the operator-access disclosure (D3) with its retention decision (D4).
- Deletion completeness: checkpoint-gap fix, post-cascade verification and repair ledger, visible source-delete failures (D5), and worker fast-fail on vanished runs (D6).
- Count-quota race safety (D9).
- Provider constraint documentation verified on the local stack (D10); bounded multi-account load journey and dependency/secret checks (D11).

## Out of Scope

- Enterprise compliance certification, school tenancy, RBAC administration, SSO, collaboration, or support-ticket operations (DRAFT).
- Anonymous unrestricted model use, user billing/payment (DRAFT).
- Application-owned password handling (DRAFT).
- An in-app operator console or operator content-reading path (D3 selects the no-operator-role model).
- Cloud provider selection, region deployment, and public entry infrastructure (F012; D10 boundary).
- Performance benchmarking, soak testing, or capacity sizing beyond invariant-holding bounded journeys (D11; TESTING.md).
- Redesigning quota semantics, run/version contracts, or any owning module's truth (verification and hardening only; behavior-preserving).
- Teacher-memory injection cases beyond the recorded F013 binding rule (D8).

## Actors / Preconditions

- Actor: the authenticated teacher (workspace owner) using any completed capability; the scripted adversarial tester acting as a second teacher (cross-account cases); the operator role does not exist in-app (D3).
- Preconditions: F001–F010 behavior present at `main`; reference stack (PostgreSQL, Redis, MinIO, fake or live model adapter) available; adversarial corpus imported as governed test data.

## Main Flow

1. A verified teacher uses every completed capability within visible ownership and usage limits; the usage surface shows current consumption against every D2 limit.
2. The system rejects cross-owner, over-rate, over-concurrency, unsafe-source, unauthorized-download, and injection attempts without leaking content or existence, returning the project error taxonomy with a recovery path.
3. Authorized operational access is disclosed (D3) and every sensitive action is auditable by the owner (D7).
4. The teacher deletes a project or account; all governed content — rows, checkpoints, vectors-if-any, objects, traces — is removed or reported as a repairable partial state until complete (D5); the account-deletion ledger retains only what D4 selects.

## Alternative Flows

- Over-rate burst: requests beyond the window are rejected 429 with `retry_after`; the window resets deterministically; no queued hidden work is created.
- Concurrent-run attempt while one run is active: rejected with the active-run pointer and recovery guidance (wait for settle/supersession per F007 semantics); retry after settle reuses idempotency and never double-bills.
- Mismatched or adversarial upload: rejected at policy boundary with a precise source/file-policy error; nothing persisted; the attempt is screened/auditable per existing patterns.
- Object-delete failure during project deletion: project stays `deleting`, failure recorded, re-issued delete repairs (existing behavior preserved and verified); source-level object failure becomes visible instead of swallowed (D5).
- Account deletion with partial store failure: `purge_failed` recorded with the remaining store named; repair re-issues; Clerk step records its own status (existing behavior verified).
- Vanished run detected by the worker mid-flight: settles immediately as terminal missing-run outcome; no retry storm; traces keep the settle event (D6).
- Provider outage during limit-relevant work: existing provider/transient taxonomy and bounded retry apply unchanged; limits never fabricate success.

## Business Rules / Invariants

- Managed identity proves who the caller is; PostgreSQL ownership records decide access; no client-side control is enforcement (DRAFT rule, verified system-wide).
- PostgreSQL is authoritative for quota, rate, and concurrency decisions; gateway/provider limits are defense in depth only (D1).
- Denial never discloses another workspace's content, metadata, or existence; error bodies carry the taxonomy's safe fields only.
- Source content, filenames, metadata, model output, MCP tool/server descriptions, and (future) memory content are untrusted input and can never grant tools, change policy or gates, alter quota decisions, or cross workspaces (D8).
- Account/project deletion is not complete while any owned private content remains in any governed store; partial cleanup stays visible and repairable until complete; reconciliation ledgers never retain a second content copy (D5).
- Retained post-deletion audit data is content-free and disclosed (D4); during the account's lifetime the owner can inspect sensitive-action audit rows (D7).
- A retry or duplicate never becomes a new model-cost run (F003/F007 contracts preserved and re-verified under limits).

## State Transitions

- Rate/concurrency decision per request: `allowed -> executed | rejected(429, retry_after)`; counters roll at fixed window boundaries; no persistent punitive state.
- Concurrent-run admission per workspace: `admitted(1 active)` / `rejected_with_active_pointer`; the active-run state machine is the existing run lifecycle (F003+) — F011 adds admission control only.
- Project deletion: existing `active -> deleting -> deleted` plus verified-complete; new: `deleting` with residual-ledger entries -> `deleted` only at zero residuals (D5).
- Source deletion: `ready/parsed states -> deleting -> deleted`, plus a visible object-failure state that remains repairable (D5).
- Worker vanished-run settle: `executing -> missing_run (terminal)` immediately on detection (D6).
- Account deletion: existing `purging -> purged | purge_failed(+clerk status)` with completeness verification feeding `purged` (D5).

## Data Changes

- New persisted data: rate-window counters (extend `QuotaCounter` semantics or equivalent single-table design chosen by the Implementation Plan), download audit events (existing `audit_events` shape), deletion completeness/repair ledger rows (content-free: store, key/id, status, timestamps), and — if D4 selects option (b) — a content-free retained security ledger detached from workspace lifetime. Concurrent-run admission reuses existing run columns (no new run state).
- No changes to domain tables' semantics; existing cascades gain checkpoint-table coverage; count-quota enforcement becomes constraint/transaction-backed (D9) with no observable API change beyond race safety.
- Exact tables, columns, indexes, and migration steps belong to the Implementation Plan; every F011-added row is covered by project/account deletion per its owning rule (retained-ledger rows excepted by D4 decision).

## API Behavior

- All existing endpoints keep their contracts; new failure modes use the existing taxonomy: `quota/rate-limit` (429 with window/retry-after fields and the named limit) and admission-rejection (conflict-class with active-run pointer) — exact codes per Implementation Plan.
- `GET /account/usage` — owner-authorized read of every D2 limit with current consumption and window reset times.
- `GET /account/audit` — owner-authorized, cursor-bounded list of the workspace's sensitive-action audit events (progressive disclosure; no payloads).
- Existing account deletion endpoints keep shape; responses may add completeness-verification fields (residual counts per store while `purge_failed`/`deleting`).
- No new public unauthenticated surface; `/health` unchanged.

## Error Cases

- Rate/concurrency rejection: 429/admission error naming the limit, current state, and recovery (wait/`retry_after`, active-run pointer); never content-bearing.
- Cross-owner or unauthenticated access on any F011-verified path: authorization-not-found without existence disclosure (unchanged taxonomy, sweep-verified).
- Adversarial upload/injection: source/file-policy or requirement errors with precise reasons; containment recorded; no partial persistence.
- Verification/repair failure (store unreachable during completeness check): deletion status stays incomplete with the store named; repair retriable; never silently complete.
- Dependency-audit tool unavailability: recorded fallback evidence and residual risk (D11), never a fabricated pass.

## Idempotency / Concurrency / Transactions

- Limit counters use atomic conditional SQL; concurrent requests at the boundary admit exactly the limit (same race-safety class as D9; tested concurrently).
- Concurrent-run admission is decided transactionally against run state; two simultaneous starts for the same idempotency identity still converge on one run (F003 unique-identity constraint preserved).
- Deletion remains idempotent and retry-safe; verification is read-only; repair reuses delete idempotency.
- Worker fast-fail and bounded retries never produce a second billed run for the same identity (D6 + existing cap/idempotency contracts).

## Security / Privacy / Authorization

- Every F011 surface is workspace-authorized; no new role; operator model per D3 with disclosure; audit per D4/D7.
- The adversarial corpus is synthetic, licensed, checksummed, and never derived from real teacher or student data.
- Reconciliation/audit ledgers are content-free by construction; prompts, filenames, titles, and traces never enter them.
- Secrets: verified absent from tracked files, error bodies, and logs; provider credentials stay in ignored env files.

## Non-functional

- No new infrastructure, service, cache, queue, second database, model dependency, or framework (D1); enforcement composes FastAPI dependencies, PostgreSQL, and existing patterns.
- Rate middleware overhead is O(1) queries on the quota path; expensive-work paths are guarded before model spend.
- Suites stay deterministic on the fake adapter; live-model use is not required for F011 evidence (faults and limits are scriptable) except where an existing live suite already covers the path.

## UI Impact

- UI involved: `YES`
- Affected screens: account page (usage/limits region, operator-access disclosure, audit list, deletion-status extension), quota/rate/admission error states across existing flows (generation/deck/exercise starts, uploads, narration), source deletion-failure state, and the reduced small-screen equivalents.
- Primary user flow: hit a limit -> understand it -> recover safely -> inspect usage/privacy -> delete completely.
- Major UI states: rate-limited (with reset), concurrency-rejected (with active-run pointer), quota (existing), source-delete-failed (repairable), deletion verified-complete vs partial, disclosure/audit views.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given the endpoint inventory of every mounted application route, when each object-bearing path is exercised cross-account and unauthenticated, then every attempt is refused without content, metadata, signed-object, trace, or existence disclosure, and the sweep is executable as a repeatable adversarial suite.
- AC-002: Given the D2 limits, when requests exceed the window rate, concurrency cap, or upload volume, then authoritative PostgreSQL-enforced rejection occurs before model spend, the response names the limit with reset/recovery information, and no hidden queued work is created.
- AC-003: Given a workspace with one active generation run, when any additional family run is started, then admission is rejected with the active-run pointer; after settle/supersession, start succeeds through existing idempotency with no duplicate billing; concurrent duplicate starts converge on one run.
- AC-004: Given the versioned adversarial corpus (D8 classes 1–6), when each scenario is processed through its real boundary (upload, parse, plan, generate, render, import), then no scenario alters tool selection, system policy, confirmation/validation gates, quota decisions, or cross-workspace visibility, and containment is observable in traces or rejection records.
- AC-005: Given mismatched-content, oversize, or bomb-shaped uploads, when submitted, then rejection happens at the policy boundary with bounded resource consumption and a precise file-policy error; given the student-data evasion corpus, then screening outcomes and residual false-negative risk are recorded (F001 TQ-003 close-out).
- AC-006: Given project or account deletion, when the cascade completes, then PostgreSQL rows (including LangGraph checkpoint rows), both buckets' objects, and traces are removed — verified by the completeness check with zero residuals — and when any store fails, the state remains visible and repairable until complete; given a vanished run, the worker settles it immediately as terminal without the retry storm (D6).
- AC-007: Given any artifact or evidence-document download, when completed, then an owner-inspectable audit event exists (target id only); given the account page, then the operator-access disclosure and (per D4) retention statement are visible; given account deletion, then retained audit data matches the D4 decision exactly and contains no content.
- AC-008: Given count-based quotas at their cap, when creates race concurrently, then exactly the cap succeeds and the rest receive the quota error (D9).
- AC-009: Given the dependency-audit and secret-handling checks (D11), when executed, then recorded evidence exists with a disposition per finding and no credentials appear in tracked files, error bodies, or logs.
- AC-010: Given the bounded multi-account scripted journey (D11), when N workspaces drive the core flow concurrently up to and beyond limits, then isolation holds, every limit behaves per D2, retries stay idempotent, and total model calls stay within the computed bound.
- AC-011: Given any F011-denied path, when the teacher inspects the usage/limits or error surface, then the limit, current consumption, reset/recovery path, and (for small screens) the documented reduced experience are present and truthful (UI branch refines presentation).

## Open Questions

All five DRAFT open questions and the blocking refinement decisions are resolved (D1–D11 above; Issue #22 bound 2026-09-01). Non-blocking residuals:

- [DEFERRED, Implementation Plan] Exact counter/ledger table shapes, migration steps, error-code strings, audit list payload, and disclosure wording.
- [DEFERRED, F012] Cloud provider selection and region deployment against the D10 constraint set.

## Risks and Assumptions

- [CONFIRMED] Public demo access requires verified login and per-user cost controls (DRAFT).
- [CONFIRMED] Full traces increase security and deletion risk but remain required and user-owned (ADR-0003).
- [ASSUMED, D1] A single-process application-level fixed-window limiter suffices for the demo's abuse profile; revisit only with measured contention evidence before F012 deployment.
- [ASSUMED, D11] `uv audit`/`pnpm audit` availability in the verification environment; fallback recorded if absent.
- [ASSUMED] No AV engine in Phase 1 (no new service; parser strictness + sniffing + bounded extraction as boundary) — residual risk recorded with AC-005 evidence unless the owner overrides.

## Deliberately Deferred Detail

- Counter/ledger DTOs, table columns, indexes, and migration steps (Implementation Plan + DATABASE doc sync)
- Exact error code strings and retry-after field shapes (Implementation Plan + API doc sync)
- Disclosure and usage copy wording, placement, and small-screen layout (`ux-ui.md`)
- Pixel-level UI and complete Test Design (`ux-ui.md`, `test-design.md`)

## Gate Record: DONE

- Status: `PASS`
- Validation time: 2026-09-01
- Decision Authority: `YMY / Project Owner` — full delivery flow authorized interactively on 2026-09-01 ("全部授权": commit/push/PR/merge/Issue update); merge performed as merge commit `42fd778` (PR #23)
- Conditions met:
  - All 11 ACs satisfied with automated or recorded evidence (backend 454 passed, 1 env-gated skip + ruff clean; web 83/83 + eslint 0 errors + tsc/build clean); TS-018 authenticated E2E environment-gated with green component substitute coverage and a recorded resume condition (M-1, repo precedent class)
  - Review: no Critical findings; implementation-found defects IF-1..IF-4 fixed with tests before review; residuals M-1/M-2/L-1..L-3 owner-visible in review.md and the Test Design execution snapshot
  - Security evidence: uv audit 0 findings; pnpm audit 0 findings via workspace overrides (postcss >=8.5.18, sharp >=0.35.0); tracked-tree credential scan clean
  - Documentation sync: API/DATABASE/TESTING updated with F011 resolutions; Spec enumerations truthful; ROADMAP/STAGE/Issue #22 synchronized (auto-closed by merge)
  - Delivery: PR [#23](https://github.com/MaoyuanYang/LessonCanvas/pull/23) merged `42fd778`; main re-verified (backend 454 passed + ruff clean; web 83/83 + tsc clean)
- DONE evidence manifest (working-tree SHA-256 prefixes at gate time):
  - `spec.md` @ `d27deee5bfc8` (pre-DONE content; this record appended after)
  - `ux-ui.md` @ `875da011e55e`
  - `test-design.md` @ `66c431920e95` (incl. execution snapshot)
  - `plan.md` @ `850c40e8e41a`
  - `review.md` @ `216c63239c6e`
  - `specs/ROADMAP.md` @ `e9f799d3445c` (pre-DONE)
- Follow-up (owner-visible, non-blocking): run the authenticated guardrails E2E under stable auth and append evidence (M-1); F012 must verify the D10 provider constraint set against the actually selected cloud providers and re-check the SSE single-process assumption for the deployed topology.

# Test Design: F001 Grounded Confirmed Brief

## Inputs and Environment

- Spec/Gate/revision: `specs/F001-grounded-confirmed-brief/spec.md` — `SPEC READY: PASS` @ `d7ae5094c490`
- UX/UI/Gate/revision: `specs/F001-grounded-confirmed-brief/ux-ui.md` — `UI READY: PASS` @ `c4cd127cb372`
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (contain full manifests; VCS base `de9306d`)
- Test Design revision/change-log ID: `test-design-f001-r1`
- Issue: [GitHub Issue #1](https://github.com/MaoyuanYang/LessonCanvas/issues/1)
- Test strategy/conventions: `docs/TESTING.md` risk map and layers. Proposed toolchain (established by Implementation Plan Task 0, commands then synced to AGENTS/README/TESTING): pytest + httpx (unit/integration/API), Vitest + Testing Library (component/interaction), Playwright (E2E), ruff/tsc for static checks. Deterministic CI uses fakes for DeepSeek and Clerk; controlled live-model runs stay separate per AGENTS.md.
- Environment/services: local docker compose providing PostgreSQL+pgvector, Redis, MinIO; FastAPI app + Celery worker under test; Next.js dev server for E2E. DeepSeek replaced by a scripted fake provider in deterministic suites; Clerk replaced by verifiable test sessions (Clerk dev instance / signed test tokens).
- Test data/fixtures: synthetic senior-high English unit materials (public/created for tests); adversarial fixtures for injection and student-data detection; standards snapshot fixture subset mirroring the bundled snapshot schema.
- Known constraints: no scaffold exists yet; toolchain bootstrap is implementation work of this Feature. Heuristic student-data detection has residual false negatives (recorded, teacher review loop mitigates).

## Risk Inventory

| Risk/invariant | Impact | Likelihood | Evidence | Planned coverage |
| --- | --- | --- | --- | --- |
| Cross-account disclosure | Private teacher material leaks | Medium | TESTING.md top risk | TS-003 adversarial API |
| Student data enters grounding | Privacy violation | Medium | Spec rule | TS-005 |
| Prompt/document injection via sources or snapshot | Policy bypass, tool grant, cross-workspace leak | Medium | TESTING.md risk map | TS-016, TS-017 |
| Confirmed version mutated / stale overwrite | Intent corruption | Medium | DATABASE.md concurrency | TS-012, TS-013, TS-014 |
| Duplicate discovery runs / duplicate model cost | Cost + state corruption | Medium | API.md idempotency | TS-014, TS-015, TS-020 |
| Streaming stop loses content or duplicates work | Teacher loses answers; trace incomplete | Medium | API.md streaming rules | TS-010 |
| Provider failure loses interview state | Teacher restarts from zero | Medium | DeepSeek availability unknown | TS-020, TS-025 |
| Deletion leaves orphaned content | Privacy violation | Medium | DATABASE.md deletion | TS-018, TS-019, TS-026 |
| Questioning harasses or drifts | Bad first Agent experience | Medium | D9 rule | TS-007, TS-008, TS-009 |
| Ungrounded draft fields | Teacher cannot trust brief | Medium | Core value | TS-011, TS-016 |
| Small-screen attempts structured tasks | Broken/confusing experience | Low | D10 boundary | TS-022 |

## Acceptance Traceability

| Acceptance | Scenario IDs | Test level | Automated target/path | Status/evidence |
| --- | --- | --- | --- | --- |
| AC-001 | TS-001 | Integration/API/E2E | backend auth tests; E2E sign-in | DESIGNED |
| AC-002 | TS-002, TS-024 | API/E2E | project CRUD suite | DESIGNED |
| AC-003 | TS-003 | API (adversarial) | isolation suite | DESIGNED |
| AC-004 | TS-004, TS-022 | API/Component | upload policy suite | DESIGNED |
| AC-005 | TS-005 | Integration | student-data fixtures | DESIGNED |
| AC-006 | TS-006 | Integration | source lifecycle suite | DESIGNED |
| AC-007 | TS-007, TS-008, TS-024 | Unit/Integration/E2E | questioning-rule suite | DESIGNED |
| AC-008 | TS-009, TS-022 | Unit/Component | round-cap suite | DESIGNED |
| AC-009 | TS-010 | API/Integration | SSE stop suite | DESIGNED |
| AC-010 | TS-011 | API | draft grounding suite | DESIGNED |
| AC-011 | TS-012, TS-022 | API/Component | revision + conflict suite | DESIGNED |
| AC-012 | TS-013, TS-014, TS-024 | Integration/Concurrency/E2E | confirmation suite | DESIGNED |
| AC-013 | TS-013 | Integration | version authority suite | DESIGNED |
| AC-014 | TS-016 | Integration | MCP tool + citation suite | DESIGNED |
| AC-015 | TS-018 | Integration | deletion cascade suite | DESIGNED |
| AC-016 | TS-019 | Integration | account deletion suite (Clerk fake) | DESIGNED |
| AC-017 | TS-020, TS-025 | Integration/E2E | provider failure suite | DESIGNED |
| AC-018 | TS-010, TS-025 | Integration/E2E | reconnect suite | DESIGNED |
| AC-019 | TS-022, TS-023 | Component/Accessibility | reduced-boundary + a11y suite | DESIGNED |

## Test Scenarios

### TS-001: Workspace bootstrap from verified session

- Protects: `AC-001`
- Risk/type: Auth / Happy
- Given: a valid Clerk session for a new teacher / an existing teacher
- When: the app is entered with the session token
- Then: a workspace is created exactly once (new) or resolved (existing); missing/expired/forged tokens yield authentication errors and never a workspace
- Level: Integration + API
- Automation target/path: backend integration (identity module) + API auth suite
- Data/fixture/environment: Clerk fake issuing verifiable test tokens
- Result/evidence: NOT RUN

### TS-002: Project CRUD owner-scoped

- Protects: `AC-002`
- Risk/type: Happy
- Given: authenticated workspace
- When: teacher creates (name, optional hints), lists, resumes (GET), and deletes projects
- Then: operations succeed owner-scoped; list shows status/phase/last activity; duplicate creation under quota behaves per quota rules
- Level: API
- Automation target/path: project API suite
- Data/fixture/environment: synthetic projects; quota fixture at limit
- Result/evidence: NOT RUN

### TS-003: Cross-account non-disclosure

- Protects: `AC-003`
- Risk/type: Auth / Security (adversarial)
- Given: teacher A owns project/source/brief; teacher B authenticated
- When: B requests A's project, source, discovery stream, brief, or trace by ID (guess/enumeration)
- Then: every response is a safe not-found with no existence or content disclosure; B's list never contains A's resources
- Level: API (adversarial)
- Automation target/path: isolation suite (mandatory cross-owner negatives per TESTING.md)
- Data/fixture/environment: two seeded workspaces
- Result/evidence: NOT RUN

### TS-004: Upload policy enforcement

- Protects: `AC-004`
- Risk/type: Boundary / Error
- Given: project with k sources
- When: uploads with disallowed format, size >20MB, or the 11th file are submitted; a valid file is submitted
- Then: violations are rejected with the specific policy code and recovery guidance and never enter grounding; the valid file moves to processing
- Level: API
- Automation target/path: upload policy suite
- Data/fixture/environment: generated oversized binary; wrong-extension fixture
- Result/evidence: NOT RUN

### TS-005: Student-data rejection before grounding

- Protects: `AC-005`
- Risk/type: Security / Boundary
- Given: a file containing identifiable student data patterns (synthetic)
- When: it is uploaded and processed
- Then: it is rejected with a safe explanation before any retrieval availability; no rejected content appears in retrieval results or grounding citations
- Level: Integration
- Automation target/path: source-policy suite with synthetic student-data fixtures
- Data/fixture/environment: synthetic fixtures only; no real student data
- Result/evidence: NOT RUN

### TS-006: Source lifecycle states

- Protects: `AC-006`
- Risk/type: Happy / Error
- Given: accepted uploads
- When: parsing succeeds for one and fails for another (corrupt fixture)
- Then: states become ready / failed respectively and are visible via API; failed source is excluded from retrieval; ready source is retrievable
- Level: Integration
- Automation target/path: source lifecycle suite (Celery worker against compose services)
- Data/fixture/environment: valid PDF/DOCX/TXT/MD fixtures; corrupt fixture
- Result/evidence: NOT RUN

### TS-007: Questioning asks only required gaps within limits

- Protects: `AC-007`
- Risk/type: Happy / Rule
- Given: ready sources covering some of the seven required fields
- When: discovery runs with scripted model responses
- Then: questions target only unfilled required fields; each round has <=3 questions; agent-led rounds never exceed 6; no small-talk content appears
- Level: Unit (orchestration rules with stubbed model) + Integration (workflow)
- Automation target/path: discovery-rule unit suite; workflow integration
- Data/fixture/environment: scripted fake model; fixture sources with known coverage
- Result/evidence: NOT RUN

### TS-008: No gaps produces immediate draft

- Protects: `AC-007`
- Risk/type: Alternative flow
- Given: sources + teacher hints already satisfy all seven fields
- When: discovery starts
- Then: no question round occurs; the structured draft is produced directly
- Level: Unit/Integration
- Automation target/path: discovery-rule suite
- Data/fixture/environment: complete-coverage fixture
- Result/evidence: NOT RUN

### TS-009: Round cap marks unresolved gaps; teacher may continue

- Protects: `AC-008`
- Risk/type: Boundary
- Given: scripted model that cannot resolve two fields within 6 rounds
- When: the cap is reached
- Then: the draft presents with those fields explicitly marked unresolved; teacher-initiated answers after the cap are accepted and update the draft
- Level: Unit/Integration + Component (gap markers)
- Automation target/path: round-cap suite; brief panel component test
- Data/fixture/environment: scripted fake model
- Result/evidence: NOT RUN

### TS-010: Streaming stop, trace integrity, re-ask, reconnect

- Protects: `AC-009`, `AC-018`, trace invariant
- Risk/type: UI/API / Concurrency
- Given: a streaming interview response in flight
- When: the teacher stops display; later reconnects after disconnect; later presses explicit re-ask
- Then: stop only interrupts display — the model call completes and the full response exists in the owner-scoped trace; reconnect resumes from authoritative state without duplicating model work; re-ask starts exactly one new quota-counted response
- Level: API/Integration (SSE harness)
- Automation target/path: SSE stop/reconnect suite
- Data/fixture/environment: scripted fake model with delayed token stream
- Result/evidence: NOT RUN

### TS-011: Draft grounding display contract

- Protects: `AC-010`
- Risk/type: Happy / Contract
- Given: a produced draft
- When: the brief draft is fetched
- Then: all seven fields are present; each evidence-based field carries citation references (private source or standards snapshot version) or an explicit teacher-stated marker
- Level: API (contract)
- Automation target/path: brief contract suite
- Data/fixture/environment: fixture run with known citations
- Result/evidence: NOT RUN

### TS-012: Structured correction and stale conflict

- Protects: `AC-011`
- Risk/type: Happy / Error / Concurrency
- Given: draft revision N
- When: a correction is saved with base N; a second correction is submitted with stale base N-1
- Then: first save creates revision N+1; stale submission returns the version-conflict error class; no silent overwrite
- Level: API
- Automation target/path: revision suite
- Data/fixture/environment: seeded draft
- Result/evidence: NOT RUN

### TS-013: Confirmation atomicity and immutability

- Protects: `AC-012`, `AC-013`
- Risk/type: Happy / Error / Transaction
- Given: draft with missing required fields / draft with all seven non-empty; a confirmed version exists
- When: confirm is attempted in each state; a correction targets the confirmed version
- Then: incomplete confirm returns requirement error naming missing fields; complete confirm atomically creates immutable version; the confirmed version is never mutated; later correction starts a new draft cycle; downstream planning input resolves only to the confirmed version
- Level: Integration
- Automation target/path: confirmation suite (PostgreSQL transaction boundary)
- Data/fixture/environment: seeded drafts
- Result/evidence: NOT RUN

### TS-014: Concurrent confirmation and duplicate starts

- Protects: `AC-012`, idempotency invariants
- Risk/type: Concurrency
- Given: one draft and two simultaneous confirm requests; one active discovery run and a duplicate start
- When: they race
- Then: exactly one immutable version is created (same version returned to both); duplicate discovery start returns the existing active run; database constraints (not UI) enforce both
- Level: Concurrency/Integration
- Automation target/path: concurrency suite against real PostgreSQL
- Data/fixture/environment: parallel request harness
- Result/evidence: NOT RUN

### TS-015: Single active discovery run per project

- Protects: run invariant
- Risk/type: Concurrency
- Given: an active discovery run
- When: start is requested again (double submit, retry)
- Then: no second run is created; no duplicate model cost; state remains consistent
- Level: Concurrency/API
- Automation target/path: discovery lifecycle suite
- Data/fixture/environment: scripted fake model
- Result/evidence: NOT RUN

### TS-016: Standards snapshot retrieval, citation, and untrusted metadata

- Protects: `AC-014`
- Risk/type: Integration / Security
- Given: the bundled standards snapshot and the internal MCP-compatible retrieval tool
- When: grounding retrieves standards evidence; a snapshot fixture carries hostile tool/server-style metadata
- Then: citations record snapshot version; retrieval stays inside the configured snapshot; hostile metadata cannot grant tools, change policy, or surface other workspaces
- Level: Integration
- Automation target/path: MCP tool boundary suite (per TESTING.md adversarial MCP cases)
- Data/fixture/environment: snapshot fixture subset + adversarial metadata fixture
- Result/evidence: NOT RUN

### TS-017: Injection defense through private sources

- Protects: untrusted-input invariant
- Risk/type: Security (adversarial)
- Given: a source containing prompt-injection payloads ("ignore instructions", tool-grant attempts, cross-project probes)
- When: discovery uses it for grounding
- Then: system policy unchanged; no tool grants; no other-workspace disclosure; outputs remain within the interview contract
- Level: Integration (adversarial corpus per TESTING.md)
- Automation target/path: injection suite
- Data/fixture/environment: adversarial source fixtures
- Result/evidence: NOT RUN

### TS-018: Project deletion cascade with partial failure

- Protects: `AC-015`
- Risk/type: Recovery / Error
- Given: project with sources, vectors, objects, drafts, versions, traces
- When: deletion runs; in a second case MinIO deletion is injected to fail
- Then: success case removes all rows/vectors/objects and writes a non-content audit row; failure case leaves a visible failed-deletion state and an idempotent retry completes the cascade
- Level: Integration
- Automation target/path: deletion suite with injected MinIO failure
- Data/fixture/environment: compose services; failure injection point
- Result/evidence: NOT RUN

### TS-019: Account deletion ordering

- Protects: `AC-016`
- Risk/type: Recovery
- Given: workspace with data and a Clerk fake
- When: account deletion is requested; in a second case the Clerk call fails
- Then: workspace data is purged before the Clerk user-deletion call; failure leaves a visible state with recovery path; ordering is enforced by the application, not the provider
- Level: Integration
- Automation target/path: account deletion suite
- Data/fixture/environment: Clerk fake with controllable failure
- Result/evidence: NOT RUN

### TS-020: Provider failure preserves state

- Protects: `AC-017`, no-duplicate-cost invariant
- Risk/type: Error / Recovery
- Given: scripted fake model injecting timeout/outage mid-interview
- When: the failure occurs and the teacher retries
- Then: named provider/transient error class; draft/run state preserved; retry resumes the same run without re-executing completed model work
- Level: Integration
- Automation target/path: provider failure suite
- Data/fixture/environment: scripted failures
- Result/evidence: NOT RUN

### TS-021: Quota enforcement before expensive work

- Protects: quota invariant
- Risk/type: Boundary
- Given: workspace at quota limit (projects or model calls)
- When: a new expensive operation is requested
- Then: quota/rate-limit error class with guidance; no model call is issued; quota state comes from PostgreSQL, never client claims
- Level: Unit + API
- Automation target/path: quota suite
- Data/fixture/environment: seeded quota counters
- Result/evidence: NOT RUN

### TS-022: Workspace component states

- Protects: `AC-004`, `AC-008`, `AC-010`, `AC-011`, `AC-012`, `AC-019` (UI surfaces)
- Risk/type: UI / Interaction
- Given: mocked API states per the UX/UI state matrix
- When: the teacher views sources/brief/discovery surfaces
- Then: rejection alerts name rules; gap markers visible; confirm disabled with missing-field reasons; stale conflict banner offers reload; small-screen viewport shows read-only + conversational answering with desktop-required messages on structured tasks
- Level: Component/Interaction (Vitest + Testing Library)
- Automation target/path: component suite per surface
- Data/fixture/environment: API mocks; viewport presets >=1024 / <1024
- Result/evidence: NOT RUN

### TS-023: Accessibility of the confirm journey

- Protects: `AC-019`, WCAG 2.2 AA obligation
- Risk/type: Accessibility
- Given: the sign-in -> create -> answer -> confirm journey
- When: operated by keyboard only
- Then: every action reachable; focus moves to results/errors per UX rules; streamed text announced in throttled batches; statuses not color-only; automated checks plus recorded manual pass
- Level: Accessibility
- Automation target/path: automated a11y checks in component/E2E + manual checklist evidence
- Data/fixture/environment: E2E environment
- Result/evidence: NOT RUN

### TS-024: E2E happy path

- Protects: `AC-001`, `AC-002`, `AC-007`, `AC-012`
- Risk/type: Happy / E2E
- Given: teacher with Clerk dev session and synthetic sources
- When: full journey sign-in -> project -> upload -> discovery (scripted model) -> draft -> correction -> confirm
- Then: confirmed brief version visible with evidence; authoritative state consistent across reload
- Level: E2E (Playwright)
- Automation target/path: E2E suite
- Data/fixture/environment: compose stack + Clerk dev + fake model
- Result/evidence: NOT RUN

### TS-025: E2E failure and reconnect recovery

- Protects: `AC-017`, `AC-018`
- Risk/type: Error / E2E
- Given: interview in progress
- When: provider failure is injected; separately, the connection drops mid-stream
- Then: named provider error with retry that preserves state; reconnect resumes without duplicate work or new run
- Level: E2E
- Automation target/path: E2E recovery suite
- Data/fixture/environment: failure injection in fake model
- Result/evidence: NOT RUN

### TS-026: Trace completeness and deletion

- Protects: trace invariant, `AC-015`
- Risk/type: Observability / Privacy
- Given: a completed discovery run
- When: its trace is read by the owner; the project is then deleted
- Then: trace contains prompts, responses, citations, tool usage, latency, cost within owner scope; after deletion no trace content remains
- Level: Integration
- Automation target/path: trace suite + deletion assertions
- Data/fixture/environment: seeded run
- Result/evidence: NOT RUN

## Non-functional and Compatibility Coverage

- Idempotency/duplicate: TS-012, TS-014, TS-015, TS-020
- Concurrency/transaction/consistency: TS-013, TS-014 (real PostgreSQL constraints)
- Retry/timeout/recovery: TS-018, TS-019, TS-020, TS-025
- Migration/backward compatibility: initial migrations are exercised by integration bootstrap; backward compatibility `N/A - greenfield, no existing consumers`
- Performance/capacity: latency/cost captured per run (TS-026); load testing `N/A - deferred to F009/F011 per ROADMAP`
- Security/privacy: TS-003, TS-005, TS-016, TS-017
- Observability: TS-026

## UI Coverage

- Interaction/navigation: TS-022, TS-024
- Loading/Empty/Error/Success: TS-022 (state matrix mocks), TS-024 (E2E success), TS-025 (error)
- Permission/validation: TS-003 (API), TS-022 (validation/disabled reasons), TS-024 (auth entry)
- Responsive: TS-022 viewport presets implementing the 1024px boundary (D-BP)
- Accessibility: TS-023
- E2E/visual regression: E2E TS-024/TS-025; visual regression baseline established for workspace shell + brief panel during implementation (first UI Feature; no broad screenshot churn)

## Open Test Questions

| ID | Question/blocker | `Critical/Non-critical` | Owner | Resolution/unblock condition | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Live DeepSeek cost/variance in CI | Non-critical | Implementation assignee | Deterministic CI uses scripted fake provider; live-model evaluation runs separately per AGENTS.md Build and Test | RESOLVED |
| TQ-002 | Clerk sessions in automated tests | Non-critical | Implementation assignee | Clerk dev instance + verifiable test tokens; identity boundary still exercised via token verification | RESOLVED |
| TQ-003 | Student-data detection false negatives | Non-critical | Implementation assignee | Synthetic adversarial fixtures + documented residual risk; teacher review loop mitigates; revisit with F011 | RESOLVED |
| TQ-004 | Toolchain bootstrap (no scaffold exists) | Non-critical | Implementation assignee | Established by Implementation Plan Task 0; AGENTS/README/TESTING synced when commands exist | RESOLVED |

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` is verifiable and maps to at least one `TS-*`. | YES | Acceptance Traceability table covers AC-001..AC-019 |
| TR-02 | Happy Path, major Alternative Flows, and boundaries are covered. | YES | TS-001/002/011/024 happy; TS-008/009/010 alternatives; TS-004/021 boundaries |
| TR-03 | Error, Authentication/Security, and Regression risks are covered. | YES | TS-003/005/016/017 security; TS-006/020 errors; regression via automated suites as baseline |
| TR-04 | Idempotency, Concurrency, Transaction, and Consistency are covered or justified N/A. | YES | TS-012/013/014/015 |
| TR-05 | High-risk Retry/Timeout, Migration/Compatibility, performance, and similar concerns are covered or justified N/A. | YES | TS-018/019/020/025; migration/compat and load N/A reasons recorded above |
| TR-06 | UI interaction/state, Accessibility, and E2E are covered according to risk or justified N/A. | YES | TS-022/023/024/025; visual baseline scoped |
| TR-07 | Test levels and automation targets are appropriate and MUST NOT target only implementation details. | YES | All scenarios assert observable API/UI/DB outcomes, not private calls |
| TR-08 | Environment, data, fixtures, and external dependencies are available, or alternative verification is confirmed. | YES | Compose services + fakes for DeepSeek/Clerk confirmed; fixtures synthetic; bootstrap is Plan Task 0 (TQ-004) |
| TR-09 | A Bug has reproduction evidence and a regression scenario, or a confirmed evidence-based surrogate, alternative verification, and residual risk. | YES | `N/A - new Feature, no Bug`; section retained with this reason |
| TR-10 | No Critical Requirement is unverifiable, and no Critical Test Question is `OPEN` or `DEFERRED`. | YES | Open Test Questions all RESOLVED, none Critical |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `d7ae5094c490`, UX/UI `c4cd127cb372`, plus their Gate Record manifests (base `de9306d`), and this artifact `test-design-f001-r1` @ `dc6978dfefc8`
- Evidence checklist result: ALL YES
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `d7ae5094c490`
- Validated UI revision or complete skip-decision link: `c4cd127cb372`
- Validated Test Design revision: `test-design-f001-r1` @ `dc6978dfefc8`
- Validated at: 2026-08-24
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-24
- Approval scope: F001 Test Design at `test-design-f001-r1`

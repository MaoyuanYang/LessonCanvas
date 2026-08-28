# Test Design: F002 Confirmed Unit Blueprint

## Inputs and Environment

- Spec/Gate/revision: `specs/F002-confirmed-unit-blueprint/spec.md` — `SPEC READY: PASS` @ `108178994342`
- UX/UI/Gate/revision: `specs/F002-confirmed-unit-blueprint/ux-ui.md` — `UI READY: PASS` @ `a8cfd23189ac`
- Upstream input manifest link/revisions: Spec Gate Record and UI READY Record (contain full manifests; VCS base `8bf078e`)
- Test Design revision/change-log ID: `test-design-f002-r1`
- Issue: [GitHub Issue #3](https://github.com/MaoyuanYang/LessonCanvas/issues/3)
- Test strategy/conventions: `docs/TESTING.md` risk map and layers; toolchain established by F001 (pytest + httpx, Vitest + Testing Library, Playwright, ruff/tsc). Deterministic suites use the FakeModelAdapter and faked Clerk sessions; live-model evidence stays separate per AGENTS.md.
- Environment/services: local docker compose (PostgreSQL+pgvector, Redis, MinIO); FastAPI app + Celery worker; Next.js dev server for E2E. DeepSeek replaced by scripted FakeModelAdapter scenarios; Clerk via token fixtures (F001 harness).
- Test data/fixtures: synthetic confirmed briefs (seven fields) seeded through the existing brief service; synthetic blueprint payloads (unit objectives, lessons) at, below, and above the brief lesson count; standards-snapshot fixture subset with adversarial metadata; adversarial injection sources.
- Known constraints: authenticated E2E remains limited by Clerk device-verification (F001 residual B-001); F002 E2E extends the existing authenticated suite under the same constraint. The representative real unit is not selected (Spec NON_BLOCKING); all fixtures are synthetic.

## Risk Inventory

| Risk/invariant | Impact | Likelihood | Evidence | Planned coverage |
| --- | --- | --- | --- | --- |
| Blueprint confirms against wrong/stale brief version | Downstream generation follows wrong intent | Medium | DATABASE.md version binding | TS-001, TS-011, TS-018 |
| Completeness checks bypassed | Invalid blueprint authorizes generation | Medium | Spec D1 | TS-007, TS-009 |
| Blocking finding decided instead of corrected | Authority corruption | Medium | Spec D3 | TS-008 |
| Waivable finding decided without recorded reason | Untraceable teacher decision | Medium | Spec D3, audit rules | TS-008, TS-017 |
| Stale blueprint authorizes downstream work | Stale overwrite | Medium | API.md supersession | TS-011, TS-018 |
| Duplicate planning runs / duplicate model cost | Cost + state corruption | Medium | API.md idempotency | TS-001, TS-010 |
| Cross-account disclosure of planning/blueprint/findings/trace | Private material leaks | Medium | TESTING.md top risk | TS-013 |
| Injection via sources or snapshot during planning | Policy bypass / tool grant | Medium | ADR-0004, TESTING.md | TS-012, TS-016 |
| Provider failure loses planning state | Teacher restarts from zero | Medium | DeepSeek availability | TS-014 |
| Streaming stop loses content or duplicates work | Trace incomplete / duplicate cost | Medium | API.md streaming | TS-015 |
| Questioning drift in planning | Bad interview experience | Low | D5 caps (F001-proven pattern) | TS-002, TS-004 |
| Small-screen attempts structured blueprint tasks | Broken experience | Low | Spec D8 | TS-021, TS-022 |

## Acceptance Traceability

| Acceptance | Scenario IDs | Test level | Automated target/path | Status/evidence |
| --- | --- | --- | --- | --- |
| AC-001 | TS-001, TS-010, TS-020 | Integration/API/Concurrency | `tests/test_planning.py` | DESIGNED |
| AC-002 | TS-002, TS-003 | Unit/Integration | `tests/test_planning.py` | DESIGNED |
| AC-003 | TS-004 | Integration + Component | `tests/test_planning.py`; blueprint panel component test | DESIGNED |
| AC-004 | TS-005, TS-023 | API (contract) | `tests/test_blueprint.py` | DESIGNED |
| AC-005 | TS-006, TS-021 | API/Component | `tests/test_blueprint.py` | DESIGNED |
| AC-006 | TS-007, TS-021 | API + Component | `tests/test_blueprint.py` | DESIGNED |
| AC-007 | TS-008, TS-021 | API + Component | `tests/test_blueprint.py` | DESIGNED |
| AC-008 | TS-009, TS-010, TS-023 | Integration/Concurrency | `tests/test_blueprint.py` | DESIGNED |
| AC-009 | TS-011, TS-024 | Integration/E2E | `tests/test_blueprint.py` | DESIGNED |
| AC-010 | TS-012 | Integration (adversarial) | `tests/test_planning.py` + standards tool suite | DESIGNED |
| AC-011 | TS-013 | API (adversarial) | isolation suite extension | DESIGNED |
| AC-012 | TS-014 | Integration | `tests/test_planning.py` | DESIGNED |
| AC-013 | TS-015 | API/Integration (SSE) | SSE suite extension | DESIGNED |
| AC-014 | TS-021, TS-022 | Component/Accessibility | blueprint panel suite + a11y pass | DESIGNED |
| AC-015 | TS-017 | Integration | trace + deletion suite extension | DESIGNED |
| AC-016 | TS-011, TS-018 | API/Integration | `tests/test_blueprint.py` | DESIGNED |

## Test Scenarios

### TS-001: Planning start binds brief version, idempotent, gated

- Protects: `AC-001`
- Risk/type: Happy / Idempotency / Boundary
- Given: a project with confirmed brief version v1; a project without a confirmed brief; a workspace at quota limit
- When: planning start is requested (including double submit)
- Then: with brief, an active run is created bound to v1 and duplicate starts return the same run; without brief, a requirement error directs to the brief gate; at quota, a quota error is returned and no run or model call is created
- Level: Integration/API
- Automation target/path: `apps/backend/tests/test_planning.py`
- Data/fixture/environment: seeded briefs via brief service; quota counter fixture at limit; FakeModelAdapter
- Result/evidence: NOT RUN

### TS-002: Planning questions only material gaps within 6x3 caps

- Protects: `AC-002`
- Risk/type: Rule / Happy
- Given: a confirmed brief with planning gaps (ambiguous objective split, missing period intent) and ready sources
- When: planning runs with scripted model responses
- Then: questions target only material planning gaps; each round has <=3 questions; agent-led rounds never exceed 6; answers become structured state
- Level: Unit (orchestration rules) + Integration (workflow)
- Automation target/path: `apps/backend/tests/test_planning.py` (graph rules with stubbed model)
- Data/fixture/environment: FakeModelAdapter scripted scenarios; gap-rich brief fixture
- Result/evidence: NOT RUN

### TS-003: Zero planning gaps produces immediate draft

- Protects: `AC-002` (alternative flow)
- Risk/type: Alternative flow
- Given: a complete, unambiguous confirmed brief and sufficient sources
- When: planning starts
- Then: no question round occurs; the blueprint draft is produced directly
- Level: Unit/Integration
- Automation target/path: `apps/backend/tests/test_planning.py`
- Data/fixture/environment: complete-coverage fixture
- Result/evidence: NOT RUN

### TS-004: Round cap marks unresolved planning gaps; teacher may continue

- Protects: `AC-003`
- Risk/type: Boundary
- Given: a scripted model that cannot resolve two planning gaps within 6 rounds
- When: the cap is reached
- Then: the draft presents with those gaps explicitly marked unresolved; teacher-initiated answers or hand edits after the cap are accepted and update the draft
- Level: Integration + Component (gap markers)
- Automation target/path: `apps/backend/tests/test_planning.py`; blueprint panel component test
- Data/fixture/environment: FakeModelAdapter scripted unresolvable gaps
- Result/evidence: NOT RUN

### TS-005: Draft structure and citation contract

- Protects: `AC-004`
- Risk/type: Contract / Happy
- Given: a produced blueprint draft
- When: the blueprint is fetched
- Then: the complete unit appears with lesson count matching the brief; every lesson carries title, >=1 objective referencing a unit objective, and assessment intent; unit objectives and lesson items carry citations (private source reference or standards-snapshot version) or explicit markers
- Level: API (contract)
- Automation target/path: `apps/backend/tests/test_blueprint.py`
- Data/fixture/environment: fixture run with known citations
- Result/evidence: NOT RUN

### TS-006: Structured correction and stale conflict

- Protects: `AC-005`
- Risk/type: Happy / Error / Concurrency
- Given: blueprint draft revision N
- When: a correction is saved with base N; a second correction is submitted with stale base N-1
- Then: first save creates revision N+1; stale submission returns the version-conflict error class; no silent overwrite
- Level: API
- Automation target/path: `apps/backend/tests/test_blueprint.py`
- Data/fixture/environment: seeded draft
- Result/evidence: NOT RUN

### TS-007: Blocking findings reject confirmation with named items

- Protects: `AC-006`
- Risk/type: Error / Rule
- Given: four draft variants failing each hard check (lesson count mismatch, missing required lesson field, objective coverage gap, missing lesson)
- When: confirmation is requested on each
- Then: each is rejected with a requirement error naming the failed check and affected lessons/objectives; no version is created
- Level: API
- Automation target/path: `apps/backend/tests/test_blueprint.py`
- Data/fixture/environment: four synthetic invalid payloads
- Result/evidence: NOT RUN

### TS-008: Waivable findings require fix or recorded decision

- Protects: `AC-007`
- Risk/type: Rule / Happy
- Given: a draft passing all hard checks with one waivable finding (source conflict) and one blocking finding
- When: confirmation is attempted with the waivable finding undecided; then a decision with reason is recorded; then a decision is attempted on the blocking finding
- Then: undecided waivable finding blocks confirmation naming it; recorded decision (with non-empty reason) is persisted and displayed with the finding; the blocking finding rejects decision recording and requires correction; after decision + correction, confirmation succeeds
- Level: API + Component (decision modal)
- Automation target/path: `apps/backend/tests/test_blueprint.py`; blueprint panel component test
- Data/fixture/environment: seeded findings
- Result/evidence: NOT RUN

### TS-009: Confirmation atomicity, immutability, idempotency, new cycle

- Protects: `AC-008`
- Risk/type: Transaction / Happy
- Given: a complete draft (checks pass, findings resolved/decided) at revision N; an existing confirmed version
- When: confirm executes; duplicate confirm with the same base revision executes; a correction is later saved
- Then: confirm atomically creates immutable blueprint version; duplicate returns the same version; the version is never mutated; later correction starts a new draft cycle without touching the version
- Level: Integration
- Automation target/path: `apps/backend/tests/test_blueprint.py` (PostgreSQL transaction boundary)
- Data/fixture/environment: seeded drafts; real PostgreSQL
- Result/evidence: NOT RUN

### TS-010: Concurrent confirmation and duplicate start singletons

- Protects: `AC-001`, `AC-008`, idempotency invariants
- Risk/type: Concurrency
- Given: one complete draft and two simultaneous confirm requests; an active planning run and a duplicate start
- When: they race
- Then: exactly one immutable version is created (both receive the same version); duplicate planning start returns the existing run; database constraints enforce both
- Level: Concurrency/Integration
- Automation target/path: `apps/backend/tests/test_blueprint.py`, `test_planning.py` (parallel request harness)
- Data/fixture/environment: real PostgreSQL
- Result/evidence: NOT RUN

### TS-011: Brief re-confirmation supersedes runs and stales blueprints

- Protects: `AC-009`
- Risk/type: Supersession / Consistency
- Given: an active planning run, a blueprint draft, and a confirmed blueprint version bound to brief v1
- When: brief version v2 is confirmed
- Then: the active planning run is superseded atomically; the draft and confirmed version become visibly stale; `GET /blueprint` returns the stale state with a field-level brief diff and impact summary; history rows are unchanged; the stale confirmed version cannot serve as the authorized generation input
- Level: Integration
- Automation target/path: `apps/backend/tests/test_blueprint.py`
- Data/fixture/environment: seeded brief/blueprint history
- Result/evidence: NOT RUN

### TS-012: Standards MCP tool first wiring: citations and untrusted metadata

- Protects: `AC-010`
- Risk/type: Integration / Security
- Given: the standards snapshot and the internal MCP-compatible retrieval tool wired into planning; a snapshot fixture carrying hostile tool/server-style metadata
- When: planning grounds objectives through the tool
- Then: citations record the snapshot version; retrieval stays inside the configured snapshot; hostile metadata cannot grant tools, change policy, or surface other workspaces
- Level: Integration (adversarial)
- Automation target/path: planning integration + standards tool suite extension (`tests/test_standards.py`)
- Data/fixture/environment: snapshot fixture subset + adversarial metadata fixture
- Result/evidence: NOT RUN

### TS-013: Cross-account non-disclosure on F002 surfaces

- Protects: `AC-011`
- Risk/type: Security (adversarial)
- Given: teacher A owns a project with planning run, blueprint draft/version, findings, decisions, and trace; teacher B authenticated
- When: B requests those resources by ID
- Then: every response is a safe not-found with no existence or content disclosure
- Level: API (adversarial)
- Automation target/path: isolation suite extension (mandatory cross-owner negatives per TESTING.md)
- Data/fixture/environment: two seeded workspaces
- Result/evidence: NOT RUN

### TS-014: Provider failure preserves planning state

- Protects: `AC-012`, no-duplicate-cost invariant
- Risk/type: Error / Recovery
- Given: FakeModelAdapter injecting timeout/outage mid-planning
- When: the failure occurs and the teacher retries
- Then: named provider/transient error; run and draft state preserved; retry resumes the same run without re-executing completed model work
- Level: Integration
- Automation target/path: `apps/backend/tests/test_planning.py`
- Data/fixture/environment: scripted failures
- Result/evidence: NOT RUN

### TS-015: SSE stop, trace integrity, re-ask, reconnect in planning

- Protects: `AC-013`
- Risk/type: UI/API / Concurrency
- Given: a streamed planning response in flight
- When: the teacher stops display; reconnects after disconnect; presses explicit re-ask
- Then: stop interrupts display only — the model call completes and the full response exists in the owner-scoped trace; reconnect resumes from authoritative state without duplicating model work; re-ask starts exactly one new quota-counted response
- Level: API/Integration (SSE harness)
- Automation target/path: SSE suite extension (`tests/test_streaming.py`)
- Data/fixture/environment: FakeModelAdapter delayed token stream
- Result/evidence: NOT RUN

### TS-016: Injection defense through sources during planning

- Protects: untrusted-input invariant
- Risk/type: Security (adversarial)
- Given: a ready source containing prompt-injection payloads and a snapshot fixture with injected instructions
- When: planning uses them for grounding
- Then: system policy unchanged; no tool grants; no other-workspace disclosure; output stays within the blueprint contract
- Level: Integration (adversarial corpus per TESTING.md)
- Automation target/path: injection suite extension
- Data/fixture/environment: adversarial source fixtures
- Result/evidence: NOT RUN

### TS-017: Planning trace completeness and deletion cascade

- Protects: `AC-015`
- Risk/type: Observability / Privacy
- Given: a completed planning run with questions, answers, citations, and tool usage
- When: its trace is read by the owner; the project is then deleted
- Then: the trace contains prompts, responses, citations, tool usage, latency, and cost within owner scope; deletion removes planning runs, blueprint drafts, versions, findings, decisions, and traces; the audit row records the deletion without content
- Level: Integration
- Automation target/path: trace + deletion suite extensions (`tests/test_trace.py`, `tests/test_deletion.py`)
- Data/fixture/environment: seeded run; compose services
- Result/evidence: NOT RUN

### TS-018: Authorization boundary before/after confirmation

- Protects: `AC-016`
- Risk/type: Rule / Security
- Given: an unconfirmed draft; a stale confirmed version; a current confirmed version
- When: the blueprint state is inspected and any downstream-generation surface is probed
- Then: only a current confirmed blueprint version resolves as the authorized generation input; unconfirmed and stale states are explicit and non-authorizing; no artifact-generation endpoint exists in F002
- Level: API/Integration
- Automation target/path: `apps/backend/tests/test_blueprint.py`
- Data/fixture/environment: seeded states
- Result/evidence: NOT RUN

### TS-019: Explicit re-plan appends a new revision and preserves history

- Protects: alternative-flow invariant
- Risk/type: Happy / History integrity
- Given: a completed planning run with draft revision N and edited content
- When: the teacher explicitly re-plans
- Then: a new run starts after the terminal state; its result appends draft revision N+1; prior draft revisions and confirmed versions are unchanged
- Level: Integration
- Automation target/path: `apps/backend/tests/test_planning.py`
- Data/fixture/environment: seeded completed run
- Result/evidence: NOT RUN

### TS-020: Quota enforcement before planning work

- Protects: quota invariant
- Risk/type: Boundary
- Given: a workspace at planning-quota limit
- When: planning start is requested
- Then: quota/rate-limit error with guidance; no model call issued; quota state from PostgreSQL
- Level: Unit + API
- Automation target/path: `apps/backend/tests/test_planning.py`
- Data/fixture/environment: seeded quota counters
- Result/evidence: NOT RUN

### TS-021: Blueprint panel component states

- Protects: `AC-001`, `AC-004`, `AC-005`, `AC-006`, `AC-007`, `AC-008`, `AC-009`, `AC-014` (UI surfaces)
- Risk/type: UI / Interaction
- Given: mocked API states per the UX/UI state matrix
- When: the teacher views the blueprint surface
- Then: unavailable state names the brief gate; completeness panel lists the four checks with failing items; findings distinguish blocking vs waivable with decision affordances; confirm disabled with reasons; stale banner shows diff and impact summary; small-screen viewport shows read-only with desktop-required messages on structured tasks
- Level: Component/Interaction (Vitest + Testing Library)
- Automation target/path: `apps/web/__tests__/blueprint-panel.test.tsx`
- Data/fixture/environment: API mocks; viewport presets >=1024 / <1024
- Result/evidence: NOT RUN

### TS-022: Accessibility of the blueprint journey

- Protects: `AC-014`, WCAG 2.2 AA obligation
- Risk/type: Accessibility
- Given: the start -> answer -> correct -> decide -> confirm journey
- When: operated by keyboard only
- Then: every action reachable; focus moves to results/errors/decisions per UX rules; phase changes announced politely; statuses and finding tiers not color-only; automated checks plus recorded manual pass
- Level: Accessibility
- Automation target/path: automated a11y checks in component/E2E + manual checklist evidence
- Data/fixture/environment: E2E environment
- Result/evidence: NOT RUN

### TS-023: E2E planning-to-confirmation happy path

- Protects: `AC-001`..`AC-008` (journey)
- Risk/type: Happy / E2E
- Given: a teacher with a confirmed brief (seeded through the F001 flow) and synthetic sources
- When: full journey planning start -> answer scripted questions -> draft review -> correction -> finding decision -> confirm
- Then: confirmed blueprint version visible with citations and recorded decision; authoritative state consistent across reload
- Level: E2E (Playwright)
- Automation target/path: authenticated E2E suite extension
- Data/fixture/environment: compose stack + Clerk dev + FakeModelAdapter
- Result/evidence: NOT RUN

### TS-024: E2E stale and re-plan path

- Protects: `AC-009`
- Risk/type: Supersession / E2E
- Given: a confirmed blueprint on brief v1
- When: the teacher edits the brief and confirms v2
- Then: the blueprint view shows the stale banner with brief diff and impact summary; starting new planning binds v2; the old version remains viewable as history
- Level: E2E
- Automation target/path: authenticated E2E suite extension
- Data/fixture/environment: compose stack + fakes
- Result/evidence: NOT RUN

## Non-functional and Compatibility Coverage

- Idempotency/duplicate: TS-001, TS-006, TS-009, TS-010, TS-014, TS-019
- Concurrency/transaction/consistency: TS-009, TS-010, TS-011 (real PostgreSQL constraints)
- Retry/timeout/recovery: TS-014, TS-015
- Migration/backward compatibility: additive migrations exercised by integration bootstrap; existing F001 endpoints unchanged (regression via full existing suite); backward compatibility `N/A - no external consumers beyond the Web app in the same repository`
- Performance/capacity: latency/cost captured per planning run (TS-017); no per-run cap per Spec D7 — workspace quota is the boundary (TS-020); load testing `N/A - deferred to F009/F011 per ROADMAP`
- Security/privacy: TS-013, TS-016, TS-012, TS-018
- Observability: TS-017

## UI Coverage

- Interaction/navigation: TS-021, TS-023, TS-024
- Loading/Empty/Error/Success: TS-021 (state matrix mocks), TS-023 (success), TS-014/TS-015 (error/recovery)
- Permission/validation: TS-013 (API), TS-021 (disabled reasons), TS-023 (auth entry)
- Responsive: TS-021 viewport presets implementing the 1024px boundary and Spec D8
- Accessibility: TS-022
- E2E/visual regression: E2E TS-023/TS-024; visual-regression baseline extension limited to the blueprint panel region (first stale-view/diff surface); no broad screenshot churn

## Open Test Questions

| ID | Question/blocker | `Critical/Non-critical` | Owner | Resolution/unblock condition | Status |
| --- | --- | --- | --- | --- | --- |
| TQ-001 | Authenticated E2E under Clerk device-verification | Non-critical | `YMY / Project Owner` | F001 residual B-001: persistent profile workaround established; suites extend the existing pattern; full removal pending Clerk config change | RESOLVED |
| TQ-002 | Standards-tool retrieval quality inside planning | Non-critical | Implementation assignee | Tool is deterministic keyword retrieval over a fixed snapshot; adversarial metadata cases in TS-012; quality risk mitigated by findings + teacher correction, revisited with teacher evidence | RESOLVED |
| TQ-003 | Planning-run quota numbers | Non-critical | Implementation assignee | Numbers chosen in the Implementation Plan with cost evidence; Spec behavior (quota gate before run) is testable regardless of the number | RESOLVED |

## `TEST DESIGN READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| TR-01 | Every core `AC-*` is verifiable and maps to at least one `TS-*`. | YES | Acceptance Traceability table covers AC-001..AC-016 |
| TR-02 | Happy Path, major Alternative Flows, and boundaries are covered. | YES | TS-001/005/009/023 happy; TS-003/004/019 alternatives; TS-007/020 boundaries |
| TR-03 | Error, Authentication/Security, and Regression risks are covered. | YES | TS-013/016/012/018 security; TS-007/014 errors; regression via existing suites plus new coverage |
| TR-04 | Idempotency, Concurrency, Transaction, and Consistency are covered or justified N/A. | YES | TS-001/006/009/010/011 |
| TR-05 | High-risk Retry/Timeout, Migration/Compatibility, performance, and similar concerns are covered or justified N/A. | YES | TS-014/015; migration/compat and load N/A reasons recorded above |
| TR-06 | UI interaction/state, Accessibility, and E2E are covered according to risk or justified N/A. | YES | TS-021/022/023/024; visual baseline scoped to the new panel |
| TR-07 | Test levels and automation targets are appropriate and MUST NOT target only implementation details. | YES | All scenarios assert observable API/UI/DB outcomes, not private calls |
| TR-08 | Environment, data, fixtures, and external dependencies are available, or alternative verification is confirmed. | YES | F001 harness (compose + FakeModelAdapter + Clerk token fixtures) reused; fixtures synthetic |
| TR-09 | A Bug has reproduction evidence and a regression scenario, or a confirmed evidence-based surrogate, alternative verification, and residual risk. | YES | `N/A - new Feature, no Bug`; section retained with this reason |
| TR-10 | No Critical Requirement is unverifiable, and no Critical Test Question is `OPEN` or `DEFERRED`. | YES | Open Test Questions all RESOLVED, none Critical |

## `TEST DESIGN READY` Record

- Status: `PASS`
- Input manifest: Spec `108178994342`, UX/UI `a8cfd23189ac`, plus their Gate Record manifests (base `8bf078e`), `docs/TESTING.md` @ `a705fca3189a`, and this artifact `test-design-f002-r1` @ `9c997cfa2b6f`
- Evidence checklist result: ALL YES
- Critical Test Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `108178994342`
- Validated UI revision or complete skip-decision link: `a8cfd23189ac`
- Validated Test Design revision: `test-design-f002-r1` @ `9c997cfa2b6f`
- Validated at: 2026-08-28
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-28
- Approval scope: F002 Test Design at `test-design-f002-r1`

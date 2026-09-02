# Feature Test Design: F013 Teacher Memory

## Metadata

- Spec/Issue: `specs/F013-teacher-memory/spec.md` / [GitHub Issue #26](https://github.com/MaoyuanYang/LessonCanvas/issues/26)
- Validated inputs: Spec @ `75ee61c2cf0b` (`SPEC READY`, 2026-09-02), UX/UI @ `ux-ui-f013-r1` / `8b39aeebb9a9` (`UI READY`, 2026-09-02)
- Test Design revision: `test-design-f013-r1`
- Coverage scope: recommended risk-based scope confirmed by `YMY / Project Owner` on 2026-09-02 (interactive selection "推荐风险范围"): functional happy/alternative/boundary/error-recovery, authorization/privacy, injection defense, idempotency/duplicate/concurrency/transaction/consistency, retry/recovery, migration/backward compatibility, API contract, regression, observability, UI interaction/state/navigation + accessibility + responsive spot + deterministic E2E, one owner-authorized live-model proposal evidence pass. Excluded with reasons: performance/load/stress/soak `N/A - user scope decision (推荐风险范围, 2026-09-02); caps are bounded and no new retrieval infrastructure exists`; fuzz/property-based/mutation `N/A - normalization determinism covered by boundary fixtures (TS-005); no fuzzing infrastructure in repo`; visual regression `N/A - no visual-regression infrastructure; component + E2E cover UI acceptance`; cross-browser `N/A - repo convention chromium E2E`; i18n `N/A - zh-Hans inline copy per repo convention, asserted in unit/component tests`; deployment/rollback `N/A - no topology change in F013; migrations covered by TS-019`; canary/parallel-feature integration `N/A - no concurrent work items (single member; F013 is the only active NEXT)`.
- Environments: (a) deterministic developer stack (compose infra + process app + fake adapter + eager tasks, existing `conftest.py` pattern) for backend integration/unit and web component tests; (b) deterministic browser stack (fake adapter) for E2E; (c) live DeepSeek only for TS-026 under separate owner authorization at execution time.
- `TEST DESIGN READY` Status: `PASS` (see Gate Record)

## Risk Register and Scenario Selection

| Risk / behavior | Impact | Scenario(s) |
| --- | --- | --- |
| Proposals affect runs before confirmation | Authority violation; ADR-0005 broken | TS-007 |
| Rejected proposals nag identically / dedupe broken | Trust and noise; AC-005 broken | TS-005, TS-006 |
| Memory overrides confirmed intent silently | Source-of-truth violation | TS-009 |
| Memory content injection escapes data boundary | Injection/policy breach | TS-015 |
| Caps not enforced (count/length/budget) | Unbounded prompt growth; dishonest truncation | TS-010, TS-011 |
| Pass failures block confirmation/run flows | Availability regression on delivered Features | TS-003 |
| Duplicate passes re-bill model cost | Cost-invariant violation | TS-002, TS-003 |
| Deletion leaves governed memory copies | Privacy violation | TS-013, TS-014 |
| Cross-workspace memory access | Isolation breach | TS-016 |
| Audit rows contain memory text | Privacy boundary leak | TS-017 |
| F009 comparability silently mixes memory states | Evaluation honesty broken | TS-018 |
| Applied context invisible or second-authority drift | Evidence claim false | TS-008, TS-009, TS-022 |
| Per-project override leaks across projects | Scope violation | TS-012 |
| Proposal quality unproven against a real model | Portfolio claim unverified | TS-026 |
| Existing suites regress | Completed features broken | TS-027 |

Happy Path: TS-001/TS-008/TS-023; Alternative/boundary: TS-004/TS-005/TS-010/TS-011; Error/security: TS-003/TS-015/TS-016; Recovery: TS-003/TS-013; Concurrency/idempotency: TS-002/TS-006/TS-011 (unique-constraint race); Migration/compatibility: TS-019; Observability: TS-008/TS-017; UI: TS-020/TS-021/TS-022/TS-023/TS-024/TS-025; Regression: TS-027.

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 | TS-001, TS-002, TS-003, TS-004 |
| AC-002 | TS-008, TS-022, TS-023 |
| AC-003 | TS-009 |
| AC-004 | TS-013, TS-014 |
| AC-005 | TS-005, TS-006, TS-007 |
| AC-006 | TS-015 |
| AC-007 | TS-012 |
| AC-008 | TS-018, TS-019 |
| AC-009 | TS-010, TS-011, TS-020 |
| ADR-0005 invariants | TS-007, TS-009, TS-013, TS-014, TS-015, TS-016 |
| Regression of completed features | TS-027 |

## Scenarios

### TS-001: Proposal pass happy path after brief confirmation

- Protects: AC-001 (bounded, validated, deduplicated pending proposals with evidence)
- Risk/type: Functional / Happy path
- Given: a workspace with a project whose brief is confirmable (deterministic fake adapter scripted to return valid candidates)
- When: the teacher confirms the brief
- Then: exactly one pass runs and completes; at most 3 candidates survive validation (category enum, 300-char cap) and dedupe; each pending proposal carries category, text, and evidence reference to the confirmed brief version; the confirmation response and flow are unchanged
- Level: Integration / API
- Automation target/path: `apps/backend/tests/test_memory.py` (new)
- Result/evidence: NOT RUN

### TS-002: All three trigger points; pass idempotency per trigger identity

- Protects: AC-001; cost invariant (no re-billing)
- Risk/type: Functional / Idempotency
- Given: the deterministic stack and a project reaching blueprint confirmation and generation run settlement
- When: brief confirm, blueprint confirm, and run settlement each fire (and a settle event repeats)
- Then: each unique trigger identity (workspace, kind, version/run id) executes at most one completed pass; duplicate settle events and Celery retries reuse the pass and never schedule a second model call for a completed identity
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py`
- Result/evidence: NOT RUN

### TS-003: Pass failure is best-effort with idempotent retry

- Protects: AC-001 (non-blocking failure; retry)
- Risk/type: Error / Recovery
- Given: the fake adapter configured to fail the proposal pass (fault injection)
- When: a trigger fires and the pass fails, then the teacher retries
- Then: the confirmation/run flow completes normally; the pass state is visibly `failed` with a retry action; retry re-runs and completes; a completed pass is never re-run by retry
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py` (fake adapter fault profile, existing pattern)
- Result/evidence: NOT RUN

### TS-004: Invalid model output dropped; honest empty result

- Protects: AC-001 (untrusted output validation; honest empty)
- Risk/type: Boundary / Invalid input
- Given: the fake adapter returning mixed candidates: unknown category, over-length text, malformed JSON, plus one valid candidate
- When: the pass completes
- Then: only the valid candidate becomes a proposal; invalid ones are dropped without failing the pass; a pass where nothing survives shows the honest "no new proposals" result, never a fabricated proposal
- Level: Integration (adapter contract) + Unit (validation function)
- Automation target/path: `apps/backend/tests/test_memory.py`; fake adapter echo contract extended in `adapters/model.py` tests
- Result/evidence: NOT RUN

### TS-005: Rejection dedupe by normalized content hash

- Protects: AC-005 (no identical re-proposal; new evidence may re-propose differently)
- Risk/type: Alternative flow / Boundary
- Given: a rejected proposal of (category, text); the fake adapter later returns the same candidate with different whitespace/case and a genuinely different candidate backed by a newer confirmed version
- When: later passes run
- Then: the normalized-identical candidate is never re-proposed; the different candidate becomes a new pending proposal
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py`
- Result/evidence: NOT RUN

### TS-006: Pending-slot supersede and stale decision errors

- Protects: AC-005; concurrency correctness
- Risk/type: Concurrency / Duplicate
- Given: a pending proposal in a category and a newer distinct candidate; two concurrent decisions on one proposal
- When: the new candidate arrives; when both decisions submit
- Then: the old proposal is superseded (no rejection penalty, excluded from dedupe); the new one is pending; the second decision receives an explicit stale/proposal-already-decided error and creates no second effect; deciding a superseded proposal is rejected with the stale error
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py`
- Result/evidence: NOT RUN

### TS-007: Unconfirmed/rejected/superseded proposals never apply

- Protects: AC-005; ADR-0005 confirmation rule
- Risk/type: Functional / Invariant
- Given: a workspace with pending, rejected, and superseded proposals and zero confirmed records
- When: discovery, planning, and generation runs execute
- Then: no memory payload key appears in any model call; no `memory.applied` event lists anything; run behavior is byte-identical to a memoryless workspace
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py` (fake adapter payload capture, existing pattern)
- Result/evidence: NOT RUN

### TS-008: Confirmed records inject as labeled, snapshotted context

- Protects: AC-002 (visible subordinate application)
- Risk/type: Functional / Happy path
- Given: confirmed records across all four categories and a new project starting discovery, planning, and generation
- When: each run's model calls are made
- Then: the user payload contains a `memory_context` labeled data key holding only the effective records (capped, deterministically ordered) and no instruction-like framing; a `memory.applied` trace event records record ids, categories, texts, injected character count; the run summary/evidence API exposes the applied-memory section data
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py` (+ evidence read-model assertions)
- Result/evidence: NOT RUN

### TS-009: language_mode conflict — confirmed version wins, surfaced

- Protects: AC-003
- Risk/type: Functional / Invariant
- Given: a confirmed `language_mode` record conflicting with the bound brief's language field
- When: a run starts
- Then: the conflicting record is not injected; the model payload carries the brief's language value as today; the `memory.applied` event records the conflict; the evidence applied-context section and the record row show the conflict notice (确认版本优先)
- Level: Integration + Web component
- Automation target/path: `apps/backend/tests/test_memory.py`; `apps/web/__tests__/memory-region.test.tsx`
- Result/evidence: NOT RUN

### TS-010: Injection budget with deterministic priority and disclosure

- Protects: AC-009; U6/U5
- Risk/type: Boundary
- Given: confirmed records whose total exceeds 2500 characters
- When: the effective set is assembled
- Then: records inject whole in U6 order (language_mode > exercise_format > pacing_structure > assessment_style; most-recently-confirmed first within a category) until the budget; skipped records are listed as budget-skipped in the trace event and rendered as 未注入（超出记忆预算）; no partial record text is injected
- Level: Integration + Web component
- Automation target/path: `apps/backend/tests/test_memory.py`; `apps/web/__tests__/memory-region.test.tsx`
- Result/evidence: NOT RUN

### TS-011: Record and length caps with race safety

- Protects: AC-009
- Risk/type: Boundary / Concurrency
- Given: a workspace at 19 confirmed records (and one at the 300-character boundary)
- When: two confirms race past 20; when an edit exceeds 300 characters
- Then: exactly one confirm succeeds; the loser receives `MEMORY_LIMIT` with the count copy; the over-length edit is rejected server-side (and client-validated with a live counter first) with the length copy; previous content stays intact
- Level: Integration (unique-constraint + count check) + Web component (client validation)
- Automation target/path: `apps/backend/tests/test_memory.py`; `apps/web/__tests__/account-memory.test.tsx`
- Result/evidence: NOT RUN

### TS-012: Per-project override scope and audit

- Protects: AC-007
- Risk/type: Functional / Authorization scope
- Given: two projects in one workspace and a confirmed record
- When: the record is disabled for project A and runs start in A and B
- Then: A's runs exclude the record (listed as project-disabled); B's runs include it; the toggle writes an audit event; re-enabling restores application
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py`
- Result/evidence: NOT RUN

### TS-013: Record deletion stops future application, keeps history honest

- Protects: AC-004
- Risk/type: Recovery / Data lifecycle
- Given: a confirmed record applied by a completed run, with per-project overrides and a pending proposal referencing it
- When: the record is deleted
- Then: the record, its overrides, and the referencing proposal are gone; the next run applies no memory from it; the completed run's historical trace (including the already-injected payload and applied-context reference) remains inspectable and is removed with project deletion
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py`
- Result/evidence: NOT RUN

### TS-014: Deletion completeness for memory tables

- Protects: AC-004; F011 sweep extension
- Risk/type: Data integrity / Privacy
- Given: a workspace with records, proposals (all states), overrides, and applied-context traces
- When: the project and then the workspace are deleted
- Then: the F011 completeness verification reports zero rows across all memory tables for both cascades; the content-free retained security ledger behavior is unchanged
- Level: Integration (existing deletion suites extended)
- Automation target/path: `apps/backend/tests/test_deletion.py`, `apps/backend/tests/test_guardrails_deletion.py`; `tests/conftest.py` truncate list extended
- Result/evidence: NOT RUN

### TS-015: Adversarial memory content stays inert at re-injection

- Protects: AC-006; AGENTS untrusted-input rule
- Risk/type: Security / Injection
- Given: confirmed records whose text carries injection payloads (instruction override, tool requests, cross-workspace probes — mirroring the adversarial corpus classes)
- When: discovery/planning/generation runs execute with those records applied
- Then: payloads appear only inside the serialized `memory_context` data value and trace records; system prompts, tool availability, authorization, output schemas, and run outcomes are unchanged; no marker escapes into tool calls or policy decisions
- Level: Integration / Adversarial
- Automation target/path: `apps/backend/tests/test_guardrails_injection.py` (memory corpus extension; fake adapter verbatim echo, existing pattern)
- Result/evidence: NOT RUN

### TS-016: Owner-only authorization on every memory surface

- Protects: AC-004/AC-007 boundary; isolation
- Risk/type: Authorization
- Given: two workspaces each with records and proposals
- When: workspace B's subject calls every memory endpoint (list, confirm, reject, retry, edit, delete, project view, override) targeting workspace A resources
- Then: every call is rejected with the existing authorization error class; no existence disclosure; audit records the denial per existing behavior
- Level: API / Contract
- Automation target/path: `apps/backend/tests/test_memory.py`
- Result/evidence: NOT RUN

### TS-017: Memory actions audited without memory text

- Protects: Privacy boundary; observability
- Risk/type: Observability / Privacy
- Given: memory actions executed (pass, confirm, reject, edit, delete, override)
- When: the audit list is read
- Then: each action appears with actor/target/action and (for passes) estimated cost; no row contains record or proposal text
- Level: Integration
- Automation target/path: `apps/backend/tests/test_memory.py` (audit assertions)
- Result/evidence: NOT RUN

### TS-018: F009 memory pinning snapshot and comparability

- Protects: AC-008
- Risk/type: Regression / Contract
- Given: the evaluation harness (workspaces empty of memory by construction) and legacy evaluations holding the placeholder snapshot
- When: a new evaluation is created and passes are grouped
- Then: `memory_state_json` binds the structured revision-list snapshot (empty list for harness workspaces); `C-MEM-1` passes only with a recorded snapshot; the pass-comparability signature includes the memory set; legacy rows render as the recorded empty state without error
- Level: Integration
- Automation target/path: `apps/backend/tests/test_technical_evaluation.py` (extended); `apps/web/__tests__/technical-evaluation.test.tsx` (rendering)
- Result/evidence: NOT RUN

### TS-019: Migration and backward compatibility

- Protects: AC-008; schema rollout
- Risk/type: Migration / Compatibility
- Given: the alembic chain with the new memory tables and the F009 snapshot column unchanged in shape
- When: the test database is created via `alembic upgrade head` (existing conftest) and pre-existing F009 rows with placeholder snapshots are read
- Then: migrations apply cleanly; all existing suites pass on the migrated schema; legacy snapshot values are handled per TS-018; no destructive change to existing tables
- Level: Integration (schema-level)
- Automation target/path: full backend suite via `uv run pytest` (conftest upgrades head)
- Result/evidence: NOT RUN

### TS-020: Account 教师记忆 section component behavior

- Protects: AC-009; U1
- Risk/type: UI / States
- Given: the account page with the memory section
- When: rendered in loading, empty, loaded, quota-exceeded, edit (with live 300-char counter), delete-confirm, and pass-failed states
- Then: each state renders per the UX state matrix (skeletons, EmptyState, quota copy with management link, Modal/ConfirmModal with consequence text, retry action); pending proposals list with confirm/reject works and links to the originating project
- Level: Web component (jsdom)
- Automation target/path: `apps/web/__tests__/account-memory.test.tsx`
- Result/evidence: NOT RUN

### TS-021: Proposal region and badge component behavior

- Protects: AC-001; U2
- Risk/type: UI / States + Navigation
- Given: brief/blueprint/artifact panels hosting the proposal region
- When: pass generating, failed, empty, pending, and concurrently-decided states occur
- Then: the region shows the corresponding honest state; the badge count matches pending proposals and links to the first holding panel; inline edit before confirm enforces the length counter; the stale-decision refresh shows 该提议已被处理
- Level: Web component
- Automation target/path: `apps/web/__tests__/memory-proposals.test.tsx`
- Result/evidence: NOT RUN

### TS-022: Evidence applied-context region

- Protects: AC-002/AC-003/AC-007; U3/U5
- Risk/type: UI / States
- Given: the evidence panel with the 教师记忆（本项目） region
- When: a run with applied records, a run with conflicts/budget skips, and a run with nothing applied are selected
- Then: the region lists applied records with categories/chars, conflict notices with 确认版本优先, budget-skip disclosure, or the honest 未应用 explanation with reasons; per-record project toggles issue overrides and reflect immediately; the account link navigates
- Level: Web component + integration of the read model
- Automation target/path: `apps/web/__tests__/memory-region.test.tsx`
- Result/evidence: NOT RUN

### TS-023: Deterministic E2E memory journey

- Protects: AC-001, AC-002, AC-004 end to end
- Risk/type: E2E / Happy path + deletion
- Given: the deterministic browser stack (fake adapter scripted for candidates)
- When: the teacher confirms a brief, addresses the proposal card (badge → edit → confirm), completes planning/generation, opens evidence, deletes the record, and runs again
- Then: the full journey renders honestly at each step (proposal states, applied context, quota counters, post-deletion no-application), and no step requires live-model access
- Level: E2E (Playwright chromium)
- Automation target/path: `apps/web/e2e/memory-journey.spec.ts`
- Result/evidence: NOT RUN

### TS-024: Scripted accessibility pass for memory flows

- Protects: UX accessibility obligations; U2/U3
- Risk/type: Accessibility
- Given: the memory surfaces in the browser
- When: operated keyboard-only (badge → proposal card → confirm → evidence region toggles → account section → edit dialog)
- Then: every action is reachable, the badge and regions expose labels/aria structures, dialogs trap and restore focus, conflict/truncation notices are announced, and no meaning depends on color alone (chips carry text)
- Level: E2E scripted a11y assertions (+ manual spot per repo convention)
- Automation target/path: `apps/web/e2e/memory-journey.spec.ts` (keyboard/label assertions)
- Result/evidence: NOT RUN

### TS-025: Responsive spot for the canonical reduced experience

- Protects: UX responsive boundary
- Risk/type: Responsive
- Given: the memory surfaces at 420px width
- When: browsing proposals, applied context, and the account section
- Then: the canonical reduced experience holds (proposal decisions and read-only applied context usable; record editing shows the documented desktop-required message); no horizontal overflow or simulated full desktop
- Level: E2E viewport spot
- Automation target/path: `apps/web/e2e/memory-journey.spec.ts` (420px viewport case)
- Result/evidence: NOT RUN

### TS-026: Live-model proposal quality evidence (single authorized pass)

- Protects: Portfolio claim that real proposals are sensible; AC-001 quality dimension
- Risk/type: Live-model evidence (separated from deterministic CI per TESTING.md)
- Given: the live stack with real DeepSeek and a completed representative unit (governed synthetic corpus)
- When: the owner authorizes and triggers one proposal pass per trigger kind
- Then: proposals are category-valid, evidence-referenced, teacher-plausible; the pass cost is recorded; the result is appended as execution evidence (never a CI dependency)
- Level: Operational evidence run
- Automation target/path: scripted journey under owner authorization; evidence appended below
- Result/evidence: NOT RUN (requires owner authorization at execution time)

### TS-027: Full regression sweep

- Protects: all completed Features
- Risk/type: Regression
- Given: the implemented branch
- When: the project-required verification runs
- Then: backend `uv run pytest` fully green (including extended F009/F011 suites) + `ruff check` clean; web vitest suite green + `tsc` clean + `lint` 0 errors
- Level: Regression
- Automation target/path: repo-standard commands (AGENTS Build and Test)
- Result/evidence: NOT RUN

## Parallel-feature integration / merge regression

`N/A - no concurrent work items` (single member; F013 is the only active `NEXT`; recorded per TR-11).

## Gate Record: TEST DESIGN READY

- Status: `PASS`
- Validation time: 2026-09-02
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-02 (coverage-scope question-form "推荐风险范围" selecting the risk-based family set with recorded exclusions; combined question-form "批准两项,READY" approving TEST DESIGN READY and Plan `plan-f013-r1` @ `427356ca088e` together), scope: `test-design-f013-r1`
- Checklist: 11/11 YES (AC→TS trace complete AC-001..AC-009 + ADR-0005 invariants; happy/alternative/boundary covered TS-001/004/005/010/011; error/auth/security TS-003/015/016; idempotency/concurrency/transaction/consistency TS-002/006/011/013; retry/migration/compatibility TS-003/019 with N/A reasons recorded for performance families per user scope decision; UI/a11y/E2E TS-020..TS-025; levels target external behavior via API payloads, trace events, and rendered states; environment/fixtures deterministic with the fake-adapter/eager-task pattern and one separately-authorized live pass TS-026; no Bug in this work item — N/A new Feature; no Critical Requirement unverifiable; TR-11 N/A recorded)
- Input manifest: `specs/F013-teacher-memory/spec.md` @ `75ee61c2cf0b`; `specs/F013-teacher-memory/ux-ui.md` @ `8b39aeebb9a9`; `AGENTS.md` @ `ecde9412a7df`; `docs/TESTING.md` @ `64f6af3824c2`; `docs/UX.md` @ `bce8aecf872f`; backend/web test inventory OBSERVED 2026-09-02 (`main @ 505232e`)

## Execution Evidence Snapshot (2026-09-02, deterministic stack)

Stack: isolated PostgreSQL :5433 / MinIO :9002 / Redis :6380 containers, `LESSONCANVAS_MODEL_ADAPTER=fake`, `LESSONCANVAS_TASKS_EAGER=true`, memory checkpointer. Suites: backend 504 passed + 4 skipped (progress-dot count, exit 0) + `ruff check src tests migrations` clean; web 108/108 vitest + `tsc` clean + `eslint .` 0 errors (3 warnings pre-existing on `main`); E2E `memory-journey.spec.ts` 3/3 behind `E2E_MEM_FAULT=1` against the dev web (:3001) + fake API (:8010).

| TS | Result | Evidence location |
| --- | --- | --- |
| TS-001..TS-006, TS-007..TS-013, TS-016..TS-019 | PASS | `apps/backend/tests/test_memory.py` (green in the full-suite run) |
| TS-015 | PASS | `apps/backend/tests/test_guardrails_injection.py::test_adversarial_memory_content_stays_inert_in_payloads` + `test_memory.py::test_adversarial_memory_stays_inert_serialized_data` |
| TS-014 | PASS | `test_memory.py::test_project_and_workspace_deletion_remove_memory_completely` (extends the F011 sweep registration; conftest truncation list covers the four tables) |
| TS-018/TS-019 | PASS | updated `tests/test_technical_evaluation.py::test_engine_memory_pinning_evaluates_recording_itself` (structured snapshot passes C-MEM-1; legacy placeholder fails) + `test_full_pipeline_binds_versions_runs_artifacts_config_memory` |
| TS-020..TS-022 | PASS | `apps/web/__tests__/account-memory.test.tsx` (11 tests) |
| TS-023..TS-025 | PASS | `apps/web/e2e/memory-journey.spec.ts` (full loop / keyboard-only / 420px spot) |
| TS-026 | PASS (live, owner-authorized 2026-09-03) | `specs/F013-teacher-memory/live-evidence.json`: brief_confirm completed with 3 teacher-plausible category-valid evidence-referenced proposals (language_mode value=english derived from the 全英文 brief, exercise_format 图表类, assessment_style 形成性+小组展示; total pass cost $0.0003); run 1 additionally completed blueprint_confirm with a pacing_structure proposal; run 2's blueprint_confirm hit a real transient provider failure (pass settled failed, journey unaffected — the best-effort contract demonstrated live) and run_settled completed with an honest 0-proposal dedupe result; both journeys purged by account deletion (200 purged) |
| TS-027 | PASS | Full backend + web sweeps above |

Deviations recorded in `review.md`: IF-5 (E2E mid-journey demonstrates application on a discovery run; planning/generation payload application proven by backend TS-008) and M-1/IF-4 (dev-server click race worked around via API-resolved navigation).

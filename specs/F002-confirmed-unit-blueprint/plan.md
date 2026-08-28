# Implementation Plan: F002 Confirmed Unit Blueprint

## Ready Inputs

- Spec: `specs/F002-confirmed-unit-blueprint/spec.md` / `SPEC READY Status: PASS` / revision `108178994342`
- UX/UI: `specs/F002-confirmed-unit-blueprint/ux-ui.md` / `UI READY Status: PASS` / revision `a8cfd23189ac`
- Test Design: `specs/F002-confirmed-unit-blueprint/test-design.md` / `TEST DESIGN READY Status: PASS` / revision `9c997cfa2b6f`
- Complete controlling-input manifest: see Spec Gate Record and UI READY Record (base `8bf078e`; AGENTS `b03a2200602b`; ROADMAP `648cb6b43680`; API `1a10877df315`; DATABASE `9623b9c222b4`; ARCHITECTURE `a3118a75d52b`; PRODUCT `2ec972e941fc`; TESTING `a705fca3189a`; ADRs 0001–0005 at hashes listed in the Spec Gate Record)
- Plan revision/change-log ID: `plan-f002-r1`
- Plan Status: `CURRENT`
- Issue/work item: [GitHub Issue #3](https://github.com/MaoyuanYang/LessonCanvas/issues/3)
- Applicable AGENTS/architecture docs: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATABASE.md`, `docs/TESTING.md`, `docs/FRONTEND.md`, `docs/DESIGN_SYSTEM.md`

## Requirement Guardrail

- Scope/Acceptance changes proposed by this Plan: `NONE`
- If not NONE: `STOP`; update Spec/Test Design through Design Change before continuing.

## Current and Target Flow

### Current

F001 delivers: Clerk-authenticated workspaces, projects, sources, discovery interview (SSE), confirmed brief versions, owner-scoped traces, deletion cascade. No blueprint surface exists; the standards MCP tool is defined and tested but unwired; workspace UI has three tabs (sources/discovery/brief).

### Target

```text
apps/backend  modules/discovery_planning gains:
                planning run lifecycle (LangGraph graph mirroring discovery pattern),
                blueprint draft/version services (append-only revisions, atomic confirm),
                findings model (blocking derived deterministically; waivable from agent,
                decisions recorded through new draft revisions)
              api/planning.py, api/blueprint.py (owner-scoped, taxonomy errors)
              brief confirm transaction extended: supersede active planning run,
                stale blueprint versions (same transaction)
              standards MCP tool wired into planning grounding (first workflow use)
apps/web       workspace gains fourth tab 单元蓝图:
                start/progress + shared conversation component (extracted from discovery),
                draft review/edit + completeness panel, findings region + decision modal,
                confirm modal, stale view (banner + brief diff + impact summary),
                small-screen desktop-required gate (D8)
```

Request flow: confirmed brief -> planning start (quota gate, idempotent, bound to brief version) -> SSE interview -> draft revision 1 (citations + findings) -> structured corrections -> finding decisions -> four hard checks (server-authoritative) -> confirm -> immutable blueprint version. Brief re-confirmation supersedes the active run and stales dependent drafts/versions atomically.

## Affected Surface

| Module/page/file | `Add/Modify/Delete` | Responsibility/change | Constraint/reuse |
| --- | --- | --- | --- |
| `apps/backend/migrations/versions/*_planning_blueprint.py` | Add | `planning_runs`, `blueprint_drafts`, `blueprint_versions` | UUIDv7; UTC; unique constraints (one active run per project; unique version per source revision; monotonic draft revision per project) |
| `src/lessoncanvas/models.py` | Modify | Add the three models | DATABASE.md conventions |
| `src/lessoncanvas/modules/discovery_planning/planning.py` | Add | Planning graph: analyze (corpus + standards tool) -> ask loop (6x3 cap) -> build draft + findings | Reuse discovery graph pattern; LangGraph owns semantic state |
| `src/lessoncanvas/modules/discovery_planning/blueprint.py` | Add | Draft revision service (append-only, base-revision guard), findings state machine (decisions append revisions), completeness checks (server-authoritative), atomic confirm, stale derivation + diff/impact summary builder | Mirror `brief.py` invariants |
| `src/lessoncanvas/modules/discovery_planning/brief.py` | Modify | Confirm transaction extended: supersede active planning run; stale blueprint versions | Same transaction as version creation |
| `src/lessoncanvas/modules/sources_grounding/standards.py` | Modify (wiring only) | Expose retrieval to planning grounding; no behavior change to the tool | Untrusted-input rules (ADR-0004) |
| `src/lessoncanvas/api/planning.py`, `api/blueprint.py` | Add | Endpoints per Spec API Behavior | Taxonomy errors; owner deps |
| `src/lessoncanvas/adapters/model.py` | Modify | FakeModelAdapter planning scenarios (gaps, zero-gap, unresolvable, provider failure, delayed stream) | No DeepSeek adapter change |
| `apps/web/lib/api.ts` + zod schemas | Modify | Planning/blueprint client functions | Mirror existing patterns |
| `apps/web/components/conversation-panel.tsx` | Add (extract) | Shared streaming conversation region extracted from `discovery-panel.tsx` (D-CONVO) | Discovery panel regression green |
| `apps/web/components/blueprint-panel.tsx` | Add | Start/progress, draft review/edit, completeness, findings, confirm, stale view | Reuse ui.tsx primitives; zh-Hans copy |
| `apps/web/workspace-view.tsx` | Modify | Fourth tab with unavailable reason | D-NAV |
| Backend/web test suites | Add/Modify | New suites + extensions per Test Design | TS traceability |

## Implementation Approach

### Domain / Application

- Planning graph mirrors the proven discovery graph: `analyze_node` (brief fields + source corpus + standards tool grounding; material-gap detection), `ask_node` (persist `InteractionMessage`, `interrupt()`; 6x3 caps), `build_draft_node` (structured blueprint + waivable findings from agent; blocking findings derived deterministically by the service, never trusted from the model).
- Findings live inside the draft payload (each draft revision carries the full findings state); recording a waivable decision appends a new draft revision with the decision and reason applied — append-only lineage keeps decisions auditable without a second truth.
- Stale is derived for drafts (`bound brief version != current confirmed brief version`) and persisted for versions (`stale`, `stale_brief_version_id`) inside the brief-confirm transaction.

### Data / Migration

- One additive migration: `planning_runs` (id, project_id, workspace_id, brief_version_id, status, round_count, model_calls, timestamps; partial unique index for one active run), `blueprint_drafts` (id, project_id, workspace_id, brief_version_id, revision unique per project, payload_json, timestamps), `blueprint_versions` (id, project_id, workspace_id, brief_version_id, source_revision, version unique per project, unique (project, source_revision), payload_json including resolved findings and decisions, stale, stale_brief_version_id, timestamps).
- Deletion cascade list extended to the three tables; audit rows for blueprint confirmation and recorded finding decisions (non-content).

### API / Integration

- Endpoints per Spec; pydantic schemas frozen first; SSE planning stream reuses the narration registry and offset-reconnect mechanics from F001.
- Quota: planning start consumes the existing workspace model-call quota (counter key reused); no per-run cap (Spec D7). Initial quota policy unchanged from F001 numbers; revisit with cost evidence (TQ-003).

### Transaction / Idempotency / Concurrency / Consistency

- Planning start: idempotent via active-run partial unique index + provider of existing run; brief binding recorded at creation.
- Confirm: single transaction with unique (project, source_revision); races resolve through constraint catch returning the existing version (brief pattern).
- Brief re-confirmation: version creation, planning-run supersession, and blueprint staling in one transaction; stale state can never authorize (blueprint resolution queries filter `stale = false`).

### Frontend State / Components / UI States

- TanStack Query keys per planning/blueprint resource; SSE consumption reuses the existing fetch+ReadableStream pattern behind the extracted conversation component.
- Completeness panel renders server-computed checks (client shows guidance only); decision and confirm modals per UX/UI; stale view consumes the diff/impact summary payload.

### Security / Validation / Error Handling

- Ownership via existing workspace deps; planning/blueprint error mapping per ux-ui.md table; injection posture unchanged (sources/snapshot/model output are data; fixed tool allowlist).
- Blocking-check computation and waivable-decision persistence are server-authoritative.

### Observability

- Planning trace events: prompts, responses, citations, `tool.standards_search` usage, latency, cost — owner-scoped, deleted with project.

## Test Execution Plan

| Scenario IDs | Test target/path | When to run | Required result |
| --- | --- | --- | --- |
| TS-006, TS-009 | `apps/backend/tests/test_blueprint.py` (revision/confirm base) | T0, then full suite | PASS |
| TS-001, TS-002, TS-003, TS-004, TS-020 | `apps/backend/tests/test_planning.py` (graph rules, lifecycle, quota) | T1 | PASS |
| TS-012, TS-016 | planning integration + `tests/test_standards.py` extension (adversarial metadata, injection corpus) | T1 | PASS |
| TS-014, TS-015, TS-013, TS-010 | planning API/SSE suite, isolation extension, concurrency harness | T2 | PASS |
| TS-007, TS-008, TS-011, TS-018 | `apps/backend/tests/test_blueprint.py` (checks, decisions, supersession/stale, authorization boundary) | T3 | PASS |
| TS-017 | trace + deletion suite extensions | T4 | PASS |
| TS-021 (foundation), regression | web suites incl. discovery-panel regression after conversation extraction | T5 | PASS |
| TS-021, TS-022 (automated) | `apps/web/__tests__/blueprint-panel.test.tsx`, a11y checks | T6 | PASS |
| TS-023, TS-024, TS-022 (manual) | Playwright authenticated extension + keyboard pass | T7 | PASS or gated evidence per B-001 |
| All | full deterministic suite + ruff + web lint/typecheck/build | every Task exit; final before Review | PASS |

Live DeepSeek planning smoke: one capped manual run recorded as separate evidence during T1 (excluded from deterministic CI per TQ-001 precedent).

## Rollout, Compatibility, and Rollback

- Migration/backfill: `N/A - additive only, no existing-data rewrite`
- Feature flag/staged rollout: `N/A - Phase-1 single deployment`
- Breaking change: `NO` (existing F001 endpoints and payloads unchanged)
- Rollback: revert the delivery branch; additive migration is downward-compatible (drop new tables)

## Risks and Decisions

| Risk/decision | Level | Mitigation/choice | Needs confirmation/ADR? |
| --- | --- | --- | --- |
| Findings embedded in draft payload vs separate table | Low | Embedded + revision-appending decisions; single truth, auditable lineage; revisit if F006/F007 need cross-version finding queries | No (implementation choice within Spec) |
| Planning graph duplication of discovery graph | Medium | Mirror the established pattern (nodes, interrupt, checkpointer) with shared conventions; extract shared helpers only where a real seam exists | No |
| Standards tool retrieval quality | Medium | Deterministic keyword retrieval over fixed snapshot; findings + teacher correction mitigate; teacher evidence revisit (TQ-002) | No |
| No per-run model cap (Spec D7) cost exposure | Medium | Workspace quota is the boundary; per-run telemetry visible in trace; revisit trigger recorded in Spec | No (Decision Authority already accepted) |
| Conversation-component extraction regression | Low | Discovery-panel tests must stay green before/after extraction (T5 exit) | No |
| Authenticated E2E Clerk constraint | Low | Extend the gated CLERK_E2E pattern (B-001); record evidence | No |

## Interleaved Tasks

- [x] T0 Contracts + persistence base: DTOs frozen in `blueprint.py` normalization + web types; migration `6d1c9a20b7f4` (`blueprint_drafts`, `blueprint_versions`, `discovery_runs.kind` + `brief_version_id` + active-planning partial unique index); draft-revision service and atomic-confirm primitives. — DONE 2026-08-28 (implementation refinement: planning runs reuse `discovery_runs` with `kind` discriminator; findings embedded in draft payload with decisions as new revisions).
- [x] T1 Planning workflow: `planning.py` graph (analyze with corpus + standards tool, ask loop 6x3, build draft with server-side normalization/enrichment), idempotent start bound to brief version, workspace quota gate; FakeModelAdapter planning scenarios. — DONE 2026-08-28. Live smoke not run (session constraint; deterministic fake scenarios cover behavior; live run optional before delivery).
- [x] T2 Planning API + SSE: `api/planning.py` (start/status/answers/retry/narrate/reask/stop-narration/stream); isolation covered; planning narration reuses shared machinery (per-run cap skipped for planning per Spec D7). — DONE 2026-08-28.
- [x] T3 Blueprint API + supersession: `api/blueprint.py` (GET with checks/stale/diff/impact, PATCH draft, POST decisions, POST confirm); brief-confirm transaction extension supersedes runs and stales versions atomically. — DONE 2026-08-28.
- [x] T4 Trace + deletion extension: `tool.standards_search`/`model.planning_*` trace events; cascade covers blueprint tables; audit rows for confirm/decision. — DONE 2026-08-28.
- [x] T5 Web foundation: API client + types for planning/blueprint; `conversation-region.tsx` extracted (D-CONVO) with discovery-panel regression green. — DONE 2026-08-28.
- [x] T6 Blueprint UI: 单元蓝图 tab + panel (start/progress/questions, draft review/edit, completeness panel, findings + decision modal, confirm modal, stale view with diff, small-screen gate). — DONE 2026-08-28: 5 new component tests; 16 web tests green.
- [x] T7 E2E + accessibility: authenticated spec extended with planning->decision->confirm->stale journey (gated by CLERK_E2E per B-001); public E2E 3/3. Keyboard manual pass pending gated session (review M-2). — DONE 2026-08-28.
- [x] T8 Review + docs sync + delivery prep: `review.md` recorded (no Critical/High; M-1/M-2 follow-ups); DESIGN_SYSTEM conversation note; ROADMAP/STAGE/Issue synced. — DONE 2026-08-28: READY FOR PR.

## Start Checklist

- [x] All required Gates are PASS, or UI has a complete `SKIPPED (N/A)` decision record. — SPEC/UI/TEST DESIGN all PASS (records in artifacts)
- [x] Gate input manifests match current working-tree artifact revisions, not only the base commit. — hashes listed in Ready Inputs and Gate Records
- [x] Plan MUST NOT redefine Scope, rules, contract, or Acceptance. — Requirement Guardrail `NONE`
- [x] Major dependency/architecture/migration decisions are confirmed. — Spec D1–D8, UI D-NAV/D-CONVO/D-FIND approved by `YMY / Project Owner`; additive migration only
- [x] Tasks interleave code, tests, and docs. — each Task lists TS coverage; T8 carries docs sync
- [x] Each Task has a verification point. — Exit criteria per Task

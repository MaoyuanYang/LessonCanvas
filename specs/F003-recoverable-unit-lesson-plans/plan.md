# Implementation Plan: F003 Recoverable Unit Lesson Plans

## Ready Inputs

- Spec: `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `193e90d10b68` (`SPEC READY` PASS, 2026-08-29)
- UX/UI: `specs/F003-recoverable-unit-lesson-plans/ux-ui.md` @ `ux-ui-f003-r1` / approved content `43f93abc6ed3` (`UI READY` PASS, 2026-08-29)
- Test Design: `specs/F003-recoverable-unit-lesson-plans/test-design.md` @ `test-design-f003-r2` / `880a6a4a418c` (`TEST DESIGN READY` PASS, 2026-08-29)
- Governing docs: `AGENTS.md` @ `b03a2200602b`, `docs/ARCHITECTURE.md` @ `a3118a75d52b`, `docs/API.md` @ `1a10877df315`, `docs/DATABASE.md` @ `9623b9c222b4`, ADR-0002 @ `5145b0ff319f`, ADR-0003 @ `d0e2fcd0c587` (full manifest in Spec Gate Record; VCS base `4ccc4ef`)
- Work item: [Issue #6](https://github.com/MaoyuanYang/LessonCanvas/issues/6)

## Requirement Guardrail

`NONE` — this plan changes no Scope, business rule, API contract semantics, or Acceptance Criterion. Any need to do so returns to Spec via Design Change.

## Current and Target Flow

### Current

- `worker.py` contains only the Celery app and a health-check task; no generation dispatch exists.
- Modules: `identity_workspace`, `sources_grounding`, `discovery_planning`; no run-orchestration or artifact-production packages.
- Workspace UI has four context views (来源 / 需求访谈 / 教学简报 / 单元蓝图); blueprint confirmation exists with supersession hooks on brief re-confirmation (F002).
- SSE machinery exists for interview/planning narration (per-run stream endpoints), without an authoritative replayable event log.

### Target

```text
单元蓝图 confirmed (brief vN + blueprint vM)
  -> POST /generation/start: atomic idempotent run row (unique per project+versions)
  -> Celery dispatch -> Worker runs LangGraph generation graph:
       context assembler -> per lesson: writer (model) -> render (python-docx tool) -> validate (tool)
       per-lesson checkpoint rows + run event log appends in PostgreSQL
  -> GET /generation snapshot | GET /generation/events SSE (Last-Event-ID replay)
  -> outcomes: complete | partial_failure | capped_failure | superseded | terminal_failure
  -> resume re-dispatches same run (eligible states only); download streams authorized DOCX
```

## Affected Surface

| Area | Path / artifact | Change |
| --- | --- | --- |
| Persistence | `apps/backend/migrations/` (new) | `generation_runs`, `lesson_plan_artifacts`, `run_events` tables; UUIDv7 ids; unique idempotency constraint `(project_id, brief_version_id, blueprint_version_id)`; per-run monotonic event sequence |
| Models | `src/lessoncanvas/models.py` | Three new ORM models + deletion-cascade relationships |
| Run orchestration | `src/lessoncanvas/modules/run_orchestration/` (new) | Run service (atomic start/resume/state transitions/supersession), event-log append + replay query, cap accounting |
| Artifact production | `src/lessoncanvas/modules/artifact_production/` (new) | LangGraph generation graph (3 specialists, D6), `python-docx` render tool + structural validator tool with MCP-compatible definitions (ADR-0004 pattern) |
| Worker | `src/lessoncanvas/worker.py` | Generation task, bounded retry policy, eager-mode testability |
| API | `src/lessoncanvas/api/generation.py` (new) | start / snapshot / events SSE / resume / download; registered in `main.py` |
| Supersession | `modules/discovery_planning/blueprint.py` | `on_brief_version_confirmed` extension marks active generation runs superseded at safe checkpoint (existing transaction) |
| Trace/deletion | existing services | generation trace events; deletion cascade to new tables + binaries |
| Web | `apps/web/lib/api.ts`, types, `components/generation-panel.tsx` (new), workspace shell | Fifth context view, SSE hook with `Last-Event-ID`, states per ux-ui.md |
| E2E | `apps/web/e2e/` | Extended authenticated spec + deterministic fault-instance profile |

## Implementation Approach

### Domain / Application

- Run state machine exactly per Spec (queued/generating/validating/complete/partial_failure/capped_failure/superseded/terminal_failure/teacher_blocked; per-lesson pending/drafting/rendering/validating/complete/failed).
- Generation graph: `assemble_context` node once per run; per-lesson subflow `write -> render -> validate` with checkpoint persistence between steps; failures classified per D5 with bounded retry budget for retryable causes.
- FakeModelAdapter gains deterministic generation scenarios (per-lesson success/failure scripting, injection payloads) mirroring the F001/F002 fake pattern.

### Data / Migration

- One additive migration: three tables, FKs to project/brief/blueprint versions, indexes on `(run_id, seq)` for replay and `(run_id, lesson_index)` for artifacts; no legacy rewrite.
- Object storage: DOCX under workspace/project-scoped keys; artifact row stores key + checksum; binary existence verified before ready.

### API / Integration

- Five endpoints per Spec API Behavior; SSE envelope and DTOs frozen schema-first in T0 (Zod on web, Pydantic on API) within Spec semantics.
- SSE: per-run monotonic `id`, event types phase/lesson/narration; `Last-Event-ID` maps to replay query; replay and snapshot are read-only.
- Download: streamed from storage through the app boundary with ownership check; denial is non-disclosing.

### Transaction / Idempotency / Concurrency / Consistency

- Start: single transaction — ownership check, confirmed-version binding, unique-constraint insert (duplicate → select existing), dispatch handoff.
- Per-lesson idempotency: lesson outcome rows keyed by `(run_id, lesson_index)`; completed lessons skipped by state, never re-executed.
- Supersession: the existing brief-confirm transaction marks active generation runs `superseded`; an in-flight lesson completes its current step, then the run stops at the checkpoint without publishing further artifacts under the old version binding.
- Cap: increment-before-call accounting on the run row with a conditional UPDATE guard (`UPDATE ... SET model_calls = model_calls + 1 WHERE id = ? AND model_calls < cap`) so concurrent steps cannot exceed the cap.

### Frontend State / Components / UI States

- Typed API client + Zod schemas; SSE hook managing connection, `Last-Event-ID` cursor, reconnect banner state, and stop-narration control; snapshot refetch as fallback/tie-breaker.
- `generation-panel.tsx` implements D-GEN/D-PROG/D-NARR/D-ART/D-RECN surfaces and the state matrix from ux-ui.md; desktop-required gate below 1024px for start/resume; monitoring + downloads preserved.

### Security / Validation / Error Handling

- Every endpoint authorizes by recorded workspace ownership; cross-workspace = non-disclosing denial class.
- Generated content treated as untrusted output at every boundary (render as inert text; no tool grant from content).
- Error mapping per ux-ui.md table; no storage paths, prompts, or provider details leak.

### Observability

- Trace events for every model call, tool call (render/validate), specialist transition, failure, and retry with cost/latency (ADR-0003).
- Run event log doubles as the SSE source and F006 evidence base; retained for the run's life, workspace-scoped.

## Test Execution Plan

| Suite | Command | Scenarios |
| --- | --- | --- |
| Backend unit/integration/API | `cd apps/backend && uv run pytest` | TS-001..TS-019 (new `tests/test_generation.py`; existing suites stay green) |
| Backend lint | `uv run ruff check src tests migrations` | — |
| Web components | `corepack pnpm --filter web test` | TS-020/021/022 (new `__tests__/generation-panel.test.tsx`) |
| Web lint/type | `corepack pnpm web:lint` / `web:typecheck` | — |
| Public E2E | `corepack pnpm --filter web test:e2e` | regression (3 specs) |
| Authenticated E2E (live stack) | `CLERK_E2E=1 ... playwright test` | TS-023/025/027/029 |
| Authenticated E2E (fault instance) | same + `LESSONCANVAS_MODEL_ADAPTER=fake` backend profile, small cap env | TS-026/028 |
| Accessibility | Playwright a11y checks + manual keyboard pass | TS-024 |

## Rollout, Compatibility, and Rollback

- Additive migration only; no existing contract changes (supersession hook extends an existing transaction in-place).
- New UI surface is additive; the four existing views unchanged.
- Rollback = revert the feature branch; dropped tables are new (no legacy data loss risk; project data in existing tables unaffected).
- Live-model cost: E2E live scenarios bounded by the per-run cap and one-off; deterministic suites use fakes.

## Risks and Decisions

| Risk / decision | Handling |
| --- | --- |
| Cap setting shared with discovery/planning (`max_model_calls_per_run`) may be too small for a full unit | T0 confirms the default against per-lesson accounting (draft + narration + bounded retries for K lessons); if insufficient, introduce a generation-specific setting — a config addition, not a contract change |
| Real-Worker participation in E2E | E2E profile starts the actual Celery worker against compose services; eager mode only for integration crash simulation (TS-004) |
| SSE replay correctness under rapid events | Replay query ordered by `(run_id, seq)`; integration test TS-007 asserts no loss/duplication across reconnects |
| python-docx structural checks as openability evidence | Documented Spec assumption; F009 may strengthen |

## Interleaved Tasks

- [ ] T0 Contracts + persistence base: Zod/Pydantic DTOs and SSE envelope frozen; migration for `generation_runs`/`lesson_plan_artifacts`/`run_events`; ORM models; atomic idempotent start primitive; cap accounting confirmed (default or generation-specific setting). Exit: migration applies; TS-001/TS-015 integration proofs pass.
- [ ] T1 Run orchestration core: run service (state transitions, resume eligibility, supersession marking on brief re-confirm), event-log append + replay query, snapshot assembly. Exit: TS-005/TS-007/TS-010 pass.
- [ ] T2 Generation workflow + tools: LangGraph graph with three specialists, per-lesson checkpoints, render/validate tools with MCP-compatible definitions, FakeModelAdapter generation scripts (incl. injection payloads). Exit: TS-002/TS-003/TS-012/TS-016/TS-017/TS-019 pass.
- [ ] T3 Celery dispatch + bounded retry: worker task, retry policy, eager redelivery crash simulation. Exit: TS-004 passes; health_check unaffected.
- [ ] T4 Generation API + SSE + download: five endpoints with ownership authorization, SSE with `Last-Event-ID`, non-disclosing denial, trace emission. Exit: TS-008/TS-009/TS-011/TS-013/TS-018 pass.
- [ ] T5 Deletion cascade + audit: project/account deletion covers new tables and binaries. Exit: TS-014 passes.
- [ ] T6 Web foundation + generation panel: API client/types, SSE hook, `教案生成` view, state matrix, resume modal, reconnect banner, desktop gate. Exit: TS-020/021/022 pass; existing 16 web tests green.
- [ ] T7 E2E suites + accessibility: live-stack journeys (TS-023/025/027/029), fault-instance profile (TS-026/028), a11y automated checks + manual keyboard pass (TS-024). Exit: all E2E green with recorded evidence.
- [ ] T8 Review + docs sync + delivery prep: self review (`review.md`), API/DATABASE/TESTING/UX doc updates per impact, ROADMAP/STAGE/Issue sync, PR-ready summary. Exit: Review recorded; docs synced; `READY FOR PR`.

## Start Checklist

- [x] All required Gates are PASS. — SPEC/UI/TEST DESIGN all PASS (records in artifacts)
- [x] Gate input manifests match current working-tree revisions. — hashes in Ready Inputs
- [x] Plan does not redefine Scope, rules, contract, or Acceptance. — Requirement Guardrail `NONE`
- [x] Major dependency/architecture/migration decisions are confirmed. — Spec D1–D8 and UI D-GEN/D-PROG/D-NARR/D-ART/D-RECN approved; additive migration only
- [x] Tasks interleave code, tests, and docs. — each Task lists TS coverage; T8 carries docs sync
- [x] Each Task has an observable completion condition. — Exit criteria per Task

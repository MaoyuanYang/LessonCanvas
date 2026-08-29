# Implementation Plan: F004 Editable Lesson Slide Decks

## Ready Inputs

- Spec: `specs/F004-editable-lesson-slide-decks/spec.md` @ `b913da61ec40` (`SPEC READY` PASS, 2026-08-29)
- UX/UI: `specs/F004-editable-lesson-slide-decks/ux-ui.md` @ `ux-ui-f004-r1` / approved content `05e5748c9a4d` (`UI READY` PASS, 2026-08-29)
- Test Design: `specs/F004-editable-lesson-slide-decks/test-design.md` @ `test-design-f004-r1` / `4afef155b09f` (`TEST DESIGN READY` PASS, 2026-08-29)
- Governing docs: `AGENTS.md` @ `b03a2200602b`, `docs/ARCHITECTURE.md` @ `a3118a75d52b`, `docs/API.md` @ `4754312ca25d`, `docs/DATABASE.md` @ `bf60367cb349`, `docs/TESTING.md` @ `2e6cfdf98fe9`, `docs/DESIGN_SYSTEM.md` @ `3445d793fa21`, `docs/FRONTEND.md` @ `8ff126475523`, ADR-0004 @ `7b4a56764d3f` (full manifest in Spec Gate Record; VCS base `b727734`)
- Work item: [Issue #8](https://github.com/MaoyuanYang/LessonCanvas/issues/8)

## Requirement Guardrail

`NONE` — this plan changes no Scope, business rule, API contract semantics, or Acceptance Criterion. Any need to do so returns to Spec via Design Change.

## Current and Target Flow

### Current

- F003 delivered the version-bound generation lifecycle: `generation_runs` (unique per `(project_id, brief_version_id, blueprint_version_id)`), `lesson_plan_artifacts`, authoritative `run_events`, `run_orchestration` service, `artifact_production` LangGraph graph with `docx_tools.py`, Celery `generate_unit`, five generation endpoints, `generation-panel.tsx` (fifth view `教案生成`), and deletion cascade.
- No PPTX code exists anywhere; no deck tables, endpoints, or UI.
- Supersession marks active generation runs at brief re-confirmation (single-kind today).

### Target

```text
lesson-plan run COMPLETE for (brief vN + blueprint vM)
  -> POST /decks/generation/start: atomic idempotent deck run row
       (unique per project+versions+artifact kind; prerequisite run recorded)
  -> Celery dispatch -> Worker runs LangGraph deck graph:
       context assembler (lesson-plan content as primary input) -> per lesson:
       deck writer (model) -> render (python-pptx tool) -> validate (tool)
       per-deck checkpoint rows + run event log appends in PostgreSQL
  -> GET /decks/generation snapshot (structure summaries) | /decks/generation/events SSE (Last-Event-ID)
  -> outcomes: complete | partial_failure | capped_failure | superseded | terminal_failure
  -> resume re-dispatches same run (eligible states only); download streams authorized PPTX
```

## Affected Surface

| Area | Path / artifact | Change |
| --- | --- | --- |
| Persistence | `apps/backend/migrations/` (new) | `generation_runs.artifact_kind` (default `lesson_plan`) + `prerequisite_run_id` self-FK (nullable); unique identity extended to `(project_id, brief_version_id, blueprint_version_id, artifact_kind)`; new `slide_deck_artifacts` table (run id, lesson index, status, object key, checksum, validation outcome, slide count, language mode; unique `(run_id, lesson_index)`) |
| Models | `src/lessoncanvas/models.py` | `SlideDeckArtifact` ORM model; `GenerationRun.artifact_kind` + `prerequisite_run_id`; deletion-cascade relationships |
| Run orchestration | `src/lessoncanvas/modules/run_orchestration/` | Kind-aware extensions: `start_deck_generation` (prerequisite check + idempotent identity), deck snapshot with structure summaries, resume, cap accounting reuse; supersession marking covers deck runs |
| Artifact production | `src/lessoncanvas/modules/artifact_production/` | `pptx_tools.py` (render + structural validate with MCP-compatible definitions, ADR-0004 pattern); deck LangGraph graph (3 specialists per D6) consuming lesson-plan content; deck trace events (`model.generation_write_deck`, `tool.render_lesson_deck_pptx`, `tool.validate_lesson_deck_pptx`) |
| Worker | `src/lessoncanvas/worker.py` | `generate_decks` task, bounded retry policy, eager-mode testability |
| API | `src/lessoncanvas/api/decks.py` (new) | start / snapshot / events SSE / resume / slide-deck download; registered in `main.py` |
| Settings | `src/lessoncanvas/settings.py` | `max_model_calls_per_deck_run` (default mirrors lesson-plan cap accounting), deck slide-count bounds (`deck_max_slides`, `deck_max_stage_slides`) |
| Fake adapter | `src/lessoncanvas/adapters/model.py` | Deterministic deck-writer scripts (`generation_write_deck` kind), per-lesson success/failure scripting, injection payloads |
| Trace/deletion | existing services | Deck trace events; deletion cascade to `slide_deck_artifacts` + binaries |
| Web shared components | `apps/web/components/` (new) | D-DECKDS promotion: shared artifact progress list + run outcome banner components; `generation-panel.tsx` refactored to consume them (behavior-preserving) |
| Web deck surface | `apps/web/lib/api.ts`, `components/deck-panel.tsx` (new), `components/workspace-view.tsx` | Sixth context view `课件生成`, deck DTOs (Zod), SSE reuse, states per ux-ui.md |
| E2E | `apps/web/e2e/deck-journeys.spec.ts` (new) | Six deck journeys per TQ-002 dual-instance strategy; `authenticated.spec.ts` unchanged (regression isolation) |
| Test base | `apps/backend/tests/conftest.py` | TRUNCATE list gains `slide_deck_artifacts` |

## Implementation Approach

### Domain / Application

- Deck run state machine identical to F003 (run: queued/generating/validating/complete/partial_failure/capped_failure/superseded/terminal_failure + dispatch-time teacher_blocked; per-lesson deck: pending/drafting/rendering/validating/complete/failed).
- Deck graph: `assemble_context` once per run (lesson-plan artifacts' content per lesson = primary input, plus confirmed brief/blueprint grounding context); per-lesson subflow `write -> render -> validate` with checkpoint persistence; D5 classification and bounded in-lesson retry.
- Writer model contract per D1: structured JSON deck draft (title, objectives, key/difficult points, stage slides at most two per teaching stage, homework, speaker notes with citations); total deck slides bounded by `deck_max_slides`.

### Data / Migration

- One additive-plus-constraint migration: new columns default `lesson_plan` (existing rows backfilled by server default — no data rewrite); identity constraint swap in one migration; `slide_deck_artifacts` FK to `generation_runs`; no legacy rewrite.
- Object storage: PPTX under workspace/project-scoped keys `artifacts/{workspace_id}/{project_id}/{run_id}/lesson-{index:02d}.pptx` (deck runs have distinct run ids, so no collision with DOCX keys); artifact row stores key + checksum; binary existence verified before ready.

### API / Integration

- Five deck endpoints per Spec API Behavior; SSE envelope and DTOs frozen schema-first in T0 (Zod on web, Pydantic on API) within Spec semantics; deck event payloads add slide count on lesson completion.
- SSE: per-run monotonic `id`, `Last-Event-ID` maps to replay query; replay and snapshot read-only.
- Download: streamed from storage through the app boundary with ownership check; denial non-disclosing; PPTX media type.

### Transaction / Idempotency / Concurrency / Consistency

- Deck start: single transaction — ownership check, prerequisite lesson-plan run check (`complete` status on same bound versions), unique-constraint insert with artifact kind (duplicate -> select existing), dispatch handoff; prerequisite failure raises the requirement error inside the same boundary (no partial state).
- Per-lesson idempotency: deck outcome rows keyed by `(run_id, lesson_index)`; completed decks skipped by state.
- Supersession: existing brief-confirm transaction marks ALL active runs (both kinds) superseded; in-flight lesson finishes its current step, then stops without publishing.
- Cap: same conditional-UPDATE guard, bound to the deck run's own cap setting.

### Frontend State / Components / UI States

- D-DECKDS first: extract `artifact-progress-list` and `run-outcome-banner` shared components from `generation-panel.tsx` with identical props semantics; F003 suite must stay green unchanged (TS-023) before the deck panel consumes them.
- `deck-panel.tsx` implements D-DECKGEN/D-DECKPROG/D-DECKNARR/D-DECKART/D-DECKRECN surfaces and the ux-ui.md state matrix; two unavailable kinds (blueprint gate; lesson-plan prerequisite) each link to their view; structure summary (slide count + validation status) per lesson; desktop-required gate below 1024px for start/resume; monitoring + downloads preserved.
- API client: typed deck functions + Zod DTOs mirroring the F003 client pattern; SSE hook reuse.

### Security / Validation / Error Handling

- Every deck endpoint authorizes by recorded workspace ownership; cross-workspace = non-disclosing denial class.
- Generated deck content and speaker notes treated as untrusted output at every boundary (inert rendering; no tool grant from content).
- Error mapping per ux-ui.md table (9 rows incl. both REQUIREMENT kinds); no storage paths, prompts, or provider details leak.

### Observability

- Trace events for every deck model call, tool call (render/validate), specialist transition, failure, and retry with cost/latency (ADR-0003); each lesson's deck-draft trace records the consumed lesson-plan content as input context (AC-018).
- Deck run event log doubles as SSE source and F006 evidence base.

## Test Execution Plan

| Suite | Command | Scenarios |
| --- | --- | --- |
| Backend unit/integration/API | `cd apps/backend && uv run pytest` | TS-001..TS-019 (new `tests/test_deck_generation.py`; existing 102 tests stay green) |
| Backend lint | `uv run ruff check src tests migrations` | — |
| Web components | `corepack pnpm --filter web test` | TS-020/021/022/023 (new `__tests__/deck-panel.test.tsx`; existing 22 green unchanged) |
| Web lint/type | `corepack pnpm web:lint` / `web:typecheck` | — |
| Public E2E | `corepack pnpm --filter web test:e2e` | regression (3 specs) |
| Deck E2E (live stack) | `CLERK_E2E=1 ... playwright test deck-journeys` | TS-027/029/030 |
| Deck E2E (fault instance) | same + `LESSONCANVAS_MODEL_ADAPTER=fake` backend profile, small deck-cap env | TS-025/026/028 |
| Accessibility | Playwright a11y checks + scripted/manual keyboard pass | TS-024 |
| Manual Office smoke | controlled open of TS-030 artifacts in PowerPoint/WPS | TS-031 |

## Rollout, Compatibility, and Rollback

- Additive schema + constraint swap on a single-kind table (existing rows default `lesson_plan`); no existing contract changes; F003 lesson-plan flow behavior identical (proven by unchanged suites).
- New UI surface is additive; the five existing views unchanged (except the behavior-preserving shared-component refactor covered by TS-023).
- Rollback = revert the feature branch; `slide_deck_artifacts` is new and `artifact_kind` defaults keep pre-F004 semantics; dropping the constraint swap restores the original identity.
- Live-model cost: deck live E2E bounded by the deck-run cap and one-off; deterministic suites use fakes.

## Risks and Decisions

| Risk / decision | Handling |
| --- | --- |
| Identity-constraint swap on `generation_runs` | Single migration: add kind column with server default, swap unique constraint atomically; verified against existing F003 integration suites (unchanged) plus TS-001/TS-015 deck proofs |
| Deck cap sizing (draft + bounded retries for K lessons) | `max_model_calls_per_deck_run` config mirrors lesson-plan accounting (default 20); confirmed in T0 against fake-adapter K-lesson runs |
| Slide-count bounds vs model verbosity | `deck_max_slides` (default 16) and `deck_max_stage_slides` (default 2) enforced in the writer contract and re-validated structurally (TS-012); changing them is configuration |
| D-DECKDS refactor regressing F003 surfaces | Extraction is props-identical; F003 suite must pass unchanged before deck panel work begins (TS-023 gate inside T6) |
| Manual Office smoke availability | Preferred: automated PowerPoint COM open-check on the TS-030 artifacts (no-repair open assertion) if Office is installed on the working machine; fallback: owner-observed manual pass; either way evidence recorded in test-design.md (TS-031) |
| Real-Worker participation in deck E2E | Reuse F003 dual-instance profile unchanged (TQ-002); eager mode only for integration crash simulation (TS-004) |

## Interleaved Tasks

- [x] T0 Contracts + persistence base: Zod/Pydantic deck DTOs and SSE envelope frozen; migration (`artifact_kind`, `prerequisite_run_id`, identity constraint swap, `slide_deck_artifacts`); ORM models; atomic idempotent deck-start primitive with prerequisite check; deck cap + slide-bounds settings. Exit: migration applies; TS-001/TS-015 integration proofs pass.
- [x] T1 Deck run orchestration: kind-aware run service (start/snapshot with structure summaries/resume), event-log reuse, supersession covering deck runs. Exit: TS-005/TS-006/TS-007/TS-010 pass.
- [x] T2 PPTX tools + deck workflow: `pptx_tools.py` render/validate with MCP-compatible definitions; deck LangGraph graph with per-lesson checkpoints and lesson-plan content as primary input (AC-018 trace evidence); FakeModelAdapter deck scripts incl. injection payloads. Exit: TS-002/TS-003/TS-012/TS-013/TS-016/TS-017/TS-019 pass.
- [x] T3 Celery deck dispatch + bounded retry: `generate_decks` task, retry policy, eager redelivery crash simulation. Exit: TS-004 passes; `generate_unit` unaffected.
- [x] T4 Deck API + SSE + download: five endpoints with ownership authorization, SSE with `Last-Event-ID`, non-disclosing denial, trace emission. Exit: TS-008/TS-009/TS-011/TS-018 pass.
- [x] T5 Deletion cascade: project/account deletion covers `slide_deck_artifacts` rows and PPTX binaries. Exit: TS-014 passes.
- [x] T6 Design System promotion + deck panel: extract shared artifact-progress-list and run-outcome-banner; refactor `generation-panel.tsx` (behavior-preserving, F003 suite green unchanged); API client/types; `课件生成` view + `deck-panel.tsx` state matrix; desktop gate. Exit: TS-020/021/022/023 pass; existing 22 web tests green.
- [ ] T7 Deck E2E + accessibility: `deck-journeys.spec.ts` six journeys per TQ-002 profiles; keyboard/a11y pass; manual Office smoke evidence (TS-031). Exit: TS-024..TS-031 recorded in test-design.md Execution Evidence Snapshot.
- [ ] T8 Review + docs sync + delivery prep: review.md findings; docs sync (DATABASE slide-deck artifact note, TESTING suite names, DESIGN_SYSTEM D-DECKDS promotion, UX/UI if affected); ROADMAP/STAGE/Issue sync; PR-ready summary. Exit: review recorded; documentation sync complete; `READY FOR PR` or authorized delivery.

## Start Checklist

- [x] All required Gates are PASS. — SPEC/UI/TEST DESIGN all PASS (records in artifacts)
- [x] Gate input manifests match current working-tree revisions. — hashes in Ready Inputs
- [x] Plan does not redefine Scope, rules, contract, or Acceptance. — Requirement Guardrail `NONE`
- [x] Major dependency/architecture/migration decisions are confirmed. — Spec D1–D9 and UI D-DECKGEN/D-DECKPROG/D-DECKNARR/D-DECKART/D-DECKRECN/D-DECKDS approved; additive migration + constraint swap on single-kind table
- [x] Tasks interleave code, tests, and docs. — each Task lists TS coverage; T8 carries docs sync
- [x] Each Task has an observable completion condition. — Exit criteria per Task

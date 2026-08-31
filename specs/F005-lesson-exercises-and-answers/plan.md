# Implementation Plan: F005 Lesson Exercises and Answers

## Ready Inputs

- Spec: `specs/F005-lesson-exercises-and-answers/spec.md` @ `41b391751a33` (`SPEC READY` PASS, 2026-08-31)
- UX/UI: `specs/F005-lesson-exercises-and-answers/ux-ui.md` @ `ux-ui-f005-r1` / approved content `78923f6468b7` (`UI READY` PASS, 2026-08-31)
- Test Design: `specs/F005-lesson-exercises-and-answers/test-design.md` @ `test-design-f005-r1` / `29b9ad5c42d2` (`TEST DESIGN READY` PASS, 2026-08-31)
- Governing docs: `AGENTS.md` @ `b03a2200602b`, `docs/ARCHITECTURE.md` @ `a3118a75d52b`, `docs/API.md` @ `4754312ca25d`, `docs/DATABASE.md` @ `d52f92251bcf`, `docs/TESTING.md` @ `30e2b1e0d8bd`, `docs/DESIGN_SYSTEM.md` @ `e49999bc7f00`, `docs/FRONTEND.md` @ `8ff126475523`, `docs/UX.md` @ `a60f881a0993`, `docs/UI.md` @ `17b0512ee49a`, ADR-0004 @ `7b4a56764d3f` (full manifest in Spec Gate Record; VCS base `main @ 123523a`)
- Work item: [Issue #10](https://github.com/MaoyuanYang/LessonCanvas/issues/10)

## Requirement Guardrail

`NONE` — this plan changes no Scope, business rule, API contract semantics, or Acceptance Criterion. Any need to do so returns to Spec via Design Change.

## Current and Target Flow

### Current

- F003 delivered the version-bound generation lifecycle and F004 generalized it per artifact kind: `generation_runs` (unique per `(project_id, brief_version_id, blueprint_version_id, artifact_kind)` with `lesson_plan` | `slide_deck`), per-kind artifact tables as per-lesson checkpoints, authoritative `run_events`, `run_orchestration` service with prerequisite gating, `artifact_production` graphs with `docx_tools.py`/`pptx_tools.py`, Celery `generate_unit`/`generate_decks`, five generation + five deck endpoints, `generation-panel.tsx`/`deck-panel.tsx` on shared `artifact-run.tsx` components (six views), supersession covering all kinds, and deletion cascade.
- No exercise code exists anywhere; no exercise tables, endpoints, or UI.

### Target

```text
lesson-plan run COMPLETE for (brief vN + blueprint vM)
  -> POST /exercises/generation/start {difficulty}: atomic idempotent exercise run row
       (unique per project+versions+artifact kind; prerequisite run recorded; tier recorded, immutable)
  -> Celery dispatch -> Worker runs LangGraph exercise graph:
       context assembler (lesson-plan content + blueprint objectives + tier as primary input)
       -> per lesson: exercise writer (model, one structured draft covering items WITH answers)
       -> render BOTH DOCX files (renderer owns continuous numbering)
       -> deterministic pair validation (E == A, sections, bounds, non-empty)
       per-pair checkpoint rows + run event log appends in PostgreSQL
  -> GET /exercises/generation snapshot (pair summaries + tier) | /exercises/generation/events SSE (Last-Event-ID)
  -> outcomes: complete | partial_failure | capped_failure | superseded | terminal_failure
  -> resume re-dispatches same run (eligible states only);
     download streams authorized DOCX per file parameter (exercise | answer)
```

## Affected Surface

| Area | Path / artifact | Change |
| --- | --- | --- |
| Persistence | `apps/backend/migrations/` (new) | `generation_runs.difficulty` (String(16), NULL, set only for exercise runs; NOT part of the unique identity per Spec D9); new `exercise_artifacts` table (run id, lesson index, status, exercise object key/checksum, answer object key/checksum, category count, item count, failure reason, retry count; unique `(run_id, lesson_index)`). No identity-constraint change — `exercise` is a new `artifact_kind` value on the existing unique tuple |
| Models | `src/lessoncanvas/models.py` | `ExerciseArtifact` ORM model; `GenerationRun.difficulty`; deletion-cascade relationships |
| Run orchestration | `src/lessoncanvas/modules/run_orchestration/` | `start_exercise_generation` (tier validation + prerequisite check + idempotent identity), exercise snapshot with pair summaries and tier, resume, cap accounting reuse; supersession already kind-agnostic |
| Artifact production | `src/lessoncanvas/modules/artifact_production/` | `exercise_docx_tools.py` (render exercise + answer files, deterministic pair validate, MCP-compatible definitions per ADR-0004); exercise LangGraph graph (3 specialists per D6); trace events (`model.generation_write_exercises`, `tool.render_lesson_exercises_docx`, `tool.validate_exercise_pair`) |
| Worker | `src/lessoncanvas/worker.py` | `generate_exercises` task, bounded retry policy, eager-mode testability |
| API | `src/lessoncanvas/api/exercises.py` (new) | start (difficulty body) / snapshot / events SSE / resume / download with `file=exercise\|answer`; registered in `main.py` |
| Settings | `src/lessoncanvas/settings.py` | `max_model_calls_per_exercise_run` (default 20), `exercise_min_items_per_lesson` (default 6), `exercise_max_items_per_lesson` (default 15), `exercise_min_categories_per_lesson` (default 3), `exercise_max_categories_per_lesson` (default 4) |
| Fake adapter | `src/lessoncanvas/adapters/model.py` | Deterministic exercise-writer scripts (`generation_write_exercises` kind) derived from scripted lesson plans; failure scripting (`TRANSIENT_FAIL`, `PROVIDER_FAIL`, `EXERCISE_MISSING_ANSWER`, `EXERCISE_ORPHAN_ANSWER`, `EXERCISE_EMPTY_ANSWER`, `EXERCISE_BAD_NUMBERING`), injection payloads |
| Trace/deletion | existing services | Exercise trace events with tier in writer input context (AC-018/019); deletion cascade to `exercise_artifacts` + both binaries |
| Web exercise surface | `apps/web/lib/api.ts`, `components/exercise-panel.tsx` (new), `app/(authed)/projects/[projectId]/workspace-view.tsx` | Seventh context view `练习与答案`; exercise DTOs (Zod) incl. difficulty enum; shared `artifact-run.tsx` consumed unchanged (third consumer); tier radio group (D-EXDIFF); dual download actions (D-EXART) |
| E2E | `apps/web/e2e/exercise-journeys.spec.ts` (new) | Seven exercise journeys per TQ-002 dual-instance strategy; existing specs unchanged (regression isolation) |
| Test base | `apps/backend/tests/conftest.py` | TRUNCATE list gains `exercise_artifacts` |

## Implementation Approach

### Domain / Application

- Exercise run state machine identical to F003/F004 (run: queued/generating/validating/complete/partial_failure/capped_failure/superseded/terminal_failure + dispatch-time teacher_blocked; per-lesson pair: pending/drafting/rendering/validating/complete/failed).
- Exercise graph: `assemble_context` once per run (lesson-plan artifact content per lesson + that lesson's blueprint objectives + the selected tier = primary input); per-lesson subflow `write -> render -> validate` with checkpoint persistence; D5 classification and bounded in-lesson retry.
- Writer model contract per D1: one structured JSON draft per lesson containing instructions (tier + covered objectives), 3–4 categories from the fixed catalog, and items each carrying stem (plus options where applicable) AND answer (plus optional rationale) — pairing exists by construction in the draft; the renderer owns continuous numbering 1..N across categories (mirroring F004's renderer-owned structural titles), and the pair validator independently re-checks the rendered files so a broken draft can never pass silently.

### Data / Migration

- One additive migration: nullable `difficulty` column (no default rewrite of existing rows) + new `exercise_artifacts` table FK to `generation_runs`; no identity-constraint change and no legacy rewrite.
- Object storage: both files under workspace/project-scoped keys `artifacts/{workspace_id}/{project_id}/{run_id}/lesson-{index:02d}-exercises.docx` and `...-answers.docx` (distinct run ids and suffixes, so no collision with lesson-plan DOCX keys); artifact row stores both keys + checksums; binary existence verified before ready.

### API / Integration

- Five exercise endpoints per Spec API Behavior; start body `difficulty ∈ {foundation, consolidation, advanced}` validated as a Pydantic literal; duplicate start returns the existing run regardless of requested tier (recorded tier wins, Spec D9); SSE envelope and DTOs frozen schema-first in T0 (Zod on web, Pydantic on API) within Spec semantics; exercise event payloads add item/category counts on lesson completion and the tier on start events.
- SSE: per-run monotonic `id`, `Last-Event-ID` maps to replay query; replay and snapshot read-only.
- Download: streamed from storage through the app boundary with ownership check; `file` parameter required and validated (`exercise` | `answer`); denial non-disclosing; DOCX media type.

### Transaction / Idempotency / Concurrency / Consistency

- Exercise start: single transaction — ownership check, prerequisite lesson-plan run check (`complete` status on same bound versions), tier validation, unique-constraint insert with artifact kind (duplicate -> select existing, recorded tier preserved), dispatch handoff; prerequisite or tier failure raises inside the same boundary (no partial state).
- Per-lesson idempotency: pair outcome rows keyed by `(run_id, lesson_index)`; completed pairs skipped by state.
- Supersession: existing brief-confirm transaction already marks ALL active runs superseded (kind-agnostic from F004); in-flight lesson finishes its current step, then stops without publishing.
- Cap: same conditional-UPDATE guard, bound to the exercise run's own cap setting.

### Frontend State / Components / UI States

- Shared components consumed unchanged: `artifact-run.tsx` (`ArtifactProgressList` with `renderActions` slot hosting the two download buttons, `RunOutcomeBanners` with 练习/答案 noun, `NarrationRegion`, `ReconnectBanner`) — no extraction or modification, so F003/F004 suites stay green untouched (TS-023).
- `exercise-panel.tsx` implements D-EXGEN/D-EXDIFF/D-EXPROG/D-EXNARR/D-EXART/D-EXRECN surfaces and the ux-ui.md state matrix; two unavailable kinds (blueprint gate; lesson-plan prerequisite) each link to their view via the existing `onNavigate` pattern; required tier radio group (no default) replaced by the recorded tier once a run exists; pair summary (item + category counts) per lesson; desktop-required gate below 1024px for tier selection/start/resume; monitoring + downloads preserved.
- API client: typed exercise functions + Zod DTOs mirroring the F004 client pattern; inline SSE consumption reuse.

### Security / Validation / Error Handling

- Every exercise endpoint authorizes by recorded workspace ownership; cross-workspace = non-disclosing denial class.
- Generated exercise and answer content treated as untrusted output at every boundary (inert rendering; no tool grant from content).
- Error mapping per ux-ui.md table (10 rows incl. both REQUIREMENT kinds and the tier VALIDATION case); no storage paths, prompts, or provider details leak.

### Observability

- Trace events for every exercise model call, tool call (render/validate pair), specialist transition, failure, and retry with cost/latency (ADR-0003); each lesson's exercise-draft trace records the consumed lesson-plan content and blueprint objectives as primary input context and names the bound difficulty tier (AC-018/AC-019).
- Exercise run event log doubles as SSE source and F006 evidence base.

## Test Execution Plan

| Suite | Command | Scenarios |
| --- | --- | --- |
| Backend unit/integration/API | `cd apps/backend && uv run pytest` | TS-001..TS-019 (new `tests/test_exercise_generation.py`; existing 124 tests stay green) |
| Backend lint | `uv run ruff check src tests migrations` | — |
| Web components | `corepack pnpm web:test` | TS-020/021/022/023 (new `__tests__/exercise-panel.test.tsx`; existing 30 green unchanged) |
| Web lint/type | `corepack pnpm web:lint` / `web:typecheck` | — |
| Public E2E | `corepack pnpm --filter web test:e2e` | regression (3 specs) |
| Exercise E2E (live stack) | `CLERK_E2E=1 ... playwright test exercise-journeys` | TS-027/029/030 |
| Exercise E2E (fault instance) | same + `LESSONCANVAS_MODEL_ADAPTER=fake` backend profile, small exercise-cap env | TS-025/026/028 |
| Accessibility | Playwright a11y checks + scripted/manual keyboard pass | TS-024 |
| Manual Office smoke | controlled open of TS-030 artifacts (both files) in Word/WPS | TS-031 |

## Rollout, Compatibility, and Rollback

- Additive schema only (nullable column + new table); no existing contract changes; F003/F004 flows behavior-identical (proven by unchanged suites).
- New UI surface is additive; the six existing views unchanged (shared components consumed as-is).
- Rollback = revert the feature branch; `exercise_artifacts` is new and `difficulty` is nullable, so pre-F005 semantics are trivially restored.
- Live-model cost: exercise live E2E bounded by the exercise-run cap and one-off; deterministic suites use fakes.

## Risks and Decisions

| Risk / decision | Handling |
| --- | --- |
| Pairing correctness despite model numbering drift | Renderer owns continuous numbering from the structured draft (model never numbers), and the pair validator independently re-checks the rendered files; fake-adapter pairing-negative scripts prove the validator catches every mismatch class (TS-012) |
| Exercise cap sizing (draft + bounded retries for K lessons) | `max_model_calls_per_exercise_run` default 20 mirroring existing accounting; confirmed in T0 against fake-adapter K-lesson runs |
| Item/category bounds vs model verbosity | `exercise_min/max_items_per_lesson` (6/15) and `exercise_min/max_categories_per_lesson` (3/4) enforced in the writer contract and re-validated structurally (TS-012); changing them is configuration |
| Difficulty column misuse (accidental tier overwrite) | Tier is write-once at run creation; the start path selects the existing run on duplicates without touching `difficulty`; TS-001/TS-015 prove immutability |
| Seventh-view integration regressing existing panels | No shared-component modification; TS-023 unchanged-suite proof plus new seventh-tab assertions |
| Manual Office smoke availability | Preferred: automated Word COM open-check on the TS-030 artifacts (no-repair open assertion on both files) if Word is installed on the working machine (it was for F004's PowerPoint smoke); fallback: owner-observed manual pass; either way evidence recorded in test-design.md (TS-031) |
| Real-Worker participation in exercise E2E | Reuse the dual-instance profile unchanged (TQ-002); eager mode only for integration crash simulation (TS-004); TS-026/TS-028 carry the F004 M-1 Clerk-dev-instance risk with the same substitute-plus-residual pattern |

## Interleaved Tasks

- [x] T0 Contracts + persistence base: Pydantic/Zod exercise DTOs and SSE envelope frozen (incl. difficulty literal and pair summary fields); migration (`generation_runs.difficulty` nullable, `exercise_artifacts` table); ORM models; atomic idempotent exercise-start primitive with prerequisite + tier validation; exercise cap + item/category bounds settings; fake-adapter `generation_write_exercises` base scripts. Exit: migration applies; TS-001/TS-015 integration proofs pass.
- [x] T1 Exercise run orchestration: kind-aware run service (start/snapshot with pair summaries + tier/resume), event-log reuse, supersession coverage proof. Exit: TS-005/TS-006/TS-007/TS-010 pass.
- [x] T2 DOCX pair tools + exercise workflow: `exercise_docx_tools.py` render-both-files + deterministic pair validate with MCP-compatible definitions; exercise LangGraph graph with per-pair checkpoints, lesson-plan content + objectives + tier as primary input (AC-018/019 trace evidence), renderer-owned numbering; FakeModelAdapter pairing-negative + injection scripts. Exit: TS-002/TS-003/TS-012/TS-013/TS-016/TS-017/TS-019 pass.
- [x] T3 Celery exercise dispatch + bounded retry: `generate_exercises` task, retry policy, eager redelivery crash simulation. Exit: TS-004 passes; `generate_unit`/`generate_decks` unaffected.
- [x] T4 Exercise API + SSE + dual download: five endpoints with ownership authorization, start-body tier validation, SSE with `Last-Event-ID`, `file`-parameter download with non-disclosing denial, trace emission. Exit: TS-008/TS-009/TS-011/TS-018 pass.
- [x] T5 Deletion cascade: project/account deletion covers `exercise_artifacts` rows and both binaries. Exit: TS-014 passes.
- [x] T6 Exercise panel + seventh view: API client/types; `练习与答案` view + `exercise-panel.tsx` state matrix with tier radio group (D-EXDIFF) and dual download (D-EXART); shared `artifact-run.tsx` consumed unchanged; desktop gate. Exit: TS-020/021/022/023 pass; existing 30 web tests green.
- [x] T7 Exercise E2E + accessibility: `exercise-journeys.spec.ts` seven journeys per TQ-002 profiles; keyboard/a11y pass incl. tier fieldset; Word/COM smoke evidence on both files (TS-031). Exit: TS-024..TS-031 recorded in test-design.md Execution Evidence Snapshot.
- [x] T8 Review + docs sync + delivery prep: review.md findings; docs sync (DATABASE exercise-artifact note, TESTING suite names, UX/UI seventh view, DESIGN_SYSTEM third-consumer note, API/DATABASE open items); ROADMAP/STAGE/Issue sync; PR-ready summary. Exit: review recorded; documentation sync complete; `READY FOR PR` or authorized delivery.

## Start Checklist

- [x] All required Gates are PASS. — SPEC/UI/TEST DESIGN all PASS (records in artifacts)
- [x] Gate input manifests match current working-tree revisions. — hashes in Ready Inputs
- [x] Plan does not redefine Scope, rules, contract, or Acceptance. — Requirement Guardrail `NONE`
- [x] Major dependency/architecture/migration decisions are confirmed. — Spec D1–D9 and UI D-EXGEN/D-EXDIFF/D-EXPROG/D-EXNARR/D-EXART/D-EXRECN approved; additive migration only, no identity-constraint change (difficulty excluded from identity per D9)
- [x] Tasks interleave code, tests, and docs. — each Task lists TS coverage; T8 carries docs sync
- [x] Each Task has an observable completion condition. — Exit criteria per Task

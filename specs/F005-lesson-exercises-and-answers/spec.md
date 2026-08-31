# F005: Lesson Exercises and Answers

- Spec Status: `SPEC READY`
- Roadmap Status: `DONE`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #10](https://github.com/MaoyuanYang/LessonCanvas/issues/10)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F003` (DONE) for the version-bound run, per-lesson inventory, trace, progress, and recovery contract
- Last Updated: 2026-08-31

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-31
- Decision Authority: `YMY / Project Owner` — approved via interactive session (refinement decisions D1/D3/D7/D9 selected interactively 2026-08-31; D2/D4/D5/D6/D8 confirmed with Spec approval), scope: F005 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-020, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F005-lesson-exercises-and-answers/spec.md` @ `41b391751a33`
  - `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `77cac3f8a2c1`
  - `specs/F004-editable-lesson-slide-decks/spec.md` @ `9011ff986157`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `dae7518aeaea`
  - `docs/API.md` @ `4754312ca25d`
  - `docs/DATABASE.md` @ `d52f92251bcf`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/adr/0002-stateful-agent-and-async-execution.md` @ `5145b0ff319f`
  - `docs/adr/0003-user-owned-complete-run-traces.md` @ `d0e2fcd0c587`
  - `docs/adr/0004-mcp-tool-and-source-protocol.md` @ `7b4a56764d3f`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Exercise/answer document grammar and category catalog | Fixed catalog of six senior-high English exercise categories: `multiple_choice` (选择题), `fill_in_the_blank` (填空题), `short_answer` (简答题), `reading_comprehension` (阅读理解), `translation` (翻译), `written_expression` (书面表达). Per lesson the exercise writer selects a bounded 3–4 categories derived from that lesson's confirmed blueprint objectives and language mode; total continuously numbered items per lesson stays within configured bounds. Exercise DOCX sections: lesson title (unit + lesson), a brief instructions block naming the difficulty tier and covered objectives, then one numbered section per selected category with continuous Arabic numbering across the whole set. Answer DOCX sections: the same lesson title, then one answer section whose entries carry exactly the same numbers, each with non-empty answer or reference content (writing tasks get reference points/model text; there is no non-answer outcome). | `YMY / Project Owner`, 2026-08-31 (interactive selection: blueprint-objective-driven categories) |
| D2 | Checkpoint and recovery granularity | The exercise/answer pair is the checkpoint unit, inherited from F003 D2: one lesson = model draft → render both DOCX files → deterministic pair validation; a pair is complete only when all three succeed. Resume skips every completed pair and continues only failed or incomplete lessons. | Inherited from F003 D2; confirmed with Spec approval |
| D3 | Eligibility prerequisite and cost model | Exercise generation requires a complete lesson-plan run bound to the same confirmed brief and blueprint versions; the exercise writer consumes that run's lesson-plan content together with the lesson's confirmed blueprint objectives as primary context, so practice aligns to the confirmed teaching sequence. Slide-deck runs are not a prerequisite. The exercise run carries its own per-run model-call cap; no workspace-level concurrent-run limit (F003 D3 policy). | `YMY / Project Owner`, 2026-08-31 (interactive selection; mirrors F004 D3 without the deck requirement) |
| D4 | Progress and event contract | Inherited from F003 D4: the PostgreSQL run-event log is authoritative, SSE events carry per-run monotonic ids, `Last-Event-ID` reconnect replays missed events, a pollable snapshot stays available, and replay never triggers model work. | Inherited from F003 D4; confirmed with Spec approval |
| D5 | Failure taxonomy and retry policy | Inherited from F003 D5 (Retryable / Teacher-blocked / Terminal) applied to exercise runs. Teacher-blocked additionally covers a missing or incomplete lesson-plan run for the bound versions. | Inherited from F003 D5; confirmed with Spec approval |
| D6 | Specialist split | Minimal explicit specialists inside one LangGraph workflow: unit-context assembler (extended to assemble the confirmed lesson-plan content and blueprint objectives per lesson plus the selected difficulty tier), exercise writer (one structured exercise+answer draft per lesson), pair validator (deterministic structural and pairing check per rendered pair). No free-form Agent-to-Agent conversation; orchestration is explicit. | Inherited from F003 D6; confirmed with Spec approval |
| D7 | Validation standard | Deterministic structural and pairing validation only: both files present, non-empty, openable by the DOCX parser; required sections per the D1 grammar; item numbering starts at 1 and is contiguous within configured item-count bounds; the set of numbered answer entries equals the set of numbered exercise items exactly (no missing answer, no orphan answer); every answer entry is non-empty after trimming. Answer correctness, language quality, and objective-coverage quality are NOT judged here — they belong to F008/F009. One controlled manual Word/WPS open smoke is recorded as delivery evidence; CI carries no Office dependency. | `YMY / Project Owner`, 2026-08-31 (interactive selection: deterministic pairing checks; correctness deferred to F008) |
| D8 | Rendering and storage engineering | `python-docx` renders and validates the DOCX pair (pure Python, no external Office dependency) behind MCP-compatible internal tool definitions (ADR-0004 pattern). One artifact record per lesson holds both object keys and checksums — the pair is the record unit. Binaries go to the existing private object storage under workspace/project scoping; artifact truth stays in PostgreSQL. Exercise runs reuse the F003 run lifecycle as a new artifact kind; the concrete table strategy is finalized by the Implementation Plan. | Engineering; confirmed with Spec approval |
| D9 | Difficulty selection and binding | The teacher selects one structured difficulty tier (`foundation` / `consolidation` / `advanced`) when starting generation; the tier is required at start, recorded on the run, immutable for that run, surfaced in every snapshot, and drives the exercise writer's guidance. Run identity remains (project, confirmed brief version, blueprint version, artifact kind) without the tier: a duplicate same-version start returns the existing run with its recorded tier and never creates a second run or overwrites the tier; selecting a different tier for new work requires a new confirmed version through the existing supersession path (F007 adds targeted regeneration later). Parallel multi-tier artifact sets per version pair are deliberately not offered in Phase 1. | `YMY / Project Owner`, 2026-08-31 (interactive selection: structured difficulty choice at start) |

## Goal

Generate a paired editable DOCX exercise set and answer set for every lesson in one confirmed unit through the established version-bound, traced, and recoverable run lifecycle, with deterministic structural and pairing validation before ready status and owner-authorized download.

## Business Value

Exercises and answers complete the core teaching package while making objective coverage, pairing completeness, and file integrity observable and recoverable, without creating a second workflow authority or a student-data surface.

## User Story

As a senior-high English teacher, I want editable exercises with paired answers for each lesson at a difficulty I choose, so that classroom practice and assessment reflect the objectives and content I confirmed.

## Scope

- Start one asynchronous, idempotent, version-bound exercise generation run from the current confirmed brief and blueprint versions, gated on a complete lesson-plan run for the same versions (D3), with a required structured difficulty tier (D9).
- Orchestrate the three explicit specialists (D6) for all-lesson pair generation, consuming confirmed lesson-plan content and blueprint objectives as primary context.
- Generate one editable exercise DOCX and one paired answer DOCX per blueprint lesson under the D1 grammar, with continuous item numbering shared by both files.
- Capture complete owner-scoped run traces and per-stage cost/latency evidence.
- Enforce the exercise run's own per-run model-call cap before each expensive call.
- Acknowledge submission quickly and show phase-level plus per-lesson progress with pair summaries (category and item counts, difficulty tier).
- Make duplicate submission and Worker retry reuse the same run and per-lesson checkpoints (D2).
- Validate delivered pairs with deterministic structural and pairing checks (D7) and authorize downloads of both files.
- Register exercise-rendering and pair-validation tools with MCP-compatible definitions consumed by the workflow.

## Out of Scope

- Student submission, automatic grading, grade storage, or student-specific adaptation; no real student response, identity, or grade data enters generation or evaluation.
- A general question bank, item marketplace, or LMS export.
- Browser-based DOCX editing.
- Answer-correctness, language-quality, and objective-coverage evaluation (F008/F009); F005 only represents deterministic findings honestly.
- Final cross-artifact alignment and external teacher validation (F008/F010).
- Difficulty re-selection on an existing run, and parallel multi-tier sets per version pair (D9; revisit with teacher evidence in the F007/F013 era).
- Redesigning the run lifecycle established by F003.

## Actors / Preconditions

- Actor: an authenticated teacher owning the workspace and project.
- Preconditions: a confirmed brief version and a confirmed blueprint version exist; the blueprint contains at least one lesson; a lesson-plan run bound to those same versions is `complete`; the workspace project quota is not exhausted; the model adapter and object storage are reachable.

## Main Flow

1. The teacher selects a difficulty tier and starts exercise generation from the workspace exercise entry.
2. The API atomically creates or returns the idempotent exercise run bound to the current confirmed brief and blueprint versions and the complete lesson-plan run, records the tier, acknowledges immediately, and dispatches the Celery task.
3. The Worker executes the LangGraph workflow: assemble per-lesson context from the confirmed lesson plan and blueprint objectives → write each exercise+answer draft → render both DOCX files → validate the pair, writing per-lesson checkpoints and run events to PostgreSQL.
4. Phase-level and per-lesson progress, including narration, streams over SSE; the teacher may leave, reconnect with replay, or stop narration without affecting the run.
5. When every lesson has a valid pair, the run completes; the teacher reviews pair summaries and downloads the authorized exercise and answer DOCX files.

## Alternative Flows

- Duplicate submission (same project, same confirmed versions, any tier): returns the existing exercise run with its recorded tier; no duplicate model work or artifacts.
- Missing or incomplete lesson-plan run at start: `teacher_blocked` with explicit recovery (generate and complete lesson plans first).
- Missing difficulty tier at start: input-validation error naming the required field and the three tiers.
- Provider transient failure or Worker crash mid-lesson: bounded Celery retry resumes the same run from the last per-lesson checkpoint; completed pairs remain intact.
- Per-run model-call cap exceeded: run enters an explicit capped-failure state; completed pairs remain downloadable; a teacher-visible recovery path is shown.
- Newer confirmed brief/blueprint version during an active run: the exercise run is marked superseded at the next safe checkpoint, stops, and cannot publish over the newer version.
- Narration stream stopped or disconnected: progress and pair production continue unaffected; SSE reconnect replays from the event log.
- Pair-validation failure for a lesson (missing section, non-contiguous numbering, item-count out of bounds, missing or orphan answer, empty answer content): that lesson enters failed state with the validation reason; other lessons continue; the lesson is eligible for bounded retry.

## Business Rules / Invariants

- An exercise run binds to exactly one immutable confirmed brief version, one blueprint version, the complete lesson-plan run bound to those versions, and one teacher-selected difficulty tier recorded at start.
- Every required lesson has at most one current exercise/answer pair outcome per artifact version while history remains immutable.
- Same-version duplicate exercise generation resolves to one run; PostgreSQL enforces run identity at the database boundary, distinguished from lesson-plan and slide-deck runs.
- Celery retry resumes the same run; PostgreSQL owns run state, per-lesson checkpoints, and the authoritative event log; Redis is transport only.
- An exercise run is complete only when every blueprint lesson has a pair that passed deterministic structural and pairing validation; partial success stays visible and recoverable.
- No model call proceeds when the exercise run's model-call cap is reached.
- A pair never becomes ready unless both referenced binaries exist and pass pair validation.
- Every numbered exercise item has exactly one numbered answer entry with non-empty content; a set failing this cannot be represented as ready (no non-answer outcome exists in this grammar).
- Exercises and answers derive from the same confirmed versions and the prerequisite lesson-plan run; they cannot silently introduce objectives or source claims outside them.
- Stale output never overwrites a newer version: supersession marks the old run and blocks publication.
- Complete traces (prompts, outputs, tools, costs, latency, failures) stay inside the owning workspace and are deleted with the project or account.
- Generated exercise content is untrusted output: it cannot change system policy, grant tools, or bypass authorization.

## State Transitions

Run (exercise): `queued -> generating -> validating -> complete | partial_failure | capped_failure | superseded | terminal_failure`. `teacher_blocked` is a dispatch-time state when required inputs are missing (confirmed versions or a complete lesson-plan run). Terminal states never transition back; `partial_failure` and `capped_failure` allow resume of eligible lessons; `superseded` is one-way.

Per lesson (pair): `pending -> drafting -> rendering -> validating -> complete | failed`. A failed lesson may re-enter drafting only through an eligible resume within the same run, preserving the per-lesson checkpoint rule (D2). Completed lessons never re-enter work.

## Data Changes

- New exercise artifact record per lesson: run id, lesson index, per-pair status, exercise object key and checksum, answer object key and checksum, validation outcome, category count and item count; artifact truth in PostgreSQL, binaries in private object storage.
- Exercise generation runs reuse the F003 run lifecycle as a new artifact kind value; the run record additionally stores the recorded difficulty tier (exact constraint strategy finalized by the Implementation Plan).
- Run-event records extend to exercise runs with exercise event payloads (including item/category counts and the difficulty tier on start events).
- Trace events extend the existing trace table with exercise generation stages.
- Project/account deletion cascades to exercise runs, exercise artifacts, events, traces, and object-storage binaries.

## API Behavior

- `POST /projects/{id}/exercises/generation/start` — body carries the required difficulty tier (`foundation` | `consolidation` | `advanced`); idempotent creation bound to current confirmed versions plus the complete lesson-plan run; returns run snapshot; duplicate same-version request returns the existing exercise run with its recorded tier; missing or incomplete lesson-plan run returns the teacher-blocked requirement error naming the prerequisite; missing or invalid tier returns an input-validation error.
- `GET /projects/{id}/exercises/generation` — authoritative run snapshot: status, difficulty tier, per-lesson pair outcomes with pair summaries, cap usage, bound versions.
- `GET /projects/{id}/exercises/generation/events` — SSE; events carry per-run monotonic ids; `Last-Event-ID` replays missed events; replay is read-only.
- `POST /projects/{id}/exercises/generation/resume` — re-dispatches the same run for eligible failures only; rejects terminal, superseded, or complete runs.
- `GET /projects/{id}/exercises/{artifactId}/download?file=exercise|answer` — workspace-authorized, streams the stored binary matching the artifact record; the `file` parameter is required and validated.
- Error semantics follow the project taxonomy: requirement/input, authentication, authorization/not-found, stale-version, quota (cap), provider/transient, partial-execution, unexpected. No storage paths or prompts leak in errors.
- Stop semantics: stopping narration does not cancel the run; run cancellation is not offered (supersession and completion are the exits).

## Error Cases

- Missing confirmed versions or missing/incomplete lesson-plan run at start: `teacher_blocked` with explicit recovery (confirm brief/blueprint, then generate and complete lesson plans).
- Missing or invalid difficulty tier at start: input-validation error listing the three accepted tiers.
- Cap exceeded mid-run: `capped_failure` state; completed pairs preserved and downloadable; recovery path shown.
- Provider hard failure after bounded retries: `terminal_failure`; completed pairs preserved; resume not offered for terminal provider failure.
- Object-storage write failure: lesson enters failed state; no pair becomes ready without both confirmed binaries.
- Validation failure (missing required sections, non-contiguous or out-of-bounds numbering, missing or orphan answer entries, empty answer content): per-lesson failed with the structural reason; eligible for bounded retry.
- Unauthorized download or cross-workspace access: authorization-denied class response without confirming existence.

## Idempotency / Concurrency / Transactions

- Exercise run creation is atomic in PostgreSQL across owner check, prerequisite check, version binding, tier recording, idempotent identity, and dispatch handoff; duplicate submissions and Celery redeliveries converge on one run.
- Per-lesson processing is idempotent per lesson index: a retried lesson re-executes only its own draft→render→validate chain; completed pairs are skipped by checkpoint.
- Event-log appends are monotonic per run; replay and polling are read-only.
- Supersession is applied transactionally when a new version is confirmed; an in-flight lesson finishes its current step and the run then stops at the checkpoint without publishing.

## Security / Privacy / Authorization

- Every exercise run, event, artifact, trace, and download is authorized by recorded workspace ownership.
- Generated exercise and answer content and model output are untrusted data; no tool grant, policy change, or cross-workspace leak through content.
- No real student response, identity, or grade data enters generation, validation, or evaluation.
- Complete traces remain workspace-scoped and are deleted with the project or account.
- Downloads never expose storage locations; authorization happens in the application boundary.

## Non-functional

- Submission acknowledgement is synchronous and fast; all generation work is asynchronous.
- One hosted model through the existing thin adapter; no provider routing added.
- The exercise run's per-run model-call cap, the per-lesson item-count bounds, and the category-count bounds are settings; changing them is configuration, not code.
- Exercise run events are retained for the life of the run (workspace-scoped) to support replay and F006 evidence.
- Worker concurrency uses existing Celery configuration; no new infrastructure product.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace exercise-generation entry with difficulty selection, per-lesson pair review with pair summary, download of both files, error recovery, superseded/stale presentation.
- Primary flow: select difficulty and start exercise generation (gated on complete lesson plans) → leave or monitor → inspect completed/failed scope → resume eligible failure → download editable exercise and answer DOCX files.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given a complete lesson-plan run for the current confirmed unit version, when exercise generation completes, then every planned lesson has an owner-authorized, openable, editable exercise DOCX and paired answer DOCX bound to that brief/blueprint version and lesson-plan run.
- AC-002: Given the same exercise-generation intent submitted twice, when both requests are handled, then they resolve to one run without duplicate model work or artifact publication.
- AC-003: Given a valid start request, when submitted, then the API acknowledges quickly with a queued run snapshot and pair generation proceeds asynchronously.
- AC-004: Given an active exercise run, when progress is observed, then phase-level and per-lesson status (pending/drafting/rendering/validating/complete/failed) with pair summary (category count, item count, validation status) and the difficulty tier is visible from the authoritative snapshot and events.
- AC-005: Given a transient provider failure after some pairs complete, when the run resumes, then completed pairs remain intact and only failed or incomplete lessons continue.
- AC-006: Given a Worker crash mid-run, when execution resumes (retry or teacher resume), then the same run continues from the last per-lesson checkpoint without re-running completed pairs.
- AC-007: Given the exercise run's model-call cap is reached, when further work is attempted, then no additional model call begins, the run enters an explicit capped state, completed pairs remain downloadable, and a recovery path is shown.
- AC-008: Given a newer confirmed version while an exercise run is active, when the run reaches its next safe checkpoint, then it is marked superseded, stops, and cannot publish over the newer version.
- AC-009: Given an SSE disconnect, when the client reconnects with `Last-Event-ID`, then missed events replay from the authoritative log and no new model work is triggered.
- AC-010: Given active exercise generation, when narration is stopped or fails, then progress and pair production continue unaffected.
- AC-011: Given a partially failed exercise run, when the teacher inspects it, then per-lesson outcomes with reasons and an eligible resume action are visible.
- AC-012: Given a download request for either file of a pair, when authorization passes, then the served binary matches the artifact record's corresponding key and checksum; when authorization fails, then access is denied without confirming existence.
- AC-013: Given any exercise run outcome, when reviewed, then complete prompts, outputs, tool calls, costs, latency, and failures are recorded in the owning workspace's trace.
- AC-014: Given a rendered pair, when validated, then both files are openable by the DOCX parser, contain the required sections per the D1 grammar, item numbering starts at 1 and is contiguous within configured item-count bounds, the numbered answer entries equal the numbered exercise items exactly, and every answer entry is non-empty; an invalid pair never reaches ready state.
- AC-015: Given project deletion, when deletion completes, then the project's exercise runs, exercise artifacts, events, traces, and stored binaries are deleted.
- AC-016: Given the confirmed brief's output-language mode, when exercises and answers are generated, then their content follows that language mode (zh-Hans / en / bilingual).
- AC-017: Given no lesson-plan run or an incomplete lesson-plan run for the current confirmed versions, when exercise generation is started, then the request fails with an explicit teacher-blocked requirement state naming the prerequisite and its recovery action.
- AC-018: Given the exercise-generation trace, when reviewed, then the confirmed lesson-plan content and blueprint objectives for each lesson are recorded as the primary input context of that lesson's exercise draft.
- AC-019: Given a teacher-selected difficulty tier at start, when the run executes, then the tier is recorded on the run, surfaced in every snapshot, and drives the exercise writer's guidance; and given a duplicate start requesting a different tier, when handled, then the existing run is returned with its recorded tier and no second run is created or tier overwritten.
- AC-020: Given a lesson's confirmed objectives and language mode, when the exercise set is drafted, then it uses 3–4 categories from the fixed six-category catalog selected by objective fit, with continuous numbering across the set and a total item count within configured bounds.

## Open Questions

All DRAFT open questions are resolved by D1–D9 above. Non-blocking residuals:

- [DEFERRED, owner-approved] Exact per-lesson item-count bounds, category-count bounds, and the exercise-run cap default are configuration; exact numbers are set in the Implementation Plan and recorded in settings.
- [DEFERRED, owner-approved] Teacher-facing wording of the three difficulty tiers is a UX-copy choice owned by the UX/UI refinement; enum values (`foundation`/`consolidation`/`advanced`) are fixed here.
- [DEFERRED, revisit with teacher evidence] Parallel multi-tier artifact sets per version pair and tier re-selection without re-confirmation are deliberately excluded (D9); revisit in the F007/F013 era if layered practice sets become a confirmed teacher need.

## Risks and Assumptions

- [CONFIRMED] Severe answer errors prevent product-validation success and cannot be hidden by file completion; deterministic pairing checks expose structure and coverage, not correctness — correctness stays with F008/F009 and is never claimed by this Feature.
- [CONFIRMED] Student submissions and grades are prohibited; no student personal data enters any surface.
- [CONFIRMED] Editable DOCX pairs are required; PDF-only or combined single-file output does not satisfy the Feature.
- [CONFIRMED] Correctness and recoverability take priority over fixed complete-unit duration.
- [CONFIRMED] Complete traces are required for every exercise run despite storage and privacy cost (ADR-0003).
- [ASSUMED] `python-docx` structural/pairing validation plus one controlled manual Word open smoke is sufficient evidence of openability and editability for Phase-1 claims; F009 may add stronger file evidence.
- [ASSUMED] The bounded six-category catalog fits the representative units and language modes (owner-selected D1); a new category requires a Design Change, not silent prompt drift.
- [ASSUMED] Difficulty immutability per run (D9) is acceptable in Phase 1 because tier switching maps to the existing supersession path and F007 adds targeted regeneration.

## Gate Record: DONE

- Status: `PASS`
- Validation time: 2026-08-31
- Decision Authority: `YMY / Project Owner` — merge authorized in the interactive session (M-1 environment residual re-run-passed; M-2/M-3 recorded deviations accepted)
- Conditions met:
  - All 20 ACs satisfied with automated evidence (150 backend tests incl. 26 exercise; 39 web tests incl. 9 exercise-panel; migrations applied to test and dev DBs)
  - Exercise E2E: seven journeys green — TS-024/025/026 (fault stack, F003 eager profile), TS-028 (small-cap), TS-027/029/030 (live stack, real DeepSeek + real Celery Worker) — plus TS-031 Word 16.0 COM smoke over all 12 files of the TS-030 pairs (opens without repair, editable)
  - Live-model defect found and fixed during TS-030 (multi-line writing answers vs the first-line-anchored pairing regex) with regression test; suites re-verified after the fix
  - Review: no Critical findings; H-1 fixed; M-1 environment residual (re-run passed) with substitute coverage; M-2/M-3 recorded deviations; L-1 hygiene
  - Documentation sync: DATABASE/TESTING/DESIGN_SYSTEM updated; ROADMAP/STAGE/Issue synchronized
  - Delivery: PR [#11](https://github.com/MaoyuanYang/LessonCanvas/pull/11) merged `5804e86` (authorized commit/push/PR/merge by `YMY / Project Owner`); main re-verified (150 backend passed + ruff clean + 39 web tests passed)
- DONE evidence manifest (working-tree SHA-256 prefixes at gate time):
  - `spec.md` @ `807f4c857bf8`
  - `ux-ui.md` @ `98e79e83c0cd`
  - `test-design.md` @ `b9f922a0c5cb`
  - `plan.md` @ `d36cc2307cd8`
  - `review.md` @ `446769289540`
  - `specs/ROADMAP.md` @ `3d795c14b6db`
  - `AGENTS.md` @ `b03a2200602b`

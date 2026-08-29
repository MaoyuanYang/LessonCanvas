# F003: Recoverable Unit Lesson Plans

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #6](https://github.com/MaoyuanYang/LessonCanvas/issues/6)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F002` (DONE); live-model JSON-contract fixes (PR #5)
- Last Updated: 2026-08-29

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-29
- Decision Authority: `YMY / Project Owner` — approved via interactive session, scope: F003 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `193e90d10b68`
  - `specs/F002-confirmed-unit-blueprint/spec.md` @ `aba5a64f1864`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `a7b4a96443f9`
  - `docs/API.md` @ `1a10877df315`
  - `docs/DATABASE.md` @ `9623b9c222b4`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/adr/0002-stateful-agent-and-async-execution.md` @ `5145b0ff319f`
  - `docs/adr/0003-user-owned-complete-run-traces.md` @ `d0e2fcd0c587`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Lesson-plan document structure | Standard senior-high English lesson-plan structure: 课题与课时, 教学目标 (language knowledge / skills / affect expanded from blueprint objectives), 教学重点与难点, 教学过程 (staged activities with time allocation, expanded from activity outline), 作业布置, 教学反思 (blank for teacher). Output language follows the confirmed brief `output_language_mode` (zh-Hans / en / bilingual). | `YMY / Project Owner`, 2026-08-29 |
| D2 | Checkpoint and recovery granularity | Per-lesson semantic checkpoint: one lesson = model draft → DOCX render → structural validation; a lesson is complete only when all three succeed. Resume skips every completed lesson and continues only failed or incomplete lessons. | `YMY / Project Owner`, 2026-08-29 |
| D3 | Quota and cost-control model | Per-run model-call cap only; no workspace-level concurrent-run limit. Cost is bounded by the per-run cap plus natural constraints: same-version idempotent submission returns the existing run, a newer confirmed version supersedes the older run, and workspace project quota limits how many projects can hold active runs. | `YMY / Project Owner`, 2026-08-29 (owner choice; concurrency-limit alternative declined) |
| D4 | SSE reconnect and event contract | PostgreSQL run-event table is authoritative. SSE events carry a per-run monotonic id; reconnect with `Last-Event-ID` replays missed events from the table; a pollable run-status snapshot remains available; replay never triggers model work. Resolves the `docs/API.md` open item for the SSE resume mechanism. | `YMY / Project Owner`, 2026-08-29 |
| D5 | Failure taxonomy and retry policy | Retryable: provider transient errors and Worker crashes use bounded Celery retry against the same run, resuming from the per-lesson checkpoint. Teacher-blocked: dispatch-time cap exhaustion or missing required inputs produce an explicit state with a recovery action, not silent retry. Terminal: failures that persist after bounded retries (provider hard failure, content-policy rejection, non-recoverable rendering error) end in a terminal state with completed lessons preserved. | Recommended; confirmed with Spec approval |
| D6 | Specialist split | Minimal explicit specialists inside one LangGraph workflow: unit-context assembler (builds per-lesson generation context from confirmed brief, blueprint, and source citations), lesson-plan writer (one structured draft per lesson), document validator (structural check per rendered file). No free-form Agent-to-Agent conversation; orchestration is explicit. | Recommended; confirmed with Spec approval |
| D7 | Artifact validation standard | Structural validation only in F003: file is present, openable by the DOCX parser, contains the required top-level sections, and has non-empty body. Downloads are workspace-authorized. Content-quality evaluation belongs to F008/F009 and is not claimed here. | Recommended; confirmed with Spec approval |
| D8 | Rendering and storage engineering | `python-docx` renders and validates DOCX (pure Python, no external Office dependency) behind an MCP-compatible internal tool definition (ADR-0004 pattern). Binaries go to the existing private object storage under workspace/project scoping; artifact truth (identity, status, object key, checksum) stays in PostgreSQL. New tables: generation run, lesson-plan artifact, and run-event log (names finalized by the Implementation Plan). | Engineering; confirmed with Spec approval |

## Goal

Generate an editable DOCX lesson plan for every lesson in one confirmed unit through an asynchronous, version-bound run that preserves complete traces, idempotent model cost, completed work, and safe recovery.

## Business Value

First substantial teaching deliverable and first proof that the approved Agent architecture executes long-running, full-unit work without turning retries or failures into data loss or duplicated model cost.

## User Story

As a senior-high English teacher, I want all lesson plans generated from my confirmed unit blueprint and recoverable after failure, so that I receive useful editable material without restarting valid work.

## Scope

- Start one asynchronous, idempotent, version-bound generation run from the current confirmed brief and blueprint versions.
- Orchestrate three explicit specialists (D6) for all-lesson plan generation.
- Generate one structured, editable DOCX lesson plan per blueprint lesson (D1 structure).
- Capture complete owner-scoped run traces and per-stage cost/latency evidence.
- Enforce the authoritative per-run model-call cap before each expensive call.
- Acknowledge submission quickly and show phase-level plus per-lesson progress.
- Make duplicate submission and Worker retry reuse the same run and per-lesson checkpoints (D2).
- Preserve completed lesson plans; resume only failed or incomplete lessons.
- Validate delivered files structurally and authorize downloads.
- Stream generation narration alongside phase progress; narration is never a second source of truth.
- Provide authoritative SSE progress with `Last-Event-ID` replay (D4).
- Register document-generation and validation tools with MCP-compatible definitions consumed by the workflow.

## Out of Scope

- PPTX decks, exercises, answers, and the complete alignment report (F004/F005/F008).
- Content-quality evaluation of generated plans (F008/F009).
- User-facing low-level trace exploration beyond this run's progress/evidence (F006).
- Upstream brief/blueprint revision and targeted cross-artifact regeneration (F007).
- Browser-based DOCX editing.
- A workspace-level concurrent-run limit (declined in D3).

## Actors / Preconditions

- Actor: an authenticated teacher owning the workspace and project.
- Preconditions: a confirmed brief version and a confirmed blueprint version exist for the project; the blueprint contains at least one lesson; the workspace project quota is not exhausted; the model adapter and object storage are reachable.

## Main Flow

1. The teacher starts generation from the workspace generation entry.
2. The API atomically creates or returns the idempotent run bound to the current confirmed brief and blueprint versions, acknowledges immediately, and dispatches the Celery task.
3. The Worker executes the LangGraph workflow: assemble per-lesson context → write each lesson plan → render DOCX → validate structure, writing per-lesson checkpoints and run events to PostgreSQL.
4. Phase-level and per-lesson progress, including narration, streams over SSE; the teacher may leave, reconnect with replay, or stop narration without affecting the run.
5. When every lesson has a valid artifact, the run completes; the teacher downloads authorized DOCX plans.

## Alternative Flows

- Duplicate submission (same project, same confirmed versions): returns the existing run; no duplicate model work or artifacts.
- Provider transient failure or Worker crash mid-lesson: bounded Celery retry resumes the same run from the last per-lesson checkpoint; completed lessons remain intact.
- Per-run model-call cap exceeded: run enters an explicit capped-failure state; completed lessons remain downloadable; a teacher-visible recovery path (new run after intent change, or explicit retry of remaining lessons under the same cap policy) is shown.
- Newer confirmed brief/blueprint version during an active run: the run is marked superseded at the next safe checkpoint, stops, and cannot publish over the newer version.
- Narration stream stopped or disconnected: phase progress and artifact production continue unaffected; SSE reconnect replays from the event log.
- Structural validation failure for a lesson: that lesson enters failed state with the validation reason; other lessons continue; the lesson is eligible for bounded retry.
- Teacher resumes an eligible failure: the same run is re-dispatched; only failed or incomplete lessons run.

## Business Rules / Invariants

- A run binds to exactly one immutable confirmed brief version and one blueprint version and never reads a later mutable draft.
- Same-version duplicate generation resolves to one run; PostgreSQL enforces run identity at the database boundary.
- Celery retry resumes the same run; PostgreSQL owns run state, per-lesson checkpoints, and the authoritative event log; Redis is transport only.
- A run is complete only when every blueprint lesson has a structurally valid artifact outcome; partial success stays visible and recoverable.
- No model call proceeds when the run's model-call cap is reached.
- An artifact never becomes ready unless its referenced binary exists and passes structural validation.
- Stale output never overwrites a newer version: supersession marks the old run and blocks publication.
- Complete traces (prompts, outputs, tools, costs, latency, failures) stay inside the owning workspace and are deleted with the project or account.
- Generated lesson-plan content is untrusted output: it cannot change system policy, grant tools, or bypass authorization.

## State Transitions

Run: `queued -> generating -> validating -> complete | partial_failure | capped_failure | superseded | terminal_failure`. `teacher_blocked` is a dispatch-time state when required inputs are missing. Terminal states never transition back; `partial_failure` and `capped_failure` allow resume of eligible lessons; `superseded` is one-way.

Per lesson: `pending -> drafting -> rendering -> validating -> complete | failed`. A failed lesson may re-enter drafting only through an eligible resume within the same run, preserving the per-lesson checkpoint rule (D2). Completed lessons never re-enter work.

## Data Changes

- New generation-run record: project, bound brief/blueprint version ids, status, model-call counter and cap, timestamps; unique constraint enforces idempotent identity per project and bound versions.
- New lesson-plan artifact record: run id, lesson index, per-lesson status, object key, checksum, validation outcome; artifact truth in PostgreSQL, binary in private object storage.
- New run-event record: per-run monotonic sequence, event type, payload, timestamp; authoritative source for SSE replay (D4).
- Trace events extend the existing trace table with generation stages.
- Project/account deletion cascades to runs, artifacts, events, traces, and object-storage binaries.

## API Behavior

- `POST /projects/{id}/generation/start` — idempotent creation bound to current confirmed versions; returns run snapshot; duplicate same-version request returns the existing run.
- `GET /projects/{id}/generation` — authoritative run snapshot: status, per-lesson outcomes, cap usage, bound versions.
- `GET /projects/{id}/generation/events` — SSE; events carry per-run monotonic ids; `Last-Event-ID` replays missed events; replay is read-only.
- `POST /projects/{id}/generation/resume` — re-dispatches the same run for eligible failures only; rejects terminal, superseded, or complete runs.
- `GET /projects/{id}/lesson-plans/{artifactId}/download` — workspace-authorized, streams the stored binary matching the artifact record.
- Error semantics follow the project taxonomy: requirement/input, authentication, authorization/not-found, stale-version, quota (cap), provider/transient, partial-execution, unexpected. No storage paths or prompts leak in errors.
- Stop semantics: stopping narration does not cancel the run (consistent with F001); cancellation of a run is not offered in F003 (supersession and completion are the exits).

## Error Cases

- Missing confirmed versions at start: `teacher_blocked` with explicit recovery (confirm brief/blueprint first).
- Cap exceeded mid-run: `capped_failure` state; completed lessons preserved and downloadable; recovery path shown.
- Provider hard failure after bounded retries: `terminal_failure`; completed lessons preserved; resume not offered for terminal provider failure.
- Object-storage write failure: lesson enters failed state; no artifact becomes ready without a confirmed binary.
- Validation failure: per-lesson failed with structural reason; eligible for bounded retry.
- Unauthorized download or cross-workspace access: authorization-denied class response without confirming existence.

## Idempotency / Concurrency / Transactions

- Run creation is atomic in PostgreSQL across owner check, version binding, idempotent identity, and dispatch handoff; duplicate submissions and Celery redeliveries converge on one run.
- Per-lesson processing is idempotent per lesson index: a retried lesson re-executes only its own draft→render→validate chain; completed lessons are skipped by checkpoint.
- Event-log appends are monotonic per run; replay and polling are read-only.
- Supersession is applied transactionally when a new version is confirmed; an in-flight lesson finishes its current step and the run then stops at the checkpoint without publishing.

## Security / Privacy / Authorization

- Every run, event, artifact, trace, and download is authorized by recorded workspace ownership.
- Generated content and model output are untrusted data; no tool grant, policy change, or cross-workspace leak through content.
- Complete traces remain workspace-scoped and are deleted with the project or account.
- Downloads never expose storage locations; authorization happens in the application boundary.

## Non-functional

- Submission acknowledgement is synchronous and fast; all generation work is asynchronous.
- One hosted model through the existing thin adapter; no provider routing added.
- Default per-run model-call cap is a setting; changing it is configuration, not code.
- Run events are retained for the life of the run (workspace-scoped) to support replay and F006 evidence.
- Worker concurrency uses existing Celery configuration; no new infrastructure product.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace generation entry, per-lesson plan review/download, contextual progress, error recovery, superseded/stale presentation.
- Primary flow: start confirmed-version generation → leave or monitor → inspect completed/failed scope → resume eligible failure → download.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given a confirmed blueprint, when generation completes, then every planned lesson has an owner-authorized, openable, structurally valid editable DOCX lesson plan bound to that brief/blueprint version.
- AC-002: Given the same generation intent submitted twice, when both requests are handled, then they resolve to one run without duplicate model work or artifact publication.
- AC-003: Given a valid start request, when submitted, then the API acknowledges quickly with a queued run snapshot and generation proceeds asynchronously.
- AC-004: Given an active run, when progress is observed, then phase-level and per-lesson status (pending/drafting/rendering/validating/complete/failed) is visible from the authoritative snapshot and events.
- AC-005: Given a transient provider failure after some lessons complete, when the run resumes, then completed lesson plans remain intact and only failed or incomplete lessons continue.
- AC-006: Given a Worker crash mid-run, when execution resumes (retry or teacher resume), then the same run continues from the last per-lesson checkpoint without re-running completed lessons.
- AC-007: Given the per-run model-call cap is reached, when further work is attempted, then no additional model call begins, the run enters an explicit capped state, completed lessons remain downloadable, and a recovery path is shown.
- AC-008: Given a newer confirmed version while a run is active, when the run reaches its next safe checkpoint, then it is marked superseded, stops, and cannot publish over the newer version.
- AC-009: Given an SSE disconnect, when the client reconnects with `Last-Event-ID`, then missed events replay from the authoritative log and no new model work is triggered.
- AC-010: Given active generation, when narration is stopped or fails, then phase progress and artifact production continue unaffected.
- AC-011: Given a partially failed run, when the teacher inspects it, then per-lesson outcomes with reasons and an eligible resume action are visible.
- AC-012: Given a download request, when authorization passes, then the served binary matches the artifact record; when authorization fails, then access is denied without confirming existence.
- AC-013: Given any run outcome, when reviewed, then complete prompts, outputs, tool calls, costs, latency, and failures are recorded in the owning workspace's trace.
- AC-014: Given a rendered lesson plan, when validated, then it is openable, contains the required top-level sections, and has a non-empty body; an invalid file never reaches ready state.
- AC-015: Given project deletion, when deletion completes, then the project's runs, artifacts, events, traces, and stored binaries are deleted.
- AC-016: Given the confirmed brief's output-language mode, when plans are generated, then lesson-plan content follows that language mode (zh-Hans / en / bilingual).

## Open Questions

All DRAFT open questions are resolved by D1–D8 above. Non-blocking residuals:

- [DEFERRED, owner-approved] Exact DOCX typography (fonts, margins, heading styles) is an implementation-level visual choice owned by the UX/UI refinement and Design System rules; it does not change AC-014's structural requirements.
- [DEFERRED, owner-approved] Cap default value is configuration; the exact number is set in the Implementation Plan and recorded in settings.

## Risks and Assumptions

- [CONFIRMED] Correctness and recoverability take priority over fixed complete-unit duration.
- [CONFIRMED] Complete traces are required for every run despite storage and privacy cost (ADR-0003).
- [CONFIRMED] Observed recovery gap (2026-08-28 live testing): a crashed model call can strand a run in an initializing state with no recovery path; F003's run state machine, bounded retry, and teacher resume close this gap for generation runs.
- [ASSUMED] `python-docx` structural validation is sufficient evidence of openability for the portfolio's Phase-1 claims; F009 may add stronger file evidence.
- [ASSUMED] Per-run model-call cap plus idempotency and supersession adequately bounds cost for Phase 1 (D3 owner decision); revisit with F011 guardrails.

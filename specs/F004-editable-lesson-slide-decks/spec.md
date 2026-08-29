# F004: Editable Lesson Slide Decks

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #8](https://github.com/MaoyuanYang/LessonCanvas/issues/8)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F003` (DONE) for the version-bound run, per-lesson inventory, progress, trace, and recovery contract
- Last Updated: 2026-08-29

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-29
- Decision Authority: `YMY / Project Owner` — approved via interactive session (refinement decisions D1/D3/D7/D9 selected interactively; D2/D4/D5/D6/D8 confirmed with Spec approval), scope: F004 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-018, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F004-editable-lesson-slide-decks/spec.md` @ `b913da61ec40`
  - `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `77cac3f8a2c1`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `8472a050533f`
  - `docs/API.md` @ `4754312ca25d`
  - `docs/DATABASE.md` @ `bf60367cb349`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/adr/0002-stateful-agent-and-async-execution.md` @ `5145b0ff319f`
  - `docs/adr/0003-user-owned-complete-run-traces.md` @ `d0e2fcd0c587`
  - `docs/adr/0004-mcp-tool-and-source-protocol.md` @ `7b4a56764d3f`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Deck structure grammar | Fixed skeleton with bounded stage slides: per lesson one title slide (unit + lesson title), one objectives slide, one key-and-difficult-points slide, teaching-stage slides derived from the lesson plan's staged 教学过程 (model plans at most two slides per teaching stage, total deck bounded by a configured maximum), and one homework slide. Teacher guidance and source citations render into speaker notes, never into fake slide footers. Content language follows the confirmed brief `output_language_mode` (zh-Hans / en / bilingual). | `YMY / Project Owner`, 2026-08-29 (interactive selection: fixed skeleton + bounded stage slides) |
| D2 | Checkpoint and recovery granularity | Per-lesson semantic checkpoint inherited from F003 D2: one lesson = model draft → PPTX render → structural validation; a deck is complete only when all three succeed. Resume skips every completed deck and continues only failed or incomplete lessons. | Inherited from F003 D2; confirmed with Spec approval |
| D3 | Eligibility prerequisite and cost model | Deck generation requires a complete lesson-plan run bound to the same confirmed brief and blueprint versions; the deck writer consumes that run's lesson-plan content as its primary context so decks stay aligned to the confirmed teaching sequence. The deck run carries its own per-run model-call cap; no workspace-level concurrent-run limit (F003 D3 policy). | `YMY / Project Owner`, 2026-08-29 (interactive selection: lesson-plan completion as prerequisite) |
| D4 | Progress and event contract | Inherited from F003 D4: the PostgreSQL run-event log is authoritative, SSE events carry per-run monotonic ids, `Last-Event-ID` reconnect replays missed events, a pollable snapshot stays available, and replay never triggers model work. | Inherited from F003 D4; confirmed with Spec approval |
| D5 | Failure taxonomy and retry policy | Inherited from F003 D5 (Retryable / Teacher-blocked / Terminal) applied to deck runs. Teacher-blocked additionally covers a missing or incomplete lesson-plan run for the bound versions. | Inherited from F003 D5; confirmed with Spec approval |
| D6 | Specialist split | Minimal explicit specialists inside one LangGraph workflow: unit-context assembler (extended to assemble the confirmed lesson-plan content per lesson), deck writer (one structured deck draft per lesson), deck validator (structural check per rendered file). No free-form Agent-to-Agent conversation; orchestration is explicit. | Inherited from F003 D6; confirmed with Spec approval |
| D7 | Artifact validation standard | Deterministic structural validation in CI: file present, openable by the PPTX parser, required slides present per the D1 grammar, non-empty text frames, content rendered as editable text frames (a deck whose slides are whole-slide images fails), slide count within configured bounds. One controlled manual PowerPoint/WPS open smoke is recorded as delivery evidence; CI carries no Office dependency. Content-quality evaluation belongs to F008/F009. | `YMY / Project Owner`, 2026-08-29 (interactive selection: deterministic + controlled manual smoke) |
| D8 | Rendering and storage engineering | `python-pptx` renders and validates PPTX (pure Python, no external Office dependency) behind MCP-compatible internal tool definitions (ADR-0004 pattern). Binaries go to the existing private object storage under workspace/project scoping; artifact truth (identity, status, object key, checksum) stays in PostgreSQL. Deck runs reuse the F003 run lifecycle with run identity distinguished per artifact kind; the concrete table strategy is finalized by the Implementation Plan. | Engineering; confirmed with Spec approval |
| D9 | Preview strategy | No in-browser slide preview. The UI presents per-lesson structure summaries (slide count, required sections, validation status) and owner-authorized download; the teacher opens the downloaded PPTX in a local Office application. | `YMY / Project Owner`, 2026-08-29 (interactive selection: download + structure summary) |

## Goal

Generate an editable PPTX slide deck for every lesson in one confirmed unit through the established version-bound, traced, and recoverable run lifecycle, with structural file validation before ready status and owner-authorized download.

## Business Value

Slide decks supply a core classroom deliverable and prove the F003 run-and-recovery contract generalizes to a second artifact type with a materially different rendering and validation boundary, without creating a second workflow authority.

## User Story

As a senior-high English teacher, I want an editable deck aligned to each confirmed lesson plan, so that I can prepare classroom presentation material without rebuilding the lesson sequence.

## Scope

- Start one asynchronous, idempotent, version-bound deck generation run from the current confirmed brief and blueprint versions, gated on a complete lesson-plan run for the same versions (D3).
- Orchestrate the three explicit specialists (D6) for all-lesson deck generation, consuming confirmed lesson-plan content as primary context.
- Generate one structured, editable PPTX deck per blueprint lesson (D1 grammar) with teacher notes and citations in speaker notes.
- Capture complete owner-scoped run traces and per-stage cost/latency evidence.
- Enforce the deck run's own per-run model-call cap before each expensive call.
- Acknowledge submission quickly and show phase-level plus per-lesson progress with structure summaries.
- Make duplicate submission and Worker retry reuse the same run and per-lesson checkpoints (D2).
- Preserve completed decks; resume only failed or incomplete lessons.
- Validate delivered files structurally (D7) and authorize downloads (D9).
- Register deck-rendering and validation tools with MCP-compatible definitions consumed by the workflow.

## Out of Scope

- Browser-based slide editing or third-party Office/Google synchronization.
- Server-side thumbnail or fidelity preview of decks (D9 choice).
- Exercises, answers, alignment review, and teacher-product validation (F005/F008/F010).
- Content-quality evaluation of generated decks (F008/F009).
- Redesigning the run lifecycle established by F003.
- Template customization beyond the restrained D1 grammar.

## Actors / Preconditions

- Actor: an authenticated teacher owning the workspace and project.
- Preconditions: a confirmed brief version and a confirmed blueprint version exist; the blueprint contains at least one lesson; a lesson-plan run bound to those same versions is `complete`; the workspace project quota is not exhausted; the model adapter and object storage are reachable.

## Main Flow

1. The teacher starts deck generation from the workspace deck entry.
2. The API atomically creates or returns the idempotent deck run bound to the current confirmed brief and blueprint versions and the complete lesson-plan run, acknowledges immediately, and dispatches the Celery task.
3. The Worker executes the LangGraph workflow: assemble per-lesson context from the confirmed lesson plan → write each deck draft → render PPTX → validate structure, writing per-lesson checkpoints and run events to PostgreSQL.
4. Phase-level and per-lesson progress, including narration, streams over SSE; the teacher may leave, reconnect with replay, or stop narration without affecting the run.
5. When every lesson has a valid deck, the run completes; the teacher reviews structure summaries and downloads authorized PPTX decks.

## Alternative Flows

- Duplicate submission (same project, same confirmed versions): returns the existing deck run; no duplicate model work or artifacts.
- Missing or incomplete lesson-plan run at start: `teacher_blocked` with explicit recovery (generate and complete lesson plans first).
- Provider transient failure or Worker crash mid-lesson: bounded Celery retry resumes the same run from the last per-lesson checkpoint; completed decks remain intact.
- Per-run model-call cap exceeded: run enters an explicit capped-failure state; completed decks remain downloadable; a teacher-visible recovery path is shown.
- Newer confirmed brief/blueprint version during an active run: the deck run is marked superseded at the next safe checkpoint, stops, and cannot publish over the newer version.
- Narration stream stopped or disconnected: progress and deck production continue unaffected; SSE reconnect replays from the event log.
- Structural validation failure for a lesson (including an image-only or out-of-bounds deck): that lesson enters failed state with the validation reason; other lessons continue; the lesson is eligible for bounded retry.
- Teacher resumes an eligible failure: the same run is re-dispatched; only failed or incomplete lessons run.

## Business Rules / Invariants

- A deck run binds to exactly one immutable confirmed brief version, one blueprint version, and the complete lesson-plan run bound to those versions; it never reads a later mutable draft.
- Every required lesson has at most one current deck outcome per artifact version while history remains immutable.
- Same-version duplicate deck generation resolves to one run; PostgreSQL enforces run identity at the database boundary, distinguished from lesson-plan runs.
- Celery retry resumes the same run; PostgreSQL owns run state, per-lesson checkpoints, and the authoritative event log; Redis is transport only.
- A deck run is complete only when every blueprint lesson has a structurally valid deck outcome; partial success stays visible and recoverable.
- No model call proceeds when the deck run's model-call cap is reached.
- A deck never becomes ready unless its referenced binary exists and passes structural validation.
- Stale output never overwrites a newer version: supersession marks the old run and blocks publication.
- Complete traces (prompts, outputs, tools, costs, latency, failures) stay inside the owning workspace and are deleted with the project or account.
- Generated deck content is untrusted output: it cannot change system policy, grant tools, or bypass authorization.

## State Transitions

Run (deck): `queued -> generating -> validating -> complete | partial_failure | capped_failure | superseded | terminal_failure`. `teacher_blocked` is a dispatch-time state when required inputs are missing (confirmed versions or a complete lesson-plan run). Terminal states never transition back; `partial_failure` and `capped_failure` allow resume of eligible lessons; `superseded` is one-way.

Per lesson (deck): `pending -> drafting -> rendering -> validating -> complete | failed`. A failed lesson may re-enter drafting only through an eligible resume within the same run, preserving the per-lesson checkpoint rule (D2). Completed lessons never re-enter work.

## Data Changes

- New slide-deck artifact record: run id, lesson index, per-lesson status, object key, checksum, validation outcome, slide count; artifact truth in PostgreSQL, binary in private object storage.
- Deck generation runs reuse the F003 run lifecycle with identity distinguished per artifact kind (exact constraint strategy finalized by the Implementation Plan).
- Run-event records extend to deck runs with deck event payloads (including slide count on completion).
- Trace events extend the existing trace table with deck generation stages.
- Project/account deletion cascades to deck runs, deck artifacts, events, traces, and object-storage binaries.

## API Behavior

- `POST /projects/{id}/decks/generation/start` — idempotent creation bound to current confirmed versions plus the complete lesson-plan run; returns run snapshot; duplicate same-version request returns the existing deck run; missing or incomplete lesson-plan run returns the teacher-blocked requirement error naming the prerequisite.
- `GET /projects/{id}/decks/generation` — authoritative run snapshot: status, per-lesson outcomes with structure summaries, cap usage, bound versions.
- `GET /projects/{id}/decks/generation/events` — SSE; events carry per-run monotonic ids; `Last-Event-ID` replays missed events; replay is read-only.
- `POST /projects/{id}/decks/generation/resume` — re-dispatches the same run for eligible failures only; rejects terminal, superseded, or complete runs.
- `GET /projects/{id}/slide-decks/{artifactId}/download` — workspace-authorized, streams the stored binary matching the artifact record.
- Error semantics follow the project taxonomy: requirement/input, authentication, authorization/not-found, stale-version, quota (cap), provider/transient, partial-execution, unexpected. No storage paths or prompts leak in errors.
- Stop semantics: stopping narration does not cancel the run; run cancellation is not offered (supersession and completion are the exits).

## Error Cases

- Missing confirmed versions or missing/incomplete lesson-plan run at start: `teacher_blocked` with explicit recovery (confirm brief/blueprint, then generate and complete lesson plans).
- Cap exceeded mid-run: `capped_failure` state; completed decks preserved and downloadable; recovery path shown.
- Provider hard failure after bounded retries: `terminal_failure`; completed decks preserved; resume not offered for terminal provider failure.
- Object-storage write failure: lesson enters failed state; no deck becomes ready without a confirmed binary.
- Validation failure (missing required slides, empty text, image-only slides, out-of-bounds slide count): per-lesson failed with structural reason; eligible for bounded retry.
- Unauthorized download or cross-workspace access: authorization-denied class response without confirming existence.

## Idempotency / Concurrency / Transactions

- Deck run creation is atomic in PostgreSQL across owner check, prerequisite check, version binding, idempotent identity, and dispatch handoff; duplicate submissions and Celery redeliveries converge on one run.
- Per-lesson processing is idempotent per lesson index: a retried lesson re-executes only its own draft→render→validate chain; completed decks are skipped by checkpoint.
- Event-log appends are monotonic per run; replay and polling are read-only.
- Supersession is applied transactionally when a new version is confirmed; an in-flight lesson finishes its current step and the run then stops at the checkpoint without publishing.

## Security / Privacy / Authorization

- Every deck run, event, artifact, trace, and download is authorized by recorded workspace ownership.
- Generated deck content and model output are untrusted data; no tool grant, policy change, or cross-workspace leak through content.
- Complete traces remain workspace-scoped and are deleted with the project or account.
- Downloads never expose storage locations; authorization happens in the application boundary.

## Non-functional

- Submission acknowledgement is synchronous and fast; all generation work is asynchronous.
- One hosted model through the existing thin adapter; no provider routing added.
- The deck run's per-run model-call cap and the per-deck slide-count bounds are settings; changing them is configuration, not code.
- Deck run events are retained for the life of the run (workspace-scoped) to support replay and F006 evidence.
- Worker concurrency uses existing Celery configuration; no new infrastructure product.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace deck-generation entry, per-lesson deck review with structure summary, download, error recovery, superseded/stale presentation.
- Primary flow: start deck generation (gated on complete lesson plans) → leave or monitor → inspect completed/failed scope → resume eligible failure → download editable PPTX.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given a complete lesson-plan run for the current confirmed unit version, when deck generation completes, then every planned lesson has an owner-authorized, openable, editable PPTX deck bound to that brief/blueprint version and lesson-plan run.
- AC-002: Given the same deck-generation intent submitted twice, when both requests are handled, then they resolve to one run without duplicate model work or artifact publication.
- AC-003: Given a valid start request, when submitted, then the API acknowledges quickly with a queued run snapshot and deck generation proceeds asynchronously.
- AC-004: Given an active deck run, when progress is observed, then phase-level and per-lesson status (pending/drafting/rendering/validating/complete/failed) with structure summary (slide count, validation status) is visible from the authoritative snapshot and events.
- AC-005: Given a transient provider failure after some decks complete, when the run resumes, then completed decks remain intact and only failed or incomplete lessons continue.
- AC-006: Given a Worker crash mid-run, when execution resumes (retry or teacher resume), then the same run continues from the last per-lesson checkpoint without re-running completed decks.
- AC-007: Given the deck run's model-call cap is reached, when further work is attempted, then no additional model call begins, the run enters an explicit capped state, completed decks remain downloadable, and a recovery path is shown.
- AC-008: Given a newer confirmed version while a deck run is active, when the run reaches its next safe checkpoint, then it is marked superseded, stops, and cannot publish over the newer version.
- AC-009: Given an SSE disconnect, when the client reconnects with `Last-Event-ID`, then missed events replay from the authoritative log and no new model work is triggered.
- AC-010: Given active deck generation, when narration is stopped or fails, then progress and deck production continue unaffected.
- AC-011: Given a partially failed deck run, when the teacher inspects it, then per-lesson outcomes with reasons and an eligible resume action are visible.
- AC-012: Given a download request, when authorization passes, then the served binary matches the artifact record; when authorization fails, then access is denied without confirming existence.
- AC-013: Given any deck run outcome, when reviewed, then complete prompts, outputs, tool calls, costs, latency, and failures are recorded in the owning workspace's trace.
- AC-014: Given a rendered deck, when validated, then it is openable by the PPTX parser, contains the required slides per the D1 grammar, presents non-empty editable text frames (not whole-slide images), and stays within configured slide-count bounds; an invalid file never reaches ready state.
- AC-015: Given project deletion, when deletion completes, then the project's deck runs, deck artifacts, events, traces, and stored binaries are deleted.
- AC-016: Given the confirmed brief's output-language mode, when decks are generated, then deck content follows that language mode (zh-Hans / en / bilingual).
- AC-017: Given no lesson-plan run or an incomplete lesson-plan run for the current confirmed versions, when deck generation is started, then the request fails with an explicit teacher-blocked requirement state naming the prerequisite and its recovery action.
- AC-018: Given the deck-generation trace, when reviewed, then the confirmed lesson-plan content for each lesson is recorded as the primary input context of that lesson's deck draft.

## Open Questions

All DRAFT open questions are resolved by D1–D9 above. Non-blocking residuals:

- [DEFERRED, owner-approved] Exact slide typography and layout (fonts, colors, title placement) is an implementation-level visual choice owned by the UX/UI refinement and Design System rules; it does not change AC-014's structural requirements.
- [DEFERRED, owner-approved] The deck-run cap default and per-deck slide-count bounds are configuration; exact numbers are set in the Implementation Plan and recorded in settings.

## Risks and Assumptions

- [CONFIRMED] Editable PPTX is required; PDF-only output does not satisfy the Feature.
- [CONFIRMED] The Web application provides no Office-class slide editing or fidelity preview (D9).
- [CONFIRMED] Correctness and recoverability take priority over fixed complete-unit duration.
- [CONFIRMED] Complete traces are required for every deck run despite storage and privacy cost (ADR-0003).
- [ASSUMED] `python-pptx` structural validation plus one controlled manual Office open smoke is sufficient evidence of openability and editability for Phase-1 claims; F009 may add stronger file evidence.
- [ASSUMED] The complete-lesson-plan prerequisite (D3) does not create a blocking UX bottleneck in Phase 1 because lesson-plan generation precedes deck generation in the natural teacher flow.

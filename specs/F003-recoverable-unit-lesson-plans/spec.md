# F003: Recoverable Unit Lesson Plans

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Generate an editable DOCX lesson plan for every lesson in one confirmed unit while preserving complete traces, progress, idempotent model cost, completed work, and safe recovery.

## Business Value

This is the first substantial teaching deliverable and the first proof that the approved Agent architecture can execute long-running, full-unit work without turning retries or failures into data loss or duplicated model cost.

## User Story

As a senior-high English teacher, I want all lesson plans generated from my confirmed unit blueprint and recoverable after failure, so that I receive useful editable material without restarting valid work.

## Scope

- Start one asynchronous, version-bound run from a confirmed brief and blueprint.
- Orchestrate explicit specialist responsibilities needed for all-lesson plan generation.
- Generate a structured, editable DOCX lesson plan for every lesson in the confirmed blueprint.
- Capture complete owner-scoped run traces and per-stage cost/latency evidence for later disclosure.
- Reserve and enforce authoritative per-user generation quota before expensive work, then reconcile it against the run outcome.
- Acknowledge submission quickly and show named queue, generation, completion, and partial-failure progress.
- Make duplicate submission and Worker retry reuse the same run and semantic checkpoints.
- Preserve completed lesson plans and resume only failed or incomplete scope.
- Validate that delivered files are authorized, present, structurally sound, and openable.

## Out of Scope

- PPTX slide decks, exercises, answers, and the complete alignment report.
- User-facing low-level trace exploration beyond the progress/evidence needed to understand this run.
- Upstream brief/blueprint revision and targeted cross-artifact regeneration.
- Browser-based DOCX editing.

## Main Flow

1. The teacher starts generation from the current confirmed blueprint version.
2. The system returns one idempotent run and asynchronously produces lesson plans with visible phase and lesson scope.
3. Successful lesson plans remain available if another lesson or external dependency fails.
4. The teacher resumes an eligible failure from its safe checkpoint and downloads authorized DOCX plans when ready.

## Core Business Rules

- A run binds to one immutable confirmed brief/blueprint version and never reads a later mutable draft.
- The same-version duplicate generation request returns the existing run rather than creating duplicate model cost or artifacts.
- Celery retry resumes the same run; PostgreSQL owns run state and semantic checkpoints.
- A run is complete only when every required lesson plan has a valid artifact outcome; partial success remains visible and recoverable.
- Redis is transport, never business or checkpoint truth.
- PostgreSQL-backed Identity and Workspace state is authoritative for generation quota; provider or gateway limits are defense in depth.
- Complete traces stay in the owning workspace and are deleted with the project or account.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Confirmed blueprint version | Immutable input and lesson inventory | Discovery and Planning |
| Generation run | Idempotent long-running orchestration attempt | Run Orchestration in PostgreSQL |
| Semantic checkpoint | Recoverable workflow state | Run Orchestration in PostgreSQL through LangGraph |
| Lesson-plan artifact | Version-bound editable teaching file | Artifact Production metadata plus private object storage |
| Run trace | Complete inputs, decisions, tools, outcomes, costs, and failures | Run Orchestration; owned by the teacher workspace |
| Quota reservation | Prevents uncontrolled duplicate or concurrent model work | Identity and Workspace in PostgreSQL |

## Major API / Integration Impact

- FastAPI accepts an idempotent generation command, serves authoritative run/artifact state, authorizes downloads, and streams progress through SSE.
- Celery/Redis delivers Worker execution; LangGraph/PostgreSQL controls semantic state; the selected model and DOCX tooling provide external/tool boundaries.
- Exact task granularity, events, endpoints, checkpoint format, and rendering library wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace generation, lesson-plan artifact review/download, contextual progress and error recovery
- Primary user flow: start confirmed-version generation -> leave or monitor -> inspect completed/failed scope -> resume -> download
- Major UI states: queued, active phase, lesson progress, partial success, transient failure, non-retryable failure, paused/waiting, resumed, complete, stale/superseded, quota/provider failure

## Dependencies

- Feature dependencies: `F002` for a confirmed complete-unit blueprint
- External dependencies: selected model, Redis/Celery environment, PostgreSQL checkpoint support, private object storage, and a DOCX generation/validation boundary

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a confirmed unit blueprint, when generation completes, then every planned lesson has an owner-authorized, openable editable DOCX lesson plan bound to that version.
- [ ] Given the same generation intent is submitted twice, when both requests are handled, then they resolve to one run without duplicate model work or artifact publication.
- [ ] Given a Worker or transient provider failure after some lessons complete, when the run resumes, then completed lesson plans remain intact and only eligible incomplete work continues.
- [ ] Given an old run is superseded by a newer confirmed version, when it reaches a safe checkpoint, then it stops and cannot publish over the newer version.
- [ ] Given insufficient generation quota, when the teacher starts or repeats an expensive run, then no unauthorized model work begins and the limit/recovery state is explicit.

## Risks and Assumptions

- [CONFIRMED] Correctness and recoverability take priority over a fixed complete-unit duration.
- [CONFIRMED] Complete traces are required for every run despite storage and privacy cost.
- [RECOMMENDED] Establish the minimal specialist split that clearly demonstrates explicit orchestration without free-form Agent delegation. Revisit during evaluation if role boundaries are not explainable.
- [UNKNOWN, NON_BLOCKING] Exact lesson-plan content and DOCX rendering expectations are not selected. Resolve with teacher examples and Office validation during refinement.

## Open Questions

- [ ] Which lesson-plan outcomes and document checks are critical for the first representative unit?
- [ ] What is the safe checkpoint and retry boundary for each expensive step?
- [ ] How are quota reservation, release, and model cost reported across partial failure and retry?
- [ ] Which progress granularity informs the teacher without exposing unstable internal implementation?
- [ ] How do SSE reconnect, resume position, and event evolution restore authoritative progress after the browser leaves or loses its network connection?
- [ ] What conditions make a failure retryable, blocked on teacher action, or terminal?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

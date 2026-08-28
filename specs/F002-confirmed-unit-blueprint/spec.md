# F002: Confirmed Unit Blueprint

- Spec Status: `SPEC READY`
- Roadmap Status: `DONE`
- Work item: [GitHub Issue #3](https://github.com/MaoyuanYang/LessonCanvas/issues/3)
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F001` (DONE)
- Last Updated: 2026-08-28

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-28
- Decision Authority: `YMY / Project Owner` — approved via interactive session, scope: F002 Spec at the revision below
- Input manifest (VCS base `8bf078e` plus working-tree SHA-256 prefixes):
  - `specs/F002-confirmed-unit-blueprint/spec.md` @ `108178994342`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `648cb6b43680`
  - `docs/API.md` @ `1a10877df315`
  - `docs/DATABASE.md` @ `9623b9c222b4`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - Dependency Spec: `specs/F001-grounded-confirmed-brief/spec.md` @ `88c8000aa885` (DONE; reused surfaces documented as extensions, no redefinition)
  - ADRs 0001–0005 read; no conflict. UX/UI/DESIGN_SYSTEM/FRONTEND/TESTING read as input; their revisions are listed at their own Gates.
- Checklist: 11/11 `YES` (row 9 = `N/A - Greenfield`, recorded as evidence; F001-implemented surfaces this Feature extends were verified against the current code inventory). All 4 DRAFT open questions `RESOLVED` (D1–D8); remaining items `NON_BLOCKING`.

## Refinement Decision Log

All decisions below were made by `YMY / Project Owner` during `feature-dev` Spec Refinement on 2026-08-28 (interactive session). Scope: F002 only unless noted.

| # | Decision | Resolution | Revisit trigger |
| --- | --- | --- | --- |
| D1 | Blueprint confirmability | Four hard completeness checks gate confirmation: (1) lesson count equals the confirmed brief's lesson/period count, (2) every lesson's required fields are non-empty, (3) every unit objective is covered by at least one lesson, (4) no unresolved blocking finding | Teacher testing shows a check is wrong or missing for downstream generation |
| D2 | Lesson intent granularity | Per lesson: required core fields (title, lesson objectives referencing unit objectives, assessment intent) plus optional fields (period count, activity outline as free-form text, material notes). No activity-level schema and no universal curriculum model; activity detail belongs to F003 lesson plans | F003 refinement shows the blueprint lacks a structurally required field |
| D3 | Conflict tiers | Blocking findings (missing lesson, missing required field, objective coverage gap, lesson count mismatch) require correction before confirmation. Waivable findings (source content conflict, standards alignment warning, period distribution warning) may be resolved by correction or by an explicit recorded teacher decision with a reason; confirmation requires every waivable finding to be fixed or explicitly decided | Alignment evidence in F006/F008 shows a waivable tier is actually correctness-critical |
| D4 | Stale brief handling | A newly confirmed brief version marks dependent blueprint drafts and confirmed blueprint versions visibly stale; a stale confirmed blueprint cannot authorize downstream generation. The UI shows a field-level brief diff plus an impact summary. Per-lesson impact scoping belongs to F007 | F007 refinement needs richer comparison than the summary |
| D5 | Planning interaction model | Interview-style planning: the Agent asks only material planning-gap questions (at most 6 agent-led rounds with at most 3 questions per round, same caps as F001 discovery); with zero gaps the draft is presented directly. Answers become structured state. After the draft, the teacher works through structured correction and findings; chat never silently confirms or mutates the blueprint | Teacher testing shows the interview harms planning quality or cost |
| D6 | Evidence scope | Planning grounds in both the project's ready sources and the curriculum-standards snapshot through the internal MCP-compatible retrieval tool (`search_curriculum_standards`), wired into a workflow for the first time. Unit objectives and lesson items carry citations (source reference or snapshot version) | A trustworthy external official-source MCP server becomes available |
| D7 | Planning cost boundary | No per-run model-call cap for planning runs; cost is bounded by the workspace-level quota enforced before planning starts. Provider-failure retry reuses the same run without duplicate model cost | Cost evidence shows planning runs must be individually bounded |
| D8 | Small-screen boundary | Small screens offer read-only blueprint viewing and status; structured editing, finding decisions, and confirmation are desktop-only with an explicit desktop-required message (consistent with F001 D10) | Teacher evidence shows substantial planning work away from desktop |

## Goal

Turn one confirmed requirements brief into a source-linked, complete-unit blueprint through targeted Agent planning questions, and require the teacher's second explicit confirmation before any artifact generation, so downstream generation follows a coherent plan the teacher approved.

## Business Value

The blueprint makes full-unit generation governable. It lets the teacher correct lesson sequence, objective coverage, and intended assessment before errors multiply across every downstream file, and it establishes the second teacher-authority gate required by the product workflow.

## User Story

As a senior-high English teacher, I want to inspect and confirm how my unit intent is distributed across every lesson, so that all later artifacts follow a coherent plan I approved.

## Scope

- Start an idempotent planning run bound to the current immutable confirmed brief version.
- Ground planning in the project's ready sources and the curriculum-standards snapshot through the internal MCP-compatible retrieval tool, with citations.
- Ask only material planning-gap questions, streamed over SSE with stop control, capped at 6 agent-led rounds with at most 3 questions each.
- Produce a structured blueprint draft covering the complete unit and every lesson, with unit objectives, per-lesson core intent, citations, and planning findings.
- Support structured correction creating new draft revisions with optimistic base revision.
- Support blocking findings that require correction and waivable findings resolvable by an explicit recorded teacher decision with a reason.
- Confirm, when the four completeness checks pass and every finding is resolved or decided, into an immutable blueprint version.
- Mark dependent blueprint drafts and versions visibly stale when a new brief version is confirmed, with a field-level brief diff and impact summary.
- Capture complete planning traces (prompts, responses, citations, tool usage, cost, latency) in the owner-scoped run trace.
- Enforce workspace quota before planning starts.

## Out of Scope

- Lesson-plan, PPTX, exercise, answer, or alignment-report generation (F003+).
- Full run-progress, document-rendering, and recovery behavior introduced by artifact generation.
- Per-lesson impact scoping and targeted regeneration comparison (F007).
- Per-task or per-lesson output-language overrides (task-level language mode stays as confirmed in the brief; F003 refines task-level choice).
- Activity-level structured editing and any universal curriculum model (D2).
- Browser-based free-form document or slide editing.
- External MCP servers (D6 keeps the internal standards tool boundary).

## Actors / Preconditions

| Actor | Role | Permissions |
| --- | --- | --- |
| Teacher | Verified senior-high English teacher authenticated by Clerk | Full owner control of their workspace only |
| Planning Agent | Orchestrated specialist inside the LangGraph planning workflow | Reads owner-authorized sources and the standards snapshot; asks gap questions; proposes blueprint drafts; never confirms intent |
| System / Worker | FastAPI application and Celery worker | Enforces policy, quotas, ownership; executes model calls and run state |

Preconditions: valid Clerk session; a confirmed brief version exists; workspace quota not exhausted; at least the grounding boundary is available (ready sources and/or the standards snapshot).

## Main Flow

1. The teacher opens a project with a confirmed brief and starts unit planning; the system creates (or reuses) one active planning run bound to that confirmed brief version after quota enforcement.
2. The Planning Agent analyzes the confirmed brief fields, ready source evidence, and the standards snapshot, and identifies material planning gaps.
3. With gaps, the Agent streams targeted questions over SSE (at most 6 rounds, at most 3 questions each); the teacher's answers become structured state.
4. The Agent produces a structured blueprint draft revision covering the unit and every lesson, with unit objectives, per-lesson core intent, citations, and findings.
5. The teacher reviews objective distribution, flow, assessment intent, and findings, and makes structured corrections; each save creates a new draft revision.
6. The teacher fixes blocking findings and either fixes or explicitly records a decision with a reason for each waivable finding.
7. When the four completeness checks pass and every finding is resolved or decided, the teacher confirms; the system atomically creates an immutable blueprint version.
8. The confirmed blueprint version is the only authorized input for downstream generation (F003).

## Alternative Flows

- No planning gaps: the draft is presented directly without questions.
- Round cap reached: remaining planning gaps are explicitly marked unresolved in the draft; the teacher may answer further (teacher-initiated answers are not capped) or hand-edit the draft.
- Stop during streaming: display stops; the model call completes; the full response stays in the trace; explicit re-ask starts a new quota-counted call (F001 D7 semantics).
- Provider failure: the named model-provider error preserves run and draft state and offers retry; retry resumes the same run without duplicate model cost.
- Quota exhausted before planning: quota/rate-limit error with recovery guidance; no run is created.
- Confirm with failed checks: requirement/input error naming the failed completeness checks and affected items.
- Confirm with undecided waivable findings: requirement/input error naming the findings awaiting a fix or recorded decision.
- Stale draft correction: a correction against an outdated draft revision returns an explicit version conflict; the teacher reloads and re-applies.
- New brief version confirmed mid-run or after confirmation: the active planning run is superseded and stops at a safe checkpoint; dependent drafts and confirmed blueprint versions are visibly stale with a brief diff and impact summary; history is never mutated.
- Re-plan: the teacher may explicitly start a new planning run after a completed one; the new draft appends as a new revision and never mutates prior revisions or confirmed versions; duplicate start of an active run reuses it.
- No ready sources: planning may still proceed grounded in the standards snapshot; the source-coverage limitation is visible in findings.
- Cross-account access: any non-owner request returns a safe not-found without revealing existence.
- SSE disconnect/reconnect: resumes from authoritative server state; replay never duplicates model work.

## Business Rules / Invariants

- A blueprint always belongs to exactly one immutable confirmed brief version; a planning run records that binding.
- Every lesson required by the confirmed unit scope must be represented before confirmation (lesson count check).
- Required per-lesson fields: title, at least one lesson objective referencing a unit objective, and assessment intent (D2).
- Every unit objective must be covered by at least one lesson before confirmation.
- Model output remains a draft until teacher confirmation; chat cannot silently confirm or modify it.
- Blocking findings (missing lesson, missing required field, objective coverage gap, lesson count mismatch) require correction; waivable findings (source content conflict, standards alignment warning, period distribution warning) additionally accept an explicit recorded teacher decision with a reason.
- Confirmation atomically creates an immutable blueprint version; later correction creates a new draft revision, never mutating a confirmed version.
- A newly confirmed brief version makes dependent blueprint drafts and confirmed versions visibly stale; a stale confirmed blueprint cannot authorize downstream generation; stale state never mutates history.
- The Planning Agent asks only material planning-gap questions; never small talk; at most 6 agent-led rounds with at most 3 questions each.
- One active planning run per project; duplicate starts reuse it; retries resume it.
- Planning cost is bounded by the workspace quota, not a per-run cap (D7).
- The standards snapshot is consumed through the MCP-compatible tool boundary; snapshot content and tool metadata are untrusted input and cannot change policy or bypass gates.
- PostgreSQL is authoritative for ownership, drafts, versions, and run state; Redis is transport only.
- All public identifiers are opaque UUIDv7 values.
- Private content is never stored in browser storage.
- Project/account deletion cascades to planning runs, blueprint drafts, versions, findings, and traces (F001 deletion boundary extended to F002 data).

## State Transitions

Planning run: `initializing -> planning(waiting for teacher when gaps exist) -> drafting -> draft_ready`; `planning/drafting -> provider_failed` (retryable, preserves state); `active -> superseded` when a new brief version is confirmed; one active run per project.

Blueprint draft: `draft (revision n) -> confirmed (version n)`; correction creates `draft (revision n+1)`; a completed re-plan appends a new draft revision; `draft revision n` conflicts with a stale base; `draft -> stale` when a new brief version is confirmed.

Blueprint finding: `open -> resolved_by_correction | decided_by_teacher (with recorded reason)`; blocking findings cannot reach `decided_by_teacher`.

Blueprint version: `confirmed -> stale` (when a newer brief version is confirmed); `stale` is terminal for that version. Invalid: `confirmed -> draft` mutation; `stale -> current` without a new brief-version binding.

## Data Changes

- New persistent concepts (PostgreSQL, UUIDv7 keys, UTC instants): planning run (bound to a confirmed brief version), blueprint draft revisions (structured unit + lessons payload, bound to the confirmed brief version), immutable blueprint versions, planning findings (tier, status, recorded decision reason), all workspace-owned and deleted with the project.
- Reused persistent concepts: interaction messages, trace events, quota counters, audit rows (F001 tables extended by usage, not redefined).
- Citation records reference project sources or the standards-snapshot version.
- No object-storage additions in F002 (blueprint is structured data only).
- No migration of existing data; additive migration only.

## API Behavior

Project-level contract (exact DTOs and event envelopes are defined at the `UI READY` frontend/backend contract step):

- `POST /projects/{id}/planning/start` (idempotent; quota-enforced; binds the current confirmed brief version), `GET /projects/{id}/planning` (status), `GET /projects/{id}/planning/stream` (SSE), `POST /projects/{id}/planning/answers`, `POST /projects/{id}/planning/retry`, `POST /projects/{id}/planning/reask`, `POST /projects/{id}/planning/stop-narration`.
- `GET /projects/{id}/blueprint` (current draft or version, completeness-check status, findings, stale state with brief diff and impact summary when stale), `PATCH /projects/{id}/blueprint/draft` (structured correction with base revision), `POST /projects/{id}/blueprint/decisions` (record a waivable-finding decision with reason), `POST /projects/{id}/blueprint/confirm` (carries the expected base revision; creates or selects the immutable version).
- No artifact-generation endpoint is introduced; blueprint confirmation is the only authority boundary exposed.
- Errors follow the `docs/API.md` taxonomy. Every user-visible failure carries a correlation/run reference. SSE events follow F001 semantics: owner-authorized run context, no new model work from token events, reconnect resumes from authoritative state.

## Error Cases

| Case | Behavior |
| --- | --- |
| Unauthenticated request | Authentication error; redirect to sign-in |
| Non-owner access | Safe not-found; no existence disclosure |
| Planning start without a confirmed brief | Requirement/input error directing to the brief gate |
| Quota exhausted | Quota/rate-limit error with wait or cleanup guidance; no run created |
| Model provider timeout/failure | Named provider/transient error; bounded retry; run and draft state preserved |
| Confirm with failed completeness checks | Requirement/input error naming the failed checks and affected lessons/objectives |
| Confirm with undecided waivable findings | Requirement/input error naming the findings awaiting decision |
| Stale draft correction or confirmation | Version conflict; reload and re-apply |
| Confirming a stale blueprint for downstream authorization | Not authorized; explicit missing/invalid confirmation state |
| Untrusted source/standards content attempts policy change | Rejected by the injection boundary; never grants tools or bypasses gates |
| SSE disconnect | Reconnect resumes; no duplicate model work |

## Idempotency / Concurrency / Transactions

- Planning start is idempotent per project (returns the active run; a superseded or completed run does not block a new explicit start).
- Answer submission is idempotent under duplicate delivery (message-level identity, F001 pattern).
- Blueprint confirmation is atomic under a race: the request carries the expected base draft revision; mismatch returns a conflict; duplicate confirmation of the same revision returns the existing version.
- Supersession by a new brief version is atomic: run superseded, dependent drafts and versions marked stale in one transaction; stale output can never overwrite or authorize over the newer brief version.
- Owner checks, quota reservation, and run identity are enforced at the database boundary, not only in Worker or UI.

## Security / Privacy / Authorization

- Clerk session/JWT validated at the FastAPI boundary (F001 boundary extended unchanged).
- Object-level authorization on every planning run, blueprint draft, version, finding, and trace access; cross-owner requests indistinguishable from missing resources.
- Injection boundary: source text, model output, and MCP snapshot/tool metadata cannot alter system policy, grant tools, or bypass confirmation gates.
- Complete planning traces persist only inside the owning workspace; no cross-user reuse, no training use; deleted with the project or account.
- Audit rows record blueprint confirmation, recorded finding decisions, and supersession without retaining teacher content beyond the documented boundary.
- No private source text, traces, or generated content in browser storage.

## Non-functional

- Streaming: SSE token streams with throttled semantic batching; stop control always visible (F001 semantics).
- Model budget: bounded by the workspace quota with provider timeout and bounded transient retry; no per-run cap (D7).
- Observability: each planning run records prompts, responses, citations, tool usage, latency, and cost inside the owner-scoped trace.
- Performance direction: interactive requests stay responsive; model calls run behind the established run/narration machinery; no long synchronous model calls on the request path except the SSE stream itself.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace blueprint panel (fourth contextual area after the brief), evidence references inside it
- Primary user flow: open confirmed brief -> start planning -> answer planning gaps -> inspect/edit blueprint -> resolve findings -> confirm
- Major UI states: loading, empty (no confirmed brief), generating/waiting for answer, streaming, draft, incomplete (failed checks), blocking finding, waivable finding pending decision, stale (with diff and impact summary), confirmed, permission denied, provider failure, quota, desktop-required (small screen)
- Small-screen boundary (D8): read-only viewing and status only.
- UX/UI refinement, state matrix, contract, and error mapping are completed at the `UI READY` step.

## Acceptance Criteria

- AC-001: Given a project with a confirmed brief, when planning starts, then an active planning run is created idempotently, bound to that confirmed brief version, after quota enforcement; duplicate starts reuse it; without a confirmed brief the start is rejected with explicit guidance.
- AC-002: Given material planning gaps, when the Agent plans, then it asks only those gaps, at most 6 agent-led rounds with at most 3 questions each; with zero gaps the draft is presented directly.
- AC-003: Given the round cap is reached with unresolved planning gaps, when the draft is presented, then each unresolved gap is explicitly marked and the teacher can answer further or hand-edit.
- AC-004: Given a produced draft, when the teacher reviews it, then the complete unit and every lesson appear with required per-lesson fields, and unit objectives and lesson items carry source citations or standards-snapshot version citations.
- AC-005: Given a draft correction, when it is saved, then a new draft revision is created; a stale base revision returns an explicit version conflict.
- AC-006: Given blocking findings (missing lesson, missing required field, objective coverage gap, lesson count mismatch), when confirmation is requested, then it is rejected naming each failed completeness check and affected items.
- AC-007: Given waivable findings (source content conflict, standards alignment warning, period distribution warning), when the teacher decides, then the decision and reason are recorded structurally, or the finding is fixed by correction; confirmation requires every finding resolved or decided.
- AC-008: Given the four completeness checks pass and every finding is resolved or decided, when the teacher confirms, then an immutable blueprint version is created atomically; duplicate confirmation is idempotent; confirmed versions are never mutated.
- AC-009: Given a newly confirmed brief version, when it is created, then dependent planning runs are superseded and dependent blueprint drafts and versions become visibly stale with a field-level brief diff and impact summary, and a stale confirmed blueprint cannot authorize downstream generation.
- AC-010: Given the standards snapshot, when planning uses it, then citations record the snapshot version through the MCP-compatible tool, and snapshot content cannot change policy or bypass confirmation.
- AC-011: Given another authenticated teacher, when they attempt to access the planning run, blueprint draft, version, findings, or trace, then the system reveals no private content or resource existence.
- AC-012: Given a model provider failure during planning, when it occurs, then a named provider error is shown, run and draft state are preserved, and retry resumes the same run without duplicate cost for completed work.
- AC-013: Given a streamed planning response, when the teacher stops it, then only the display stops, the complete response remains in the owner-scoped trace, and an explicit re-ask starts a new quota-counted response; SSE reconnect resumes authoritative state without duplicating work.
- AC-014: Given a small-screen session, when the teacher works, then blueprint viewing and status function read-only, while structured editing, finding decisions, and confirmation present an explicit desktop-required message.
- AC-015: Given a planning run, when it executes, then prompts, responses, citations, tool usage, cost, and latency are captured in the owner-scoped trace and deletable with the project.
- AC-016: Given an unconfirmed or stale blueprint, when downstream generation is requested through any future path, then generation is not authorized and the missing or invalid confirmation is explicit.

## Open Questions

All refinement questions are `RESOLVED` via the Refinement Decision Log (D1–D8).

Remaining `NON_BLOCKING` items:

- [UNKNOWN, NON_BLOCKING] The representative unit's lesson organization is not selected. Resolve with the participating teacher during implementation or teacher validation; does not change Spec behavior.
- [UNKNOWN, NON_BLOCKING] Exact workspace quota numbers for planning. Resolve during implementation planning with cost evidence; does not change Spec behavior.

## Risks and Assumptions

- [CONFIRMED] Full-unit, every-lesson scope is retained despite higher planning and evaluation cost.
- [CONFIRMED] The blueprint is a second teacher authority gate, not an Agent-owned final plan.
- [CONFIRMED] Interview-style planning reuses the F001 interaction, streaming, and stop semantics; deviation risk is limited to planning-question quality.
- [CONFIRMED] The internal standards MCP tool is wired into a real workflow for the first time (D6); its retrieval quality is an implementation risk mitigated by findings and teacher correction.
- No per-run planning cap (D7) means a single planning run is bounded only by the workspace quota and provider timeouts; cost exposure is accepted by the Project Owner and revisited on cost evidence.
- Blueprint structured payload shape may need tuning during teacher validation; the Spec fixes required fields and checks, not the full JSON schema.

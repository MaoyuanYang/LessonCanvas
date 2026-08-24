# F001: Grounded Confirmed Brief

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Work item: [GitHub Issue #1](https://github.com/MaoyuanYang/LessonCanvas/issues/1)
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Decision Authority: `YMY / Project Owner`
- Dependencies: None
- Last Updated: 2026-08-24

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-24
- Decision Authority: `YMY / Project Owner` — approved via interactive session, scope: F001 Spec at the revision below
- Input manifest (VCS base `de9306d` plus working-tree SHA-256 prefixes):
  - `specs/F001-grounded-confirmed-brief/spec.md` @ `d7ae5094c490`
  - `AGENTS.md` @ `2ee6dba879b1`
  - `specs/ROADMAP.md` @ `44047060e23b`
  - `docs/API.md` @ `1a10877df315`
  - `docs/DATABASE.md` @ `9623b9c222b4`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - Dependency Specs: none (F001 has no Feature dependencies)
  - ADRs 0001–0005 read; no conflict. UX/UI/DESIGN_SYSTEM/FRONTEND/TESTING read as input; their revisions are listed at their own Gates.
- Checklist: 11/11 `YES` (row 9 = `N/A - Greenfield`, recorded as evidence). All 8 refinement questions `RESOLVED` (D1–D11); remaining items `NON_BLOCKING`.

## Refinement Decision Log

All decisions below were made by `YMY / Project Owner` during `feature-dev` Spec Refinement on 2026-08-24 (interactive session). Scope: F001 only unless noted.

| # | Decision | Resolution | Revisit trigger |
| --- | --- | --- | --- |
| D1 | Managed identity provider | Clerk. FastAPI validates Clerk sessions at the boundary; the application owns workspace authorization | Access, cost, or deletion-API evidence fails during implementation |
| D2 | Hosted model | DeepSeek, one model behind a thin provider adapter (OpenAI-compatible API surface) | Quality/cost/availability evidence from discovery interviews |
| D3 | Object storage | Local MinIO only in Phase 1 development, accessed through the S3-compatible adapter | A managed S3-compatible store MUST be selected before public multi-account deployment (F011/F012) |
| D4 | Initial source formats | PDF, DOCX, TXT, MD. Max 10 files per project, max 20 MB per file. Text extraction only; no OCR | Teacher evidence shows another format is necessary for a representative unit |
| D5 | Official sources and MCP form | Curated snapshot of the senior-high English curriculum standards (《普通高中英语课程标准(2017年版2020年修订)》) exposed through an internal MCP-compatible retrieval tool. No external MCP server in F001 | A trustworthy external official-source MCP server becomes available |
| D6 | Opaque ID strategy | UUIDv7 primary keys; opaque string form in APIs; no embedded identity or business meaning | N/A (project convention decision, DATABASE.md) |
| D7 | Streaming stop semantics | Stop interrupts client-side token display only; the underlying model call completes and the full response is captured in the owner-scoped trace. An explicit teacher "re-ask" starts a new quota-counted model call. Aligns with the CONFIRMED rules in `docs/API.md` | Cost evidence shows completion-after-stop is unacceptable |
| D8 | Brief confirmability | Seven required fields (see Business Rules). Confirmation is enabled only when all seven are non-empty. Evidence-based fields show source citations or an explicit teacher-stated marker | Refinement shows a required field is not actually required for downstream planning |
| D9 | Question stopping rule | The Agent asks only material required-field gaps; at most 6 agent-led rounds with at most 3 questions per round. After the cap, remaining gaps are explicitly marked unresolved in the draft; the teacher may keep answering or hand-fill. Zero gaps means the draft is presented without questions | Teacher testing shows the cap harms brief quality |
| D10 | Small-screen boundary | Reduced canonical experience: sign-in, project list/status viewing, and conversational answering are available; structured brief editing, confirmation, source upload, and deletion are desktop-only with an explicit message | Teacher evidence shows substantial preparation away from desktop |
| D11 | Deletion and operational evidence | Project deletion is a synchronous cascade across PostgreSQL, vectors, and MinIO with an audit row; failures are visible and retryable. Account deletion purges workspace data, then calls the Clerk user-deletion API. Phase-1 operational access is developer access to local infrastructure, evidenced by audit rows for sensitive actions | Public deployment (F011/F012) requires hosted-store deletion guarantees and operator tooling |

## Goal

Let a verified senior-high English teacher establish a private, source-grounded unit-preparation project and explicitly confirm a structured teaching-requirements brief produced through targeted Agent questions, so downstream planning uses intent the teacher explicitly confirmed.

## Business Value

This is the first end-to-end Agent outcome. It proves that private source ownership, grounding, structured state, dynamic questioning, and teacher authority can work together before any expensive unit planning or artifact generation.

## User Story

As an individual senior-high English teacher, I want the Agent to identify gaps in my goals and materials and turn my answers into a reviewable brief, so that downstream planning uses intent I explicitly confirmed.

## Scope

- Authenticate through Clerk and map the authenticated subject to an owner-only workspace.
- Create, list, resume, and delete a private unit-preparation project.
- Upload allowed private sources (PDF, DOCX, TXT, MD; max 10 files; max 20 MB each; text extraction only), with format/size policy and student-data rejection plus actionable feedback.
- Consume the controlled curriculum-standards snapshot through an internal MCP-compatible retrieval tool and cite it as grounding evidence.
- Run one discovery interaction per project: source-grounded questions for required-field gaps only, streamed token by token over SSE with stop control.
- Present the inferred teaching intent as a structured draft with seven required fields, field-level grounding citations, and explicit unresolved-gap markers.
- Allow structured correction creating new draft revisions, and explicit confirmation creating an immutable brief version.
- Show draft/confirmed/waiting/error states with teacher-readable source support.
- Capture complete discovery traces (prompts, responses, citations, cost, latency) in the owner-scoped run trace.
- Provide project deletion (synchronous cascade) and an account deletion entry (workspace purge plus Clerk user deletion).
- Enforce initial quotas before expensive model work.

## Out of Scope

- Unit-blueprint creation or the second confirmation gate (F002).
- Lesson plans, slides, exercises, answers, or alignment reports (F003+).
- Open Web search, complete copyrighted textbook ingestion, cross-user source reuse, OCR/image sources.
- External MCP servers (no trustworthy official-source server exists yet; see D5).
- School organizations, collaboration, custom password authentication, custom operations console.
- Managed/hosted object storage (local MinIO only; revisit per D3).
- Structured brief editing, confirmation, upload, or deletion on small screens (D10).
- Final public-demo hardening across the complete application (F011/F012).

## Actors / Preconditions

| Actor | Role | Permissions |
| --- | --- | --- |
| Teacher | Verified senior-high English teacher authenticated by Clerk | Full owner control of their workspace only |
| Discovery Agent | Orchestrated specialist inside the LangGraph discovery workflow | Reads owner-authorized sources; proposes questions and draft fields; never confirms intent |
| System / Worker | FastAPI application and Celery worker | Enforces policy, quotas, ownership; executes parsing and model calls |

Preconditions: valid Clerk session; workspace quota not exhausted; source policy satisfied before grounding.

## Main Flow

1. The teacher signs in through Clerk; the backend maps the Clerk subject to (or creates) the private workspace.
2. The teacher creates a preparation project (project name plus optional unit hints) and uploads allowed sources.
3. Each source passes format/size/student-data policy, is parsed and made ready for retrieval, or is rejected/failed with specific feedback.
4. The teacher starts discovery. The Agent inspects ready sources and the standards snapshot, identifies required-field gaps, and streams targeted questions (zh-Hans UI copy).
5. The teacher answers; the Agent continues until gaps resolve or the 6-round cap is reached, then produces a structured brief draft with citations and explicit unresolved gaps.
6. The teacher edits the draft through structured correction; each save creates a new draft revision.
7. When all seven required fields are non-empty, the teacher confirms; the system atomically creates immutable brief version 1.
8. The confirmed brief with its evidence is exposed as the authorized input for unit planning (F002).

## Alternative Flows

- No gaps: the draft is presented immediately without questions.
- Round cap reached: remaining gaps are marked unresolved; the teacher may answer more (teacher-initiated answers are not capped) or hand-fill fields.
- Stop during streaming: display stops; the model call completes; the full response stays in the trace; the teacher may continue or explicitly re-ask (new quota-counted call).
- Rejected source: format/size/student-data rejection returns a specific safe recovery path; rejected content never enters grounding.
- Failed parsing: the source is marked failed and excluded from grounding with an explanation; other sources remain usable.
- Provider failure: the named model-provider error preserves draft/run state and offers retry; no silent fallback model.
- Stale edit: a correction against an outdated draft revision returns an explicit version conflict; the teacher reloads and re-applies.
- Cross-account access: any non-owner request returns a safe not-found without revealing existence.
- Duplicate discovery start: returns the existing active discovery run (idempotent).
- SSE disconnect/reconnect: resumes from authoritative server state; replay never duplicates model work.
- Project/account deletion: synchronous cascade; partial failure leaves a visible failed-deletion state with retry.

## Business Rules / Invariants

- Only the workspace owner may view, change, confirm, or delete the project, sources, interactions, and briefs.
- Chat history, uploaded files, and model output are evidence or drafts; only the explicitly confirmed structured brief is authoritative teaching intent.
- Source content, model responses, and MCP tool/snapshot metadata are untrusted input; they cannot grant tools, change policy, disclose other workspaces, or bypass confirmation.
- Identifiable student data, real student submissions, and grade records are rejected before entering grounding or generation.
- The Agent asks only material required-field gaps; never small talk; at most 6 agent-led rounds × ≤3 questions per round (D9).
- Seven required brief fields (D8): unit theme; lesson/period count; student context; teaching objectives and requirements; material/textbook positioning; output language mode (Chinese/English/bilingual, task-level); assessment orientation.
- Confirmation requires all seven fields non-empty and atomically creates an immutable version; later correction creates a new draft, never mutating a confirmed version.
- Stop interrupts narration only; the complete response persists in the trace; re-ask is explicit and quota-counted (D7).
- One active discovery run per project; duplicate starts reuse it.
- PostgreSQL is authoritative for ownership, drafts, versions, and run state; Redis is transport only.
- All public identifiers are opaque UUIDv7 values.
- Private content is never stored in browser storage.
- Deletion cascades to sources, drafts, versions, traces, vectors, and objects; audit rows record deletion without retaining content.

## State Transitions

Source: `uploading -> processing -> ready`; `uploading/processing -> rejected | failed`. Ready sources can be deleted; rejected/failed sources can be replaced or removed.

Discovery run: `initializing -> questioning(waiting for teacher) -> drafting -> draft_ready`; `questioning/drafting -> provider_failed` (retryable, preserves state); one active run per project.

Brief: `draft (revision n) -> confirmed (version n)`; correction of a confirmed brief creates `draft (revision 1)` of the next cycle; `draft revision n` conflicts with stale base.

Project: `active -> deleting -> deleted`; deletion failure keeps `deleting(failed)` with retry. Invalid: `deleted -> active`; `confirmed -> draft` mutation.

## Data Changes

- New persistent concepts (PostgreSQL, UUIDv7 keys, UTC instants): workspace, preparation project, source record, discovery run, interaction messages, brief draft revision, confirmed brief version, citation records, quota counters, audit rows.
- Object storage (MinIO): original uploaded files and extracted text artifacts, owner-scoped keys.
- Vectors (pgvector): source chunk embeddings scoped to the project; deleted with the project.
- Standards snapshot: versioned read-only corpus bundled with the application; citation records store snapshot version.
- Deletion removes all project-scoped rows, objects, and vectors; audit rows retain only non-content deletion evidence.
- No migration of existing data (Greenfield).

## API Behavior

Project-level contract (exact DTOs and event envelopes are defined at the `UI READY` frontend/backend contract step):

- `POST /projects`, `GET /projects`, `GET /projects/{id}`, `DELETE /projects/{id}` — owner-authorized CRUD; list returns status/phase/last activity.
- `POST /projects/{id}/sources` (multipart), `GET /projects/{id}/sources`, `DELETE /projects/{id}/sources/{sourceId}` — upload policy results are explicit (`ready`, `rejected(reason)`, `failed(reason)`).
- `POST /projects/{id}/discovery/start` (idempotent), `GET /projects/{id}/discovery/stream` (SSE), `POST /projects/{id}/discovery/answers`, `POST /projects/{id}/discovery/stop-narration`, `POST /projects/{id}/discovery/reask`.
- `GET /projects/{id}/brief`, `PATCH /projects/{id}/brief/draft` (structured correction with base revision), `POST /projects/{id}/brief/confirm`.
- `DELETE /account` — workspace purge then Clerk user deletion.
- Errors follow the `docs/API.md` taxonomy: requirement/input, authentication, authorization/ownership/not-found, stale-version/conflict, source/file-policy, quota/rate-limit, provider/transient, partial-execution/recovery, unexpected-system. Every user-visible failure carries a correlation/run reference.
- SSE events carry owner-authorized run context; incremental token events never create new model work; reconnect resumes from authoritative state.

## Error Cases

| Case | Behavior |
| --- | --- |
| Unauthenticated request | Authentication error; redirect to sign-in |
| Non-owner access | Safe not-found; no existence disclosure |
| Disallowed format / oversize file | Source/file-policy rejection with specific recovery guidance |
| Student-data detected | Rejection before grounding with safe explanation; never partial acceptance |
| Model provider timeout/failure | Named provider/transient error; bounded retry for transient faults; state preserved |
| Stale draft correction | Version conflict; reload and re-apply |
| Confirm with missing required fields | Requirement/input error naming missing fields |
| Quota exhausted | Quota/rate-limit error with wait or cleanup guidance |
| Deletion partial failure | Visible failed-deletion state; retry re-enters cascade idempotently |
| SSE disconnect | Reconnect resumes; no duplicate model work |

## Idempotency / Concurrency / Transactions

- Discovery start is idempotent per project (returns the active run).
- Answer submission is idempotent under duplicate delivery (message-level identity).
- Confirmation atomically creates or selects the immutable version under a race; the request carries the expected base revision; mismatch returns a conflict.
- Owner checks, quota reservation, and run identity are enforced at the database boundary, not only in Worker or UI.
- Duplicate narration stop requests are safe no-ops after the first.
- Deletion re-entry is safe: already-deleted items are skipped; failures remain visible.

## Security / Privacy / Authorization

- Clerk session/JWT validated at the FastAPI boundary; identity never accepted from client business payloads.
- Object-level authorization on every project, source, run, brief, and trace access; cross-owner requests indistinguishable from missing resources.
- Upload boundaries: format allowlist, size limits, file-content validation; rejected content is not retained for grounding.
- Student-data rejection runs before parsing results enter retrieval; detection combines deterministic checks and model-assisted classification, both treating content as untrusted.
- Injection boundary: source text, model output, and MCP snapshot/tool metadata cannot alter system policy, grant tools, or bypass confirmation gates.
- DeepSeek API key is server-side configuration only; never exposed to the browser or logged with content.
- Complete discovery traces persist only inside the owning workspace; no cross-user reuse, no training use; deleted with the project or account.
- Audit rows record confirmation, deletion, and sensitive access decisions without retaining teacher content.
- No private source text, traces, generated content, or identity tokens in browser storage.

## Non-functional

- Streaming: SSE token streams with throttled semantic batching for assistive technology; stop control always visible during streaming.
- Model budget: bounded by the 6-round cap, per-run model-call quota, and provider timeout with bounded transient retry.
- Observability: each discovery run records prompts, responses, citations, tool usage, latency, and cost inside the owner-scoped trace.
- Performance direction: source parsing and embedding run asynchronously (Celery); interactive requests stay responsive; no long synchronous model calls on the request path except the SSE stream itself.
- Toolchain: this is the first persistence-owning Feature; repository scaffolding (Next.js, FastAPI modular monolith, Celery worker, migrations, test harness) is implementation work inside this Feature per `specs/ROADMAP.md` sequencing notes.

## UI Impact

- UI involved: `YES`
- Affected screens: public entry/sign-in, project list, new preparation flow, unit workspace (sources, discovery, brief), account/deletion entry.
- Primary user flow: sign in -> create private project -> add sources -> answer gaps -> review/edit brief -> confirm.
- Major UI states: loading, empty project, source processing, waiting for answer, streaming, rejected/failed source, draft, stale edit conflict, confirmed, permission denied, provider failure, quota, deletion active/failed/success.
- Small-screen boundary (D10): read-only status and conversational answering; structured editing, confirmation, upload, and deletion are desktop-only with an explicit message.
- UX/UI refinement, state matrix, contract, and error mapping are completed at the `UI READY` step.

## Acceptance Criteria

- AC-001: Given a teacher with a valid Clerk session, when they enter the app, then a private owner-scoped workspace is available and the backend rejects unauthenticated or forged identity claims.
- AC-002: Given an authenticated teacher, when they create, list, resume, or delete their projects, then every operation succeeds owner-scoped with status visible.
- AC-003: Given another authenticated teacher, when they attempt to access the project, source, interaction, or brief, then the system reveals no private content or resource existence.
- AC-004: Given a source upload, when the file violates format, size, or count policy, then it is rejected with a specific safe recovery path and never enters grounding.
- AC-005: Given identifiable student data or a policy-violating source, when it is submitted, then it is rejected before grounding with a specific safe recovery path.
- AC-006: Given an accepted source, when parsing completes or fails, then the ready/failed state is visible and failed sources are excluded from grounding with explanation.
- AC-007: Given ready sources, when discovery starts, then the Agent asks only required-field gap questions, at most 6 agent-led rounds with at most 3 questions each, and presents the draft directly when no gaps exist.
- AC-008: Given the round cap is reached with unresolved gaps, when the draft is presented, then each unresolved required field is explicitly marked and the teacher can answer further or hand-fill.
- AC-009: Given a streamed interview response, when the teacher stops it, then only the display stops, the complete response remains in the owner-scoped trace, and an explicit re-ask starts a new quota-counted response.
- AC-010: Given a produced draft, when the teacher reviews it, then all seven required fields appear with field-level source citations or explicit teacher-stated markers.
- AC-011: Given a draft correction, when it is saved, then a new draft revision is created; a stale base revision returns an explicit version conflict.
- AC-012: Given all seven required fields are non-empty, when the teacher confirms, then an immutable brief version is created atomically; confirmed versions are never mutated; later corrections create new drafts.
- AC-013: Given a confirmed brief, when unit planning later starts, then the confirmed version with its evidence is the only authorized intent input.
- AC-014: Given the curriculum-standards snapshot, when grounding uses it, then citations record the snapshot version through the MCP-compatible tool, and snapshot content cannot change policy or bypass confirmation.
- AC-015: Given a project deletion request, when it executes, then PostgreSQL rows, vectors, and MinIO objects are cascade-deleted synchronously with an audit row; partial failure stays visible and retryable.
- AC-016: Given an account deletion request, when it executes, then workspace data is purged before the Clerk user-deletion call, and any failure state is visible with recovery.
- AC-017: Given a model provider failure, when it occurs during discovery, then a named provider error is shown, draft/run state is preserved, and retry resumes without duplicate cost for completed work.
- AC-018: Given an SSE disconnect, when the client reconnects, then streaming resumes from authoritative state without duplicating model work or mutating confirmed state.
- AC-019: Given a small-screen session, when the teacher works, then read-only status and conversational answering function, while structured editing, confirmation, upload, and deletion present an explicit desktop-required message.

## Open Questions

All refinement questions are `RESOLVED` via the Refinement Decision Log (D1–D11).

Remaining `NON_BLOCKING` items:

- [UNKNOWN, NON_BLOCKING] Managed object-storage provider for public deployment. Resolve before F011/F012; local MinIO until then (D3).
- [UNKNOWN, NON_BLOCKING] Exact DeepSeek model tier (e.g. deepseek-chat vs reasoning variant) and quota numbers. Resolve during implementation planning with cost evidence; does not change Spec behavior.
- [UNKNOWN, NON_BLOCKING] Participating teacher validation of the project-centered flow. Resolve before `UI READY` per `docs/UX.md`.

## Risks and Assumptions

- [CONFIRMED] One target teacher has validated the cross-artifact alignment problem and can participate in refinement.
- [CONFIRMED] The first Feature must not store private source text or generated content in browser storage.
- [CONFIRMED] Provider set for F001: Clerk, DeepSeek, local MinIO (D1–D3).
- Student-data rejection is heuristic plus model-assisted; residual false negatives are mitigated by the teacher review loop and are documented as residual risk in Test Design.
- DeepSeek availability/cost during refinement interviews is unverified; a provider-transient failure path is required (AC-017).
- Standards-snapshot currency: the bundled snapshot is a fixed version; updates are a maintenance decision outside F001.

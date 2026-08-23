# F001: Grounded Confirmed Brief

- Spec Status: `DRAFT`
- Roadmap Status: `NEXT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-23

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Let a verified senior-high English teacher establish a private, source-grounded unit-preparation project and explicitly confirm a structured teaching-requirements brief produced through targeted Agent questions.

## Business Value

This is the first end-to-end Agent outcome. It proves that private source ownership, grounding, structured state, dynamic questioning, and teacher authority can work together before any expensive unit planning or artifact generation.

## User Story

As an individual senior-high English teacher, I want the Agent to identify gaps in my goals and materials and turn my answers into a reviewable brief, so that downstream planning uses intent I explicitly confirmed.

## Scope

- Authenticate through a managed identity boundary and enter an owner-only preparation workspace.
- Create, find, resume, and delete a private unit-preparation project.
- Add an initially supported set of legally usable teacher sources and controlled official evidence.
- Reject identifiable student information and provide actionable source/readiness feedback.
- Ask source-grounded questions only for material requirement gaps and preserve conversation context.
- Present the inferred teaching intent as a structured draft, including task-level Chinese, English, or bilingual output choice.
- Allow structured correction and explicit confirmation into an immutable brief version.
- Show teacher-readable source support and the current draft/confirmed/waiting/error state.
- Stream interview and explanation responses token by token over SSE, with stop control and complete responses captured in the full trace.
- Consume controlled official sources through MCP servers and register source/retrieval tooling with MCP-compatible definitions.

## Out of Scope

- Unit-blueprint creation or the second confirmation gate.
- Lesson plans, slides, exercises, answers, or alignment reports.
- Open Web search, complete copyrighted textbook ingestion, or cross-user source reuse.
- School organizations, collaboration, custom password authentication, or a custom operations console.
- Final public-demo hardening across the complete application.

## Main Flow

1. A verified teacher creates a private preparation project and supplies allowed unit context and source material.
2. The system validates ownership and source policy, prepares evidence, and asks targeted questions for unresolved teaching requirements.
3. The teacher reviews and edits a structured brief and explicitly confirms an immutable version.
4. The project exposes the confirmed brief and evidence as the authorized input for unit planning.

## Core Business Rules

- Only the workspace owner may view, change, confirm, or delete the project and its sources.
- Chat history, uploaded files, and model output are evidence or drafts; only the explicitly confirmed structured brief is authoritative teaching intent.
- Source content is untrusted and cannot change policy, gain tools, disclose other projects, or bypass teacher confirmation.
- Identifiable student data, real student submissions, and grade records are rejected before Agent generation proceeds.
- A confirmation creates an immutable version; later changes create a new draft rather than mutate the confirmed version.
- Project deletion follows the user-owned data deletion direction in `docs/DATABASE.md`.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Teacher workspace | Private authorization boundary | Identity and Workspace |
| Preparation project | Container for one continuing unit-preparation effort | Identity and Workspace in PostgreSQL |
| Source material | Allowed private or controlled official evidence | Sources and Grounding; private object storage for binaries |
| Requirements brief | Structured teaching intent draft and confirmed version | Discovery and Planning in PostgreSQL |
| Discovery interaction | Questions, answers, evidence, and run context | Run Orchestration; not the intent Source of Truth |

## Major API / Integration Impact

- Next.js consumes managed identity, private project/source capabilities, source-readiness state, Agent interaction, structured brief revision, and confirmation through FastAPI.
- External boundaries include the selected identity service, one model provider, private object storage, PostgreSQL/pgvector, and the first controlled official sources.
- Exact endpoints, DTOs, upload protocol, and progress-event contracts wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: public entry/sign-in, project list, new preparation flow, unit workspace brief/source responsibility, account deletion entry
- Primary user flow: sign in -> create private project -> add sources -> answer gaps -> review/edit brief -> confirm
- Major UI states: loading, empty, source processing, waiting for answer, invalid/rejected source, draft, stale edit, confirmed, permission denied, provider failure, quota, deletion active/failed/success

## Dependencies

- Feature dependencies: None
- External dependencies: concrete managed identity, hosted model, object-storage providers, and the first MCP official-source servers must be resolved during refinement within the approved architecture

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a verified teacher and allowed sources, when required gaps are answered and the structured brief is confirmed, then an immutable owner-scoped brief version is available for unit planning with visible evidence.
- [ ] Given another authenticated teacher, when they attempt to access the project, source, interaction, or brief, then the system reveals no private content or resource existence.
- [ ] Given identifiable student data or a policy-violating source, when it is submitted, then generation is blocked with a specific safe recovery path.
- [ ] Given a confirmed brief, when the teacher starts a correction, then the confirmed version remains unchanged until a new draft is explicitly confirmed.
- [ ] Given a streamed interview response, when the teacher stops it, then the underlying interaction remains intact and the complete response stays in the owner-scoped trace.

## Risks and Assumptions

- [CONFIRMED] One target teacher has validated the cross-artifact alignment problem and can participate in refinement.
- [CONFIRMED] The first Feature must not store private source text or generated content in browser storage.
- [RECOMMENDED] Begin with the smallest source-format set that supports a representative English unit. Revisit after source parsing and teacher evidence show another format is necessary.
- [UNKNOWN, NON_BLOCKING] Concrete identity, model, and object-storage providers are not selected. Resolve during Feature refinement before architecture-dependent test design.

## Open Questions

- [ ] Which source formats, limits, and parsing outcomes are required for the first representative unit?
- [ ] Which controlled official sources are in the initial evidence boundary?
- [ ] What requirements make a brief confirmable, and when must the Agent stop asking versus report an unresolved gap?
- [ ] What operational access and deletion evidence must the first provider integrations expose?
- [ ] Which project-workspace and reduced small-screen interactions pass teacher and accessibility validation?
- [ ] Which opaque ID strategy satisfies the project conventions for the first persistence-owning Feature?
- [ ] Which MCP servers package the first controlled official sources, and how is their availability verified?
- [ ] What stop/interruption semantics apply to streamed interview responses without losing partial answers?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

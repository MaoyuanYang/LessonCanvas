# F013: Teacher Memory

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P1`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-23

> This is a macro-level DRAFT created during a Design Change after `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Let a teacher keep workspace-scoped, teacher-confirmed preference memory that personalizes future preparation without ever overriding confirmed intent.

## Business Value

Repeat unit preparation starts closer to the teacher's established style, and the project demonstrates governed Agent memory — proposal, confirmation, application, audit, and deletion — which most Agent demos omit.

## User Story

As a senior-high English teacher, I want the system to propose remembering preferences I confirmed in earlier work and let me manage them, so that future units start from my style without me re-explaining it.

## Scope

- Propose memory candidates from confirmed briefs, blueprints, and completed runs; never from drafts, rejected content, or unconfirmed chat.
- Require explicit teacher confirmation before any memory persists; keep proposals visibly distinct from confirmed records.
- Provide owner-only viewing, editing, and deletion of all confirmed memory records.
- Apply confirmed memory as subordinate context to discovery and generation in new projects, with the applied context visible in layered evidence.
- Bind memory records to workspace authorization and workspace deletion.
- Treat memory content as untrusted input when it is re-injected into prompts.

## Out of Scope

- Implicit auto-extraction without teacher confirmation.
- Cross-user memory, shared preference corpora, or training use.
- Memory that overrides, rewrites, or invalidates a confirmed brief or blueprint version.
- Student data, learning profiles, or grade-linked personalization.
- Recommendation or personalization analytics beyond the owning workspace.

## Main Flow

1. After a brief confirmation or completed run, the Agent proposes one or more preference candidates with supporting evidence.
2. The teacher confirms, edits, or rejects each proposal; only confirmed records persist at workspace scope.
3. A later project or run displays which confirmed memory applied as context and lets the teacher adjust applicability.
4. The teacher manages records at any time, and record or workspace deletion removes the memory everywhere it applied.

## Core Business Rules

- Only teacher-confirmed records persist; proposals are drafts with no effect on any run.
- Memory never overrides or rewrites confirmed intent; a conflict between memory and the current confirmed version surfaces as a teacher-visible question, with the confirmed version winning.
- Memory records follow workspace authorization and are deleted with the project or account.
- Rejected proposals are not re-proposed in identical form.
- Memory content is untrusted input at re-injection time and is covered by injection defenses.
- Applied memory context is recorded in the run trace so its influence is inspectable.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Memory proposal | Agent-suggested preference with evidence, pending teacher decision | Teacher Memory and Preferences; not persisted as memory until confirmed |
| Confirmed memory record | Workspace-scoped preference available as subordinate context | Teacher Memory and Preferences in PostgreSQL |
| Applied context reference | Links a run to the memory context it used | Run Orchestration trace, referencing memory records |
| Workspace authorization | Owner boundary for every memory operation | Identity and Workspace |

## Major API / Integration Impact

- The Web application needs owner-authorized proposal, confirmation, listing, editing, deletion, and applied-context visibility capabilities through FastAPI.
- Run creation and discovery consume confirmed memory as context input without letting it replace confirmed intent versions.
- Exact proposal format, applicability controls, and memory schema wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: account/workspace memory management area, in-workspace proposal surface, applied-context indicator in evidence view
- Primary user flow: receive proposal -> confirm/edit/reject -> see applied context in later runs -> manage or delete records
- Major UI states: proposal pending, confirmed, applied, conflict with confirmed intent, rejected, empty, deletion pending/failed/complete, permission denied

## Dependencies

- Feature dependencies: `F001` for workspace authorization, confirmed briefs, and the evidence boundary
- External dependencies: none beyond approved runtime and storage boundaries

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a confirmed preference in earlier work, when the Agent proposes memory and the teacher confirms it, then later runs in the workspace visibly apply it as subordinate context.
- [ ] Given memory content that conflicts with the current confirmed blueprint, when generation starts, then the blueprint wins and the conflict is surfaced rather than resolved silently.
- [ ] Given a deleted memory record or deleted workspace, when deletion completes, then no new run applies that memory and no governed copy remains.
- [ ] Given an unconfirmed proposal or a rejected proposal, when any run executes, then it has no effect and the rejected proposal is not re-proposed identically.
- [ ] Given a malicious memory record, when it is re-injected into a run, then it cannot grant tools, change policy, or cross workspace boundaries.

## Risks and Assumptions

- [CONFIRMED] Memory is workspace-scoped, teacher-confirmed, subordinate context and is deleted with the workspace (ADR-0005).
- [CONFIRMED] Memory content is untrusted input at re-injection time.
- [RECOMMENDED] Begin with explicit proposal-and-confirmation only; defer implicit extraction. Revisit if confirmation burden proves excessive and contamination defenses are demonstrated.
- [UNKNOWN, NON_BLOCKING] Memory categories and applicability granularity are not selected. Resolve during Feature refinement with the participating teacher.

## Open Questions

- [ ] Which preference categories are worth remembering first (language defaults, exercise formats, pacing, assessment style)?
- [ ] Does memory apply workspace-wide by default, or per project with explicit opt-in?
- [ ] How are applied memory contexts displayed and adjusted without creating a second workflow authority?
- [ ] How does `F009` pin or empty memory state so technical evaluations stay comparable?
- [ ] What re-proposal policy prevents nagging after rejection while still allowing genuinely new evidence?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

# F002: Confirmed Unit Blueprint

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Turn one confirmed requirements brief into a source-linked blueprint for the complete unit and every lesson, then require the teacher's second explicit confirmation before artifact generation.

## Business Value

The blueprint makes full-unit generation governable. It lets the teacher correct lesson sequence, objective coverage, and intended assessment before errors multiply across every downstream file.

## User Story

As a senior-high English teacher, I want to inspect and confirm how my unit intent is distributed across lessons, so that all later artifacts follow a coherent plan I approved.

## Scope

- Generate a complete-unit blueprint from an immutable confirmed brief and its source evidence.
- Represent every intended lesson and make objective, activity, assessment, source, and language relationships reviewable at a macro level.
- Show evidence and unresolved planning findings without replacing teacher authority.
- Support structured correction and explicit confirmation into an immutable blueprint version.
- Preserve the confirmed brief version to which the blueprint belongs.

## Out of Scope

- Lesson-plan, PPTX, exercise, answer, or alignment-report generation.
- Full run-progress, document-rendering, and recovery behavior introduced by artifact generation.
- Browser-based free-form document or slide editing.

## Main Flow

1. The teacher opens a confirmed brief version and asks the Agent to plan the unit.
2. The system proposes a source-linked blueprint covering the complete unit and every lesson.
3. The teacher reviews objective distribution, flow, assessment intent, and unresolved findings and makes structured corrections.
4. The teacher explicitly confirms an immutable blueprint version for downstream generation.

## Core Business Rules

- A blueprint always belongs to one immutable confirmed brief version.
- Every lesson required by the confirmed unit scope must be represented before confirmation.
- Model output remains a draft until teacher confirmation; chat cannot silently confirm or modify it.
- A source or curriculum conflict is visible and requires correction or a recorded teacher decision.
- A changed brief makes dependent blueprint drafts or confirmations visibly stale; it never mutates history.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Confirmed requirements brief | Immutable upstream teaching intent | Discovery and Planning |
| Unit blueprint | Complete-unit and lesson-level planning intent | Discovery and Planning |
| Lesson intent | One planned lesson's role inside the unit | Part of the owning blueprint version |
| Source evidence | Grounds the proposed plan | Sources and Grounding |
| Planning gap or conflict | Blocks or qualifies a blueprint decision before artifact alignment exists | Discovery and Planning |

## Major API / Integration Impact

- The Web application needs version-aware blueprint generation, structured draft retrieval/update, evidence, conflict, and confirmation capabilities.
- The Agent workflow pauses at the second human gate and exposes no artifact-generation authority before confirmation.
- Concrete contracts and internal specialist roles wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace brief/blueprint responsibility and contextual evidence view
- Primary user flow: open confirmed brief -> generate blueprint draft -> inspect/edit -> resolve findings -> confirm
- Major UI states: generating, partial planning failure, draft, incomplete, source conflict, stale, confirmed, permission denied, provider/limit failure

## Dependencies

- Feature dependencies: `F001` for private sources and a confirmed brief
- External dependencies: the same selected hosted model and controlled official-source boundary

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a confirmed brief, when planning succeeds, then the teacher can review a source-linked blueprint that accounts for every lesson in the intended unit.
- [ ] Given an unconfirmed or stale blueprint, when downstream generation is requested, then generation is not authorized and the missing confirmation is explicit.
- [ ] Given a teacher correction, when a new blueprint is confirmed, then the prior confirmed blueprint remains immutable and traceable.

## Risks and Assumptions

- [CONFIRMED] Full-unit, every-lesson scope is retained despite higher planning and evaluation cost.
- [CONFIRMED] The blueprint is a second teacher authority gate, not an Agent-owned final plan.
- [RECOMMENDED] Keep the first blueprint representation structured enough for impact and alignment reasoning without becoming a full lesson-plan editor. Revisit during teacher flow validation.
- [UNKNOWN, NON_BLOCKING] The representative unit's lesson organization is not selected. Resolve during Feature refinement with the participating teacher.

## Open Questions

- [ ] What minimum relationships and completeness checks make a blueprint confirmable?
- [ ] How does the teacher express lessons, periods, optional activities, and assessment intent without freezing a universal curriculum model?
- [ ] Which conflicts block confirmation and which allow a recorded teacher decision?
- [ ] What comparison is required when a confirmed brief makes an existing blueprint stale?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

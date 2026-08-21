# F004: Editable Lesson Slide Decks

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Generate an editable PPTX slide deck for every lesson in the confirmed unit through the established versioned, traced, and recoverable run lifecycle.

## Business Value

Slide decks supply a core classroom deliverable and test a materially different rendering and validation boundary without creating a second workflow authority.

## User Story

As a senior-high English teacher, I want an editable deck aligned to each lesson plan and unit intent, so that I can prepare classroom presentation material without rebuilding the lesson sequence.

## Scope

- Generate a source- and version-linked editable PPTX for every lesson.
- Reuse the established run ownership, progress, trace, idempotency, checkpoint, and partial-recovery rules.
- Preserve successful decks when another lesson or rendering step fails.
- Validate file presence, openability, renderability, and basic editable structure before ready status.
- Allow owner-authorized preview or download without implementing browser slide editing.

## Out of Scope

- A browser-based slide editor or third-party Office/Google synchronization.
- Exercise, answer, alignment, and teacher-product-validation behavior.
- Redesigning the run lifecycle established by `F003`.

## Main Flow

1. A current confirmed-version run becomes eligible for slide generation.
2. The system generates each lesson deck with progress and trace evidence.
3. Valid decks become available while failed deck scope remains recoverable.
4. The teacher previews or downloads the owner-authorized editable PPTX files.

## Core Business Rules

- Every required lesson has at most one current deck outcome per artifact version while history remains immutable.
- Slide content must derive from the same confirmed intent and evidence as the lesson plan it supports.
- A file is not ready solely because model text exists; rendering and structural validation must succeed.
- Retry and recovery reuse the bound run/version and never publish stale output as current.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Lesson intent and plan | Context for the deck's teaching sequence | Confirmed blueprint / Artifact Production |
| Slide-deck artifact | Editable per-lesson classroom presentation | Artifact Production metadata plus private object storage |
| Rendering outcome | Generation evidence that the PPTX exists and can be inspected | Artifact Production; later package validation consumes this evidence |
| Generation run and trace | Shared progress, recovery, cost, and provenance | Run Orchestration |

## Major API / Integration Impact

- Existing run, progress, artifact, and download capabilities extend to PPTX generation and validation.
- A presentation-rendering tool boundary is added without creating a new business workflow Source of Truth.
- Concrete layout grammar, renderer, file checks, and preview strategy wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace generation and per-lesson artifact review/download
- Primary user flow: monitor deck generation -> inspect result/failure -> resume if eligible -> preview/download editable PPTX
- Major UI states: not started, queued, rendering, validating, ready, partial failure, invalid file, resumed, stale/superseded, permission/provider failure

## Dependencies

- Feature dependencies: `F003` for the confirmed-version run, complete lesson inventory, progress, trace, and recovery contract
- External dependencies: selected PPTX generation and open/render validation tools

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a complete current unit version, when deck generation completes, then every lesson has an owner-authorized, openable, editable PPTX bound to that version.
- [ ] Given one deck fails rendering, when the teacher inspects the run, then successful decks remain available and the failed scope has a safe recovery path.
- [ ] Given an older version finishes late, when publication is attempted, then it remains historical and cannot become the current deck.

## Risks and Assumptions

- [CONFIRMED] Editable PPTX is required; PDF-only output does not satisfy the Feature.
- [CONFIRMED] The Web application will not provide Office-class slide editing.
- [RECOMMENDED] Use a restrained reusable presentation grammar before adding broad template customization. Revisit when teacher review identifies a concrete unmet teaching need.
- [UNKNOWN, NON_BLOCKING] Exact deck structure, visual template range, and preview fidelity are not selected. Resolve during Feature refinement.

## Open Questions

- [ ] What makes a representative senior-high English deck structurally and visually acceptable?
- [ ] Which render/open/edit checks are deterministic enough for CI and which require controlled Office smoke tests?
- [ ] How are source citations, teacher notes, and language modes represented without freezing a universal slide schema?
- [ ] What failure scope allows safe per-lesson or per-deck recovery?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

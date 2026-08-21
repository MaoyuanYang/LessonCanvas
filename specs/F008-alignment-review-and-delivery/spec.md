# F008: Alignment Review and Delivery

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Trace confirmed objectives through the complete current package, let the teacher resolve or explicitly override findings, and deliver a selected draft or technically validated unit version.

## Business Value

This Feature directly addresses the validated teacher problem: it makes cross-artifact coverage and conflict visible before a collection of generated files is treated as a coherent teaching package.

## User Story

As a senior-high English teacher, I want to review how each objective is supported by lessons, slides, exercises, and answers, so that I can correct gaps and deliver a package with an honest status.

## Scope

- Produce a unit-level Web alignment report across sources, confirmed brief, blueprint, lesson plans, slide decks, exercises, and answers for one immutable version.
- Distinguish coverage, gap, conflict, severe correctness finding, technical package status, and product-validation status.
- Link each finding to understandable evidence and affected scope.
- Allow a teacher to correct upstream intent, request targeted regeneration, or record a reasoned override for a disputed severe finding.
- Permit draft export while severe findings remain, but block technically validated completion until correction or a recorded override.
- Select and deliver the authorized current unit package and a printable alignment report without implementing browser Office editing.

## Out of Scope

- External teacher rubric and product-validation threshold execution.
- Claiming that technical package validation proves classroom usability.
- Silent mutation of sources, confirmed intent, or artifacts by the alignment process.
- School approval, collaboration, or LMS publication.

## Main Flow

1. The system evaluates one complete current version and presents objective-to-source/plan/artifact coverage and findings.
2. The teacher inspects evidence and chooses correction, targeted regeneration, or an explicit reasoned override where allowed.
3. Alignment and package status updates against the same immutable version or a newly generated replacement version.
4. The teacher exports a labelled draft or delivers the technically validated selected package.

## Core Business Rules

- Alignment and Evaluation owns findings, technical package-validation status, product-validation status, and evaluation results; it never owns or silently changes the content it evaluates.
- A finding is bound to explicit source, intent, artifact, and run versions.
- A known severe finding blocks technically validated completion unless corrected or explicitly overridden by the teacher with a recorded reason.
- Draft export remains available and is clearly labelled; it cannot be represented as technically or product validated.
- Technical package validation and teacher product validation are separate statuses.
- Only the workspace owner may override a finding, select a current deliverable, or download the private package.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Objective-alignment relationship | Connects confirmed intent to lessons and artifacts | Alignment and Evaluation, derived from version-bound evidence |
| Alignment finding | Coverage, gap, conflict, or severe issue | Alignment and Evaluation |
| Technical package-validation status | States whether technical package gates are satisfied | Alignment and Evaluation |
| Teacher override | Owner decision resolving a disputed finding with rationale | Alignment and Evaluation audit bound to workspace owner |
| Selected unit package | Authorized collection of one version's current artifacts | Export and Delivery referencing owning artifact versions |

## Major API / Integration Impact

- The Web application consumes alignment/evaluation, evidence, override, package-status, selection, export, and print capabilities through owner-authorized FastAPI contracts.
- Targeted correction delegates upstream to `F007`; export delegates to private object storage without exposing raw storage paths.
- Exact finding taxonomy, report model, override policy, and package manifest wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace alignment, artifact/evidence context, version selection, export and printable report
- Primary user flow: open complete version -> inspect coverage/findings -> correct/regenerate or override -> review status -> export selected package
- Major UI states: evaluating, partial evaluation, no findings, warning, severe finding, draft exportable, override pending/recorded, technically validated, product status separate, stale/superseded, export active/failed/ready

## Dependencies

- Feature dependencies: `F006` for layered evidence and `F007` for safe correction and targeted regeneration across all artifact families
- External dependencies: controlled content/evaluation tools and authorized Office packaging/print behavior selected during refinement

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a complete current unit version, when alignment review finishes, then each confirmed objective has visible supported, missing, conflicting, or otherwise resolved relationships across the relevant package.
- [ ] Given an unresolved severe finding, when the teacher exports, then a clearly labelled draft is allowed but technically validated completion is blocked.
- [ ] Given the owner records an allowed override with a reason, when status is recalculated, then the decision and evidence remain auditable without changing the evaluated content.
- [ ] Given a selected validated version, when delivery is requested, then only the owner receives the authorized package and printable report for that version.

## Risks and Assumptions

- [CONFIRMED] Teacher authority can resolve a disputed severe finding with a recorded reason; Agent review cannot silently overrule the teacher.
- [CONFIRMED] Product validation remains independent even when the technical package is validated.
- [RECOMMENDED] Show teacher-readable alignment relationships before exposing scoring or model-judge detail. Revisit after teacher evaluation of the report.
- [UNKNOWN, NON_BLOCKING] Exact finding severity and override eligibility are not selected. Resolve during Feature refinement and Test Design.

## Open Questions

- [ ] Which alignment relationships and severe findings are deterministic, model-assisted, or teacher-judged?
- [ ] Which severe findings may be overridden, and what reason/evidence is required?
- [ ] What constitutes a complete technically validated package without implying product validation?
- [ ] How are draft labels and selected-version status preserved inside downloaded Office files and the printable report?
- [ ] What teacher workflow keeps a large unit report understandable and keyboard accessible?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

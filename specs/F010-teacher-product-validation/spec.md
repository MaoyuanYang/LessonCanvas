# F010: Teacher Product Validation

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P1`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Record whether representative complete units meet the independently defined senior-high English teacher-quality threshold, without rewriting technical completion or overstating one evaluator's evidence.

## Business Value

The project can distinguish a strong engineering demonstration from a validated teacher product. Failed or incomplete product evidence remains useful learning rather than becoming a hidden or inflated claim.

## User Story

As the project owner and a portfolio reviewer, I want external teacher evaluation reported separately from technical results, so that teacher-usability claims are honest and reproducible.

## Scope

- Use one external senior-high English teacher and a consistent rubric to fully review at least two representative complete units.
- Evaluate severe knowledge, language, answer, and objective-alignment errors; core rubric quality; and need for structural rework.
- Require zero severe errors, a core-rubric mean of at least 4/5, and no structural rework for product-validation pass.
- Record passed, failed, or not-complete product-validation status bound to the exact evaluated versions and evidence.
- Show product-validation status separately from technical package validation and technical Phase-1 status.
- Preserve evaluator evidence privately and publish only synthetic or appropriately summarized portfolio evidence under the current privacy boundary.

## Out of Scope

- Generalizing one teacher's result to all schools, regions, textbooks, or English teachers.
- Treating positive feedback, an LLM judge, or artifact completeness alone as product validation.
- Student outcomes, classroom experiment claims, automatic grading, or educational efficacy research.
- Blocking honest technical completion solely because product validation failed.

## Main Flow

1. The evaluator receives a fixed complete-unit version, its intended context, and a consistent review rubric.
2. The evaluator reviews at least two units and records criterion evidence and severe findings.
3. The system calculates and records passed, failed, or not-complete product-validation status without changing the evaluated content.
4. LessonCanvas displays the bounded conclusion alongside, but not merged with, technical status.

## Core Business Rules

- Product validation is version-bound and cannot transfer automatically to regenerated or materially changed artifacts.
- Any severe knowledge, language, answer, or objective-alignment error fails the approved threshold.
- A mean below 4/5, structural rework requirement, missing unit, or incomplete rubric prevents pass.
- Technical Phase 1 may pass while product validation fails; the UI and portfolio must prohibit teacher-usability claims in that case.
- One teacher supplies bounded evidence, not market-wide validation.
- Model-based evaluation may inform review but cannot replace the external teacher decision.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Teacher evaluator | External domain reviewer for bounded evidence | Evaluation process; not architecture/Roadmap authority |
| Product-validation rubric | Consistent teacher-review criteria | Alignment and Evaluation |
| Evaluated unit version | Immutable complete package under review | Owning project modules |
| Severe product finding | Blocking quality evidence | Alignment and Evaluation, supported by evaluator evidence |
| Product-validation status | Passed, failed, or not complete | Alignment and Evaluation |

## Major API / Integration Impact

- Authorized rubric assignment, evidence capture, status calculation, and read-only portfolio summary extend the evaluation boundary.
- The first version may use a controlled authenticated evidence-capture flow for the external teacher rather than a generalized public reviewer role, subject to refinement.
- Concrete rubric fields, invitations, signatures, evidence attachments, and publication format wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: technical/evaluation evidence area and product-validation status summary; evaluator input surface remains an open refinement choice
- Primary user flow: select fixed unit versions -> complete teacher rubric -> record evidence -> calculate bounded status -> display separately
- Major UI states: not started, evaluator pending, partial review, severe finding, failed, passed, stale after regeneration, access denied

## Dependencies

- Feature dependencies: `F009` for fixed representative versions, version-bound evaluation evidence, and separate technical-result reporting
- External dependencies: one stable participating senior-high English teacher

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given at least two fixed complete-unit versions and a completed external-teacher rubric, when all approved thresholds pass, then product validation is recorded as passed for only those versions.
- [ ] Given any severe error, mean below 4/5, required structural rework, or incomplete evidence, when status is calculated, then product validation is failed or not complete and teacher-usability claims remain blocked.
- [ ] Given technical evidence passes while product validation fails, when status is displayed, then technical completion remains visible and product failure is equally explicit.
- [ ] Given an evaluated version is regenerated materially, when the new version becomes current, then the prior product-validation result remains historical rather than transferring.

## Risks and Assumptions

- [CONFIRMED] One teacher can provide sustained review but cannot support broad product-generalization claims.
- [CONFIRMED] Product validation does not block honest technical portfolio completion.
- [RECOMMENDED] Keep the first evaluator workflow controlled rather than build a generalized reviewer-account product. Revisit when additional independent evaluators are committed.
- [UNKNOWN, NON_BLOCKING] Rubric wording, representative topics, and evidence-publication detail are not selected. Resolve before `TEST DESIGN READY`.

## Open Questions

- [ ] Which rubric dimensions are core, and how are severe errors distinguished from ordinary revision feedback?
- [ ] Which two or more representative units provide meaningful but bounded coverage?
- [ ] Does the evaluator use an authenticated in-app flow or a controlled evidence-import process in Phase 1?
- [ ] Which evidence can appear publicly without exposing teacher identity or private content?
- [ ] What change makes a prior product-validation result stale?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

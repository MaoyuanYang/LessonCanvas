# F005: Lesson Exercises and Answers

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Generate editable DOCX exercise and answer sets for every lesson, bound to the confirmed unit version and recoverable run lifecycle.

## Business Value

Exercises and answers complete the core teaching package while exposing objective coverage, language quality, answer correctness, and source grounding as observable risks rather than hidden model output.

## User Story

As a senior-high English teacher, I want editable exercises and answers for each lesson, so that classroom practice and assessment reflect the objectives and content I confirmed.

## Scope

- Generate a paired editable DOCX exercise set and answer set for every lesson.
- Link each pair to the same confirmed intent, source evidence, lesson context, run, and artifact version.
- Reuse established progress, full trace, idempotency, checkpoint, partial-failure, and authorized-delivery behavior.
- Validate package completeness, file openability, answer coverage, and initially defined deterministic correctness constraints.
- Preserve successful lesson sets while failed scope remains visible and recoverable.

## Out of Scope

- Student submission, automatic grading, grade storage, or student-specific adaptation from real personal data.
- A general question bank, item marketplace, or LMS export.
- Browser-based DOCX editing.
- Final cross-artifact alignment and external teacher validation.

## Main Flow

1. A current confirmed-version run becomes eligible for exercise and answer generation.
2. The system produces paired lesson-level files with visible progress and evidence.
3. Validation identifies missing answers, invalid packages, or other known critical failures.
4. The teacher resumes eligible failed scope and downloads authorized editable files when ready.

## Core Business Rules

- Every required exercise has an answer or an explicitly justified non-answer outcome defined during refinement.
- Exercises and answers derive from the same confirmed version and cannot silently introduce objectives or source claims outside it.
- A package with a known severe answer, language, or file-integrity failure cannot be represented as ready.
- No real student response, identity, or grade data enters generation or evaluation.
- Retry and recovery reuse the bound run and do not duplicate current artifacts or model cost.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Lesson objective and context | Defines intended practice and assessment coverage | Confirmed blueprint and current lesson artifacts |
| Exercise artifact | Editable student-facing practice material | Artifact Production metadata plus private object storage |
| Answer artifact | Editable paired reference answer material | Artifact Production metadata plus private object storage |
| Package finding | Missing, invalid, or severe correctness evidence | Alignment and Evaluation |
| Generation run and trace | Shared progress, recovery, provenance, and cost | Run Orchestration |

## Major API / Integration Impact

- Existing run, progress, artifact, validation, and authorized-download boundaries extend to paired DOCX exercise/answer artifacts.
- Controlled deterministic and model-assisted checks may contribute evidence, but exact tools and contracts wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace generation and per-lesson exercise/answer review/download
- Primary user flow: monitor paired generation -> inspect result/finding -> resume if eligible -> download editable DOCX files
- Major UI states: not started, queued, generating, validating, ready, missing pair, severe finding, partial failure, resumed, stale/superseded, permission/provider failure

## Dependencies

- Feature dependencies: `F003` for the confirmed-version run, all-lesson inventory, trace, progress, and recovery contract
- External dependencies: selected DOCX generation/open validation and controlled content-check boundaries

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a current confirmed unit version, when generation completes, then every lesson has an owner-authorized, openable editable exercise DOCX and corresponding answer DOCX.
- [ ] Given a missing or severe answer/package finding, when validation completes, then the affected pair is not represented as ready and the teacher sees a specific recovery path.
- [ ] Given a transient failure after other lesson sets succeed, when the run resumes, then completed pairs remain intact and only eligible incomplete work continues.

## Risks and Assumptions

- [CONFIRMED] Severe answer errors prevent product-validation success and cannot be hidden by file completion.
- [CONFIRMED] Student submissions and grades are prohibited.
- [RECOMMENDED] Start with a bounded exercise variety tied to the representative units rather than claim a universal English item generator. Revisit when teacher evidence requires another exercise type.
- [UNKNOWN, NON_BLOCKING] The first exercise categories and deterministic answer checks are not selected. Resolve during Feature refinement with teacher examples.

## Open Questions

- [ ] Which exercise categories are required to demonstrate each representative unit and language mode?
- [ ] Which answer and language failures can be checked deterministically, and which require model or teacher review?
- [ ] What makes an exercise/answer pair complete and ready for downstream alignment review?
- [ ] How should teacher-requested difficulty or variation be expressed without student personal data?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

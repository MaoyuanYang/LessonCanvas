# F009: Technical Portfolio Evaluation

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-23

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Produce reproducible, version-bound evidence for grounding, specialist orchestration, editable artifacts, alignment, idempotency, concurrency behavior, cost, and failure recovery across representative complete units.

## Business Value

The project becomes a falsifiable engineering portfolio instead of a feature list or curated demo. Reviewers can see what passed, failed, changed, and cost resources under controlled conditions.

## User Story

As a portfolio reviewer or project owner, I want repeatable technical evaluation tied to complete traces and artifacts, so that I can assess the system's Agent and application engineering claims.

## Scope

- Define controlled technical evaluation runs for at least three representative complete units covering Chinese, English, and bilingual output modes.
- Create, license-check, version, and govern the synthetic or public representative unit set reused by technical evaluation and later deployed portfolio samples.
- Bind datasets, source evidence, intent versions, model configuration, run traces, artifacts, findings, and metrics to comparable evaluation results.
- Combine deterministic rule/file checks, contract evidence, model-assisted evaluation, and run-level measures without making one model judge the sole authority.
- Inject representative Worker, provider, duplicate-submission, stale-version, and partial-render failures and verify expected recovery.
- Measure grounding, workflow completion, artifact integrity, alignment evidence, latency, and model cost within the approved technical-success boundary.
- Present pass, fail, and missing-evidence outcomes through the layered evidence experience.

## Out of Scope

- External teacher product validation or teacher-usability claims.
- Replacing deterministic, integration, accessibility, or security tests with an LLM judge.
- Multi-model benchmarking, routing, fine-tuning, or generalized academic benchmarking.
- Final public multi-account hardening and cloud-release proof.

## Main Flow

1. The project owner selects a fixed synthetic/licensed representative unit and evaluation configuration.
2. The system executes or references one immutable complete-unit run and gathers deterministic, model-assisted, artifact, trace, cost, and recovery evidence.
3. Injected failure and concurrency cases produce expected state transitions and recovery outcomes.
4. The evaluation result records pass, fail, or missing evidence for the fixed version and is inspectable through its trace.

## Core Business Rules

- Evaluation never mutates the sources, intent, runs, artifacts, or findings it measures.
- Every result is bound to a fixed version and sufficient configuration evidence for later comparison.
- Public and persistent evaluation fixtures are synthetic, public, or explicitly licensed and contain no private teacher or student content.
- Evaluation runs pin or empty teacher-memory state so results remain comparable across runs and versions (ADR-0005).
- A model-based judge cannot be the only evidence for a technical or product claim.
- A failed or missing core technical criterion remains visible; it cannot be hidden by an aggregate score.
- This Feature creates technical evidence but does not alone declare the publicly deployed Phase 1 complete.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Evaluation case / set | Fixed representative input and expected evidence direction | Alignment and Evaluation |
| Evaluated version/run | Immutable subject of evaluation | Owning source, planning, run, and artifact modules |
| Technical evaluation result | Version-bound pass/fail/missing evidence | Alignment and Evaluation |
| Fault-injection outcome | Demonstrates expected failure and recovery behavior | Test/evaluation evidence linked to Run Orchestration |
| Cost / latency evidence | Shows resource and performance behavior | Run Orchestration and Observability |

## Major API / Integration Impact

- Controlled evaluation execution, result retrieval, comparison, and evidence linkage cross the application/Worker boundary without becoming a second workflow system.
- Test harnesses exercise model, database, queue, object, rendering, and Web contracts according to `docs/TESTING.md`.
- Concrete datasets, score formulas, judge prompts, thresholds beyond approved macro criteria, and result schemas wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: layered run evidence and technical evaluation status/report within authorized project or portfolio sample context
- Primary user flow: select fixed evaluation -> run/inspect -> view criteria and evidence -> compare or diagnose failure
- Major UI states: not run, queued, active, partial evidence, pass, fail, missing evidence, provider unavailable, superseded configuration, comparison unavailable

## Dependencies

- Feature dependencies: `F008` for a complete version, all artifacts, alignment status, delivery, and layered evidence
- External dependencies: one selected model provider plus controlled test/evaluation environments and representative licensed or synthetic units

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given the three representative language-mode units, when the controlled suite runs, then every result is tied to immutable sources, intent, run, artifacts, configuration, trace, and explicit criterion outcomes.
- [ ] Given injected Worker/provider/duplicate/stale-version failures, when the system handles them, then the evaluation records the expected idempotency, preservation, supersession, and recovery behavior.
- [ ] Given a failed core criterion or missing evidence, when the report is viewed, then the failure remains explicit and cannot be masked by aggregate success.
- [ ] Given only a model-judge opinion without required deterministic or integration evidence, when technical status is calculated, then the criterion is not considered proven.

## Risks and Assumptions

- [CONFIRMED] Technical success is independent from teacher product validation but still requires every approved core technical evidence class.
- [CONFIRMED] Multi-Agent remains a Phase-1 portfolio requirement even without proof that it beats a simpler baseline.
- [RECOMMENDED] Keep deterministic CI separate from controlled live-model evaluation when variance or cost would make CI unreliable. Revisit if provider controls make a stable subset affordable.
- [UNKNOWN, NON_BLOCKING] Representative unit topics, evaluation prompts, and detailed criteria are not selected. Resolve before `TEST DESIGN READY`.

## Open Questions

- [ ] Which evidence classes are blocking for each technical claim, and which are diagnostic only?
- [ ] How are live-model variance, retries, and provider changes represented without normalizing away regressions?
- [ ] Which fault injections are safe and representative in local, CI, and staging environments?
- [ ] What comparison baseline is informative even though Multi-Agent retention is not contingent on superiority?
- [ ] How are evaluation sets licensed, versioned, reviewed, and protected from accidental private content?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

# F006: Layered Run Evidence

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Let a teacher understand why a run produced its current outcome and let an authorized portfolio reviewer inspect complete technical evidence without turning the default teacher experience into a developer console.

## Business Value

Layered evidence makes grounding, specialist orchestration, tools, cost, latency, retries, checkpoints, and evaluation credible and inspectable instead of relying on architecture diagrams or a polished demo alone.

## User Story

As a teacher or authorized reviewer, I want to move from a plain-language run explanation into detailed evidence, so that I can understand the result at the depth relevant to me.

## Scope

- Present teacher-readable source, decision, progress, finding, and recovery explanations in the current project context.
- Allow the workspace owner to expand sources, specialist steps, prompts/outputs, tool calls, model configuration, cost, latency, failures, retries, checkpoints, and validation/evaluation details that exist for their run.
- Bind every displayed detail to the authoritative project, immutable intent version, run, and artifact scope.
- Disclose missing or incomplete telemetry without hiding the authoritative run outcome.
- Preserve accessible keyboard, semantic, reduced-motion, and non-color behavior for trace relationships.

## Out of Scope

- Cross-user analytics, a shared trace corpus, or using teacher content for training.
- A default raw-prompt view for every teacher task.
- A general infrastructure observability console or unrestricted operator access.
- Changing business state, retrying work, or resolving findings solely from a read-only evidence view.

## Main Flow

1. The owner opens a run, artifact, or finding and sees a teacher-readable explanation in context.
2. The owner expands technical evidence for the relevant version and run.
3. The system shows source, Agent, tool, metric, failure, recovery, and evaluation relationships without exposing another workspace.
4. The user returns to the teaching task without losing its version or decision context.

## Core Business Rules

- Complete traces belong to the teacher workspace and follow source/artifact authorization and deletion.
- Raw source, prompt, output, and trace content is never available across teacher accounts or stored in generic browser or infrastructure logs.
- Private teacher traces are never republished as portfolio samples; `F009` owns creation and versioning of synthetic evaluation fixtures used by later public proof.
- Teacher-readable state remains authoritative even if a low-level trace element is unavailable; the gap is explicit.
- Technical details may explain a teacher decision but cannot replace confirmation, override, or validation rules.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Run trace | Complete version-bound technical history | Run Orchestration in PostgreSQL; teacher workspace owns access |
| Evidence summary | Teacher-readable projection of authoritative run and source facts | Derived from owning modules; not an independent truth |
| Specialist step / tool outcome | Explains workflow work and failure | Run Orchestration plus the owning module |
| Cost / latency metric | Supports portfolio and operational evidence | Run Orchestration / Observability |
| Validation or evaluation result, when present | Explains a fixed run/artifact outcome supplied by its owning Feature | Alignment and Evaluation |

## Major API / Integration Impact

- Owner-authorized APIs expose layered run summaries and paged or scoped technical evidence without leaking raw internals in errors.
- The Web application maps trace and evaluation state into accessible progressive disclosure.
- Concrete event, trace, prompt, model-metadata, and pagination contracts wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: contextual run evidence view within the unit workspace and synthetic portfolio sample entry
- Primary user flow: open run/artifact -> read summary -> expand relevant evidence -> inspect relationship -> return to task
- Major UI states: no run, active/incomplete trace, available summary, expanded detail, missing telemetry, partial failure, stale/superseded evidence, permission denied, large-trace loading

## Dependencies

- Feature dependencies: `F003`, `F004`, and `F005` for complete artifact-family runs and trace evidence
- External dependencies: selected model metadata/cost availability and any approved telemetry tooling must preserve application ownership and deletion boundaries

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given an owner with a complete-unit run, when they open evidence, then they first receive a teacher-readable explanation and can expand version-bound sources, specialist work, tools, metrics, failures, retries, and the validation evidence available at that stage.
- [ ] Given another teacher or an unauthenticated user, when they request private run evidence, then no trace content or resource existence is disclosed.
- [ ] Given an incomplete telemetry segment, when the evidence view loads, then the gap is explicit while authoritative run and artifact status remains correct.

## Risks and Assumptions

- [CONFIRMED] Every run retains a complete user-owned trace despite privacy and storage cost.
- [CONFIRMED] Teacher-readable evidence precedes technical detail through progressive disclosure.
- [RECOMMENDED] Keep the first trace visualization relationship-focused and text-semantic before adding complex graph animation. Revisit after reviewer and accessibility evidence.
- [UNKNOWN, NON_BLOCKING] Exact hosted-model token/cost metadata and trace volume are provider-dependent. Resolve during Feature refinement.

## Open Questions

- [ ] Which evidence is essential in the teacher summary versus the technical expansion?
- [ ] How are prompts, source excerpts, and model outputs safely displayed and copied without bypassing private-content rules?
- [ ] What pagination or progressive-loading behavior is needed for a complete unit trace?
- [ ] How is operator troubleshooting access disclosed and audited without creating a separate content store?
- [ ] Which visual relationships remain understandable to keyboard and screen-reader users?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

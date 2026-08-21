# F007: Versioned Targeted Regeneration

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Let a teacher change confirmed requirements or unit intent, understand the impact, and regenerate only affected work without stale publication or loss of valid history.

## Business Value

Versioned targeted regeneration makes real teaching iteration safe and demonstrates dependency reasoning, concurrency control, model-cost discipline, and recovery beyond one-shot generation.

## User Story

As a senior-high English teacher, I want to revise confirmed intent and rebuild only affected lessons and artifacts, so that valid work remains usable and the current package stays explainable.

## Scope

- Start a structured draft from a confirmed brief or blueprint without mutating history.
- Show the proposed change and predicted affected lessons, artifacts, findings, evaluations, and active run.
- Confirm a new immutable upstream version through the applicable teacher gate.
- Detect stale edits and require explicit conflict resolution rather than last-write-wins behavior.
- Supersede an older active run at a safe checkpoint and prevent it from publishing current output.
- Regenerate affected lesson plans, decks, exercises, and answers while retaining unaffected valid artifacts when dependency evidence allows.
- Compare changed intent, impacted output, and current/historical version status.

## Out of Scope

- Free-form branching of multiple simultaneous current versions.
- Collaborative merge, approval, or school-level review workflows.
- Silent Agent mutation of a confirmed brief, blueprint, or current artifact selection.
- Pixel-level document diffing or in-browser Office editing.

## Main Flow

1. The teacher opens a confirmed version and begins a structured brief or blueprint revision.
2. The system presents an impact preview and detects stale or concurrent changes.
3. The teacher confirms a new immutable version; the old active run becomes superseded and stops at a safe checkpoint.
4. Only affected artifact scope regenerates, and the teacher compares the new result with retained history.

## Core Business Rules

- Confirmed brief and blueprint versions are immutable; revisions create new versions.
- One version is current for a project context, while older versions remain historical and traceable.
- Duplicate requests for the same intent reuse the same run; a new intent version creates a distinct run identity.
- The impact decision is explainable and conservative: uncertain dependency impact regenerates or asks rather than silently retain possibly stale work.
- An old run or artifact never overwrites the current version, even if it finishes later.
- Unaffected artifact reuse must preserve source, intent, run, and validation provenance.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Brief / blueprint draft and version | Upstream change and immutable confirmation | Discovery and Planning |
| Impact assessment | Explains affected downstream scope | Run Orchestration with owning module evidence |
| Current / stale / superseded status | Prevents version confusion and old publication | PostgreSQL business state |
| Regeneration run | Idempotent work bound to the new version | Run Orchestration |
| Reused / regenerated artifact | Historical or current derived output with provenance | Artifact Production |

## Major API / Integration Impact

- Version-aware draft, impact, confirmation, conflict, supersession, selective-run, comparison, and current-selection capabilities cross the Web/FastAPI boundary.
- PostgreSQL transactions enforce version/current/run invariants; Celery and LangGraph stop or resume work at safe boundaries.
- Exact dependency graph, conflict payload, and comparison representation wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace brief, blueprint, versions, generation, artifact comparison, and contextual evidence
- Primary user flow: edit confirmed intent -> inspect impact -> resolve conflict -> confirm new version -> monitor targeted regeneration -> compare
- Major UI states: editing draft, unsaved, impact calculating, conflict, confirmed new version, old run superseding/superseded, retained artifact, regenerating, partial failure, current/historical

## Dependencies

- Feature dependencies: `F003`, `F004`, and `F005` for all artifact families and the established versioned run/recovery behavior
- External dependencies: none beyond approved runtime and storage boundaries

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a confirmed version, when the teacher confirms a material upstream change, then a new immutable version is created and affected downstream scope is visibly identified.
- [ ] Given an older run is active, when the new version is confirmed, then the older run stops at a safe checkpoint and cannot publish over the new version.
- [ ] Given unaffected artifacts have valid provenance, when targeted regeneration completes, then they remain available without duplicate generation while affected artifacts belong to the new version.
- [ ] Given a stale browser edit, when confirmation is attempted, then the system returns a visible conflict rather than overwriting the newer version.

## Risks and Assumptions

- [CONFIRMED] Versioned impact regeneration is required; whole-unit regeneration is not the default recovery from every change.
- [CONFIRMED] Historical output remains available but never appears current after supersession.
- [RECOMMENDED] Begin with conservative dependency impact rules and visible uncertainty. Revisit after evaluation proves safe reuse for more cases.
- [UNKNOWN, NON_BLOCKING] The first set of changes that can safely retain each artifact type is not selected. Resolve during Feature refinement and Test Design.

## Open Questions

- [ ] Which upstream changes affect a whole unit, one lesson, one artifact family, or only validation?
- [ ] What is the teacher-visible difference among draft, stale, superseding, superseded, current, and validated?
- [ ] When may an active model call finish versus require cancellation at the next safe checkpoint?
- [ ] What evidence proves a reused artifact remains valid under the new intent version?
- [ ] What comparison depth is useful without creating an Office editor?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

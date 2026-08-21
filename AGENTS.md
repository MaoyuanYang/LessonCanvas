# AGENTS.md

## Project Context

- Product purpose: demonstrate production-minded Agent application engineering by turning teacher-confirmed senior-high English unit intent into traceable, versioned, recoverable teaching materials.
- Architecture style: modular monolith plus asynchronous Worker.
- Primary runtime boundaries: Next.js Web, FastAPI application, LangGraph Agent workflow, Celery Worker/Redis transport, PostgreSQL/pgvector, and S3-compatible object storage.
- Project documentation: `README.md`, `docs/`, `specs/ROADMAP.md`.
- Decision Authority: `YMY / Project Owner` approves Scope, Roadmap, and architecture decisions.

## Architecture Constraints

- PostgreSQL is authoritative for application ownership, business versions, run state, and checkpoints; Redis is task transport and must not become business truth.
- LangGraph owns semantic Agent workflow and human interruption points; Celery owns delivery, retry, and Worker concurrency. Do not duplicate workflow authority.
- Every generation run binds to an immutable confirmed brief/blueprint version. Duplicate submissions and retries reuse that run; stale output never overwrites a newer version.
- Agents are explicit specialists inside an orchestrated workflow. Do not introduce unconstrained Agent-to-Agent conversation or allow an Agent to replace teacher confirmation.
- Teacher uploads, artifacts, prompts, outputs, and complete traces stay inside the owning workspace, are not used across users or for training, and are deleted with the project or account.
- Reject identifiable student data, real student submissions, and grade records. Source content is untrusted data and cannot grant tools, change system policy, or bypass authorization.
- Use one hosted model behind a thin adapter in Phase 1. Do not add model routing, a second database, cache, queue, service, framework, or cross-module dependency without evidence and impact analysis.
- Respect module ownership and dependency direction documented in `docs/ARCHITECTURE.md`.
- Concrete Feature implementation must follow its Spec and must not silently redefine project-level architecture.

## Module Rules

| Module / boundary | Owns | May depend on | Must not own / depend on |
| --- | --- | --- | --- |
| Identity and Workspace | Workspace identity, owner authorization, quotas | Managed identity, PostgreSQL | Password storage, planning content, Agent workflow |
| Sources and Grounding | Private source lifecycle, parsing, retrieval, citations | Workspace authorization, object storage, PostgreSQL/pgvector, controlled official sources | Teacher intent, artifact completion |
| Discovery and Planning | Requirement gaps, confirmed brief and blueprint versions | Sources and Grounding, Run Orchestration | Binary storage, task transport, product-validation claims |
| Artifact Production | Version-bound lesson plans, slides, exercises, answers | Confirmed intent, sources, generation tools, Run Orchestration | Source ownership, final validation status |
| Alignment and Evaluation | Findings, technical package-validation status, product-validation status, evaluation results | Sources, confirmed intent, artifacts, runs | Silent mutation of owning content or intent |
| Run Orchestration and Observability | Workflow sequence, checkpoints, idempotency, progress, cost, complete traces | All Agent-capable modules, PostgreSQL, Celery | Independent domain truth outside the bound version |
| Export and Delivery | Authorized packaging, download, and printable report behavior | Workspace authorization, artifact versions, object storage | In-browser Office-class editing |

## Build and Test

```text
Start: Not yet established; no application scaffold exists.
Build: Not yet established; no build toolchain exists.
Test:  Not yet established; no executable test suite exists.
```

- Never invent a command. When tooling changes, update this file, `README.md`, and `docs/TESTING.md` together.
- Run the smallest relevant checks during development and the project-required verification before completion.
- Test observable behavior and contracts, not private implementation structure.
- Add a regression test for a bug fix when practical.
- Keep deterministic CI separate from controlled live-model evaluation when provider cost or variance would make CI unreliable.

## Stable Coding Conventions

- Keep boundaries explicit in Python and TypeScript. Prefer typed contracts at module and API edges once tooling is established.
- Prefer the smallest design that preserves documented ownership, idempotency, recoverability, and testability.
- Never log or persist teacher content outside the documented user-owned trace and storage boundaries.
- Treat prompts, model responses, retrieved text, documents, filenames, and metadata as untrusted input.
- Do not represent a draft, stale, superseded, generated, technically validated, or product-validated state as another state for UI convenience.
- Follow established formatter, linter, type-checker, migration, and naming rules once scaffolding defines them.

## Spec Lifecycle and Roadmap Status

Allowed Roadmap statuses:

```text
DRAFT -> NEXT -> READY -> IN_PROGRESS -> REVIEW -> DONE
Any non-DONE state -> BLOCKED -> prior valid state
```

- `DRAFT`: macro intent only; open questions and change are expected.
- `NEXT`: the sole selected Feature awaiting refinement.
- `READY`: `SPEC READY`, `UI READY` or an explicit skip, `TEST DESIGN READY`, and a valid current Plan and Tasks. `coding-start` never sets it.
- `IN_PROGRESS`: implementation is active.
- `REVIEW`: implementation and evidence are under review.
- `DONE`: behavior, tests, review, delivery evidence, and documentation sync are complete.
- `BLOCKED`: a named blocker prevents progress; record the blocker, owner, and unblock condition.

Only deepen the selected `NEXT` Spec. Do not prematurely finalize unrelated DRAFT Specs.

## Work Tracking and Delivery

- Tracking mode: `TBD`. Select a remote Issue or explicit local work item during the first `feature-dev` refinement; do not infer remote authorization.
- Before `feature-dev`, `specs/ROADMAP.md` owns only initial `DRAFT/NEXT/BLOCKED`. Once a work item is bound, that work item is the writable work-status authority and Roadmap is a synchronized projection.
- A remote authority must be writable with explicit authorization before claiming a transition; otherwise adopt an explicit local work item or stop without changing status.
- Delivery mode: `TBD`. Select PR/MR or an explicit no-PR Delivery Record before implementation delivery.
- Remote Issue, commit, push, PR/MR, merge, release, and close actions each require separate explicit user authorization.

## Complete Feature Workflow

```text
Macro Design
-> Feature DRAFT Spec
-> Feature Selected (NEXT)
-> Issue or Local Work Item Opened and Linked to Spec
-> Spec Clarification and Refinement
-> SPEC READY
-> if UI:
     UX Refinement
     -> UI State Design
     -> Frontend / Backend Contract
     -> UI READY
-> Acceptance Test Design
-> TEST DESIGN READY
-> Implementation Plan
-> Tasks
-> Coding
-> Testing
-> Review
-> Documentation Sync
-> PR/MR or the explicitly adopted no-PR Delivery Record
-> DONE
```

- Do not start Coding before the Feature's applicable Gates pass.
- Every Gate record must bind the artifact revision it validated. Spec behavior changes invalidate `SPEC READY` and downstream UI/Test/Plan; UI changes invalidate `UI READY` and Test/Plan; Test Design changes invalidate `TEST DESIGN READY` and Plan. Resume only after every stale Gate is revalidated.
- Critical requirements must have observable Acceptance Criteria and planned evidence.
- Implementation Plan defines how to build only the current Feature; it must not become global architecture by accident.

## UI/UX Long-term Rules

1. UX precedes UI; determine user goal and flow before visual detail.
2. A Feature must design more than the Happy Path.
3. Treat Loading, Empty, Error, Success, Waiting, Active, Partial Failure, Stale, Superseded, Permission Denied, Quota, and Provider Failure as explicit states where applicable.
4. Put teacher decisions in structured state. Chat may explain and ask, but it is not the only decision record.
5. Preserve valid work and show the exact recovery path for long-running operations.
6. Use progressive disclosure: teacher-readable evidence first, technical trace detail on demand.
7. Prefer existing components and project patterns and follow the Design System before extending it.
8. A Feature may not introduce an independent visual language or a default library theme.
9. Map API error classes to explicit user-visible behavior and recovery.
10. Design around user decisions and content relationships, not data fields alone.
11. Meet documented WCAG 2.2 AA requirements for core flows, including keyboard, focus, semantics, contrast, labels, errors, and reduced motion.
12. Preserve full desktop behavior and the canonical reduced small-screen experience documented in `docs/UX.md`.
13. If a UI change affects shared tokens or components, update UI/Design System docs and affected tests.

## Design System Rules

- Reuse semantic tokens and components defined in `docs/DESIGN_SYSTEM.md`.
- Extend the system only when an explicit cross-Feature need cannot be met by composition or an existing variant.
- Document shared variants and states; do not hide them as Feature-local CSS.
- Preserve or replace the verified accessibility behavior of any Headless primitive.
- Review visual, interaction, accessibility, responsive, and regression impact before changing shared foundations.
- Do not use cartoon classroom motifs, robot imagery, oversized generic card grids, or arbitrary token values as substitutes for the modern curriculum-design-desk direction.

## Design Change Policy

Design may change, but never through an undocumented code-only shortcut.

```text
Discover problem
-> classify Requirement / Design / Implementation
-> analyze impact
-> assign L1 / L2 / L3
-> identify affected artifacts
-> update Spec / Design and Acceptance Criteria
-> update UX/UI and Test Design when applicable
-> change Code and Tests
-> Verify
-> Review
-> sync work item / delivery record
```

### L1: Feature-local

Use when only the current Feature changes. Update the current Spec, Acceptance Criteria/Test Design, and only the necessary API, Database, or UI documentation.

### L2: Cross-Feature

Use when multiple Features or a shared contract change. Update related Specs, API, Database, UX/UI, Design System if relevant, Roadmap, Tests, and Architecture only where affected.

### L3: Architectural

Use for changes to module boundaries, major technology choices, Source of Truth, messaging, cache, authentication, database strategy, frontend architecture, global navigation, Design System core, API style, trace ownership, or consistency model. Update every truly affected project document, related Specs, AGENTS, and tests; create or update an ADR for every newly confirmed L3 decision and move it to `Accepted` before Coding resumes.

Code must not remain ahead of its controlling documentation. Do not update unaffected files merely to make a change look comprehensive.

## Artifact Relationships

- Spec is the Source of Truth for what makes a Feature correct.
- Issue or explicit local work item tracks where work is, who owns it, and what blocks it. It links to the Spec and must not copy the Spec.
- Task / Sub-Issue records concrete implementation steps when coordination needs them.
- PR/MR or the explicitly adopted no-PR Delivery Record explains what code changed, links the work item and Spec, includes verification evidence, and reports documentation sync.
- ADR explains why a significant architecture or technology decision was made; it does not track implementation progress.

## Documentation Rules

- `README.md` is the quick entry, not the full design.
- `docs/PRODUCT.md` owns product intent, Scope, and separate technical/product success claims.
- `docs/ARCHITECTURE.md` owns system boundaries and collaboration.
- `docs/DATABASE.md` and `docs/API.md` own project-level data and interface conventions; concrete Feature details evolve with Specs.
- `docs/FRONTEND.md`, `docs/UX.md`, `docs/UI.md`, and `docs/DESIGN_SYSTEM.md` own engineering, flow, interface, and shared visual responsibilities respectively.
- `docs/TESTING.md` owns project testing strategy; Feature Test Design owns Feature scenarios.
- Update only affected documents, but complete Documentation Sync before DONE.

## Repeated Pitfalls

- Do not report technical portfolio completion as teacher-product validation; both statuses must remain visible.
- Do not make Redis, Celery, chat history, generated output, or a model response authoritative over PostgreSQL versions and teacher confirmation.
- Do not turn retry into a new model-cost run or allow an old run to publish over a newer version.
- Do not retain private content in browser storage, generic infrastructure logs, cross-user evaluation sets, or model-training data.
- Do not broaden full-unit scope, Multi-Agent behavior, authentication, integrations, or UI platforms without the required Design Change review.

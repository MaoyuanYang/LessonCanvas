# LessonCanvas

LessonCanvas is a portfolio-first Agent application for individual mainland China senior-high English teachers. It turns teacher-owned goals and source materials into a versioned unit blueprint, lesson plans, editable slide decks, exercises with answers, and an alignment review while exposing the evidence, workflow state, evaluation, and recovery behavior behind the result.

## Core Capabilities

- Conduct a stateful requirements interview and require teacher confirmation of the resulting brief.
- Ground planning and generation in private teacher materials and controlled official sources.
- Orchestrate specialized Agents through an explicit, human-gated workflow.
- Generate a complete unit package as editable DOCX and PPTX artifacts.
- Trace goals through plans, lesson artifacts, exercises, and alignment findings.
- Preserve complete user-owned run traces and recover long-running work from safe checkpoints.
- Evaluate technical behavior and teacher-facing content as separate, honest outcomes.

## Tech Stack

| Area | Choice | Status | Notes |
| --- | --- | --- | --- |
| Web | Next.js, React, TypeScript | `CONFIRMED` | Desktop-first workspace with a reduced small-screen experience |
| API | Python, FastAPI, REST, SSE | `CONFIRMED` | HTTP commands and queries; streamed long-task progress |
| Agent orchestration | LangGraph | `CONFIRMED` | Explicit state, human gates, specialist workflows, and checkpoints |
| Background execution | Celery and Redis | `CONFIRMED` | Queueing and retries only; business state remains in PostgreSQL |
| Data | PostgreSQL and pgvector | `CONFIRMED` | System of record for business state, versions, retrieval, and runs |
| Files | S3-compatible object storage | `CONFIRMED` | Private uploads and generated DOCX/PPTX artifacts |
| Identity | Managed identity service | `CONFIRMED` | The application owns authorization, not password security |
| Model | One hosted model behind a thin adapter | `CONFIRMED` | Provider selection remains open until the Agent runtime Feature |

## Current Stage

- Macro design: `MACRO DESIGN READY` (project-level direction can be documented and mapped; no Feature is ready for Coding)
- Project documentation: macro baseline and shallow DRAFT Specs generated
- Feature planning: `F001 Grounded Confirmed Brief` is the sole `NEXT`; every Spec remains `DRAFT`
- Business implementation: not started

### Confirmed NEXT

- Feature: `F001 Grounded Confirmed Brief`
- Selection: confirmed by `YMY / Project Owner`
- Handoff: ready for `feature-dev` refinement
- Constraint: `NEXT` does not mean `SPEC READY`, `UI READY`, `TEST DESIGN READY`, or permission to Code

## Start

```text
Not yet established: no application scaffold or business implementation exists.
```

## Build

```text
Not yet established: no build toolchain has been created.
```

## Test

```text
Not yet established: no executable test suite has been created.
```

## Documentation

- Product: `docs/PRODUCT.md`
- Architecture: `docs/ARCHITECTURE.md`
- Data: `docs/DATABASE.md`
- API: `docs/API.md`
- Frontend architecture: `docs/FRONTEND.md`
- UX: `docs/UX.md`
- UI rules: `docs/UI.md`
- Design System: `docs/DESIGN_SYSTEM.md`
- Testing: `docs/TESTING.md`
- Architecture decisions: `docs/adr/README.md`
- Feature roadmap: `specs/ROADMAP.md`
- AI development rules: `AGENTS.md`

## Decision Status

- `[CONFIRMED]` means a fact was evidenced or a decision was approved by `YMY / Project Owner`.
- `[RECOMMENDED]` means a reversible default with a reason and revisit trigger.
- `[UNKNOWN, NON_BLOCKING]` means an unresolved item that cannot change the approved macro boundary and states when it will be resolved.

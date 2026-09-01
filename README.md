# LessonCanvas

LessonCanvas is a portfolio-first Agent application for individual mainland China senior-high English teachers. It turns teacher-owned goals and source materials into a versioned unit blueprint, lesson plans, editable slide decks, exercises with answers, and an alignment review while exposing the evidence, workflow state, evaluation, and recovery behavior behind the result.

## Core Capabilities

- Conduct a stateful requirements interview and require teacher confirmation of the resulting brief.
- Ground planning and generation in private teacher materials and controlled official sources.
- Orchestrate specialized Agents through an explicit, human-gated workflow.
- Generate a complete unit package as editable DOCX and PPTX artifacts.
- Trace goals through plans, lesson artifacts, exercises, and alignment findings.
- Preserve complete user-owned run traces and recover long-running work from safe checkpoints.
- Stream interview and generation narration token by token while preserving complete traces.
- Remember teacher-confirmed preferences as workspace-scoped, deletable memory.
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
| Tool protocol | MCP | `CONFIRMED` | External source consumption and internal tool definitions; no public server |

## Current Stage

- Macro design: `MACRO DESIGN READY`
- Delivered features: `F001` grounded confirmed brief, `F002` confirmed unit blueprint, `F003` recoverable unit lesson plans, `F004` editable lesson slide decks, `F005` lesson exercises and answers, `F006` layered run evidence, `F007` versioned targeted regeneration, `F008` alignment review and delivery (all `DONE`; see `specs/ROADMAP.md`)
- Next actionable: `F008 Alignment Review and Delivery` refinement (see `specs/ROADMAP.md`)
- Application scaffold: monorepo with `apps/web` (Next.js) and `apps/backend` (FastAPI + Celery) established; infrastructure via `infra/docker-compose.yml`

## Start

```text
docker compose -f infra/docker-compose.yml up -d
```

Starts PostgreSQL+pgvector, Redis, and MinIO with healthchecks.

## Build

```text
# Backend (Python 3.12, uv)
cd apps/backend
uv sync --group dev
uv run uvicorn lessoncanvas.main:app --reload        # API on :8000, GET /health

# Frontend (Node 24, pnpm via corepack)
corepack pnpm install
corepack pnpm web:dev                                # Web on :3000
corepack pnpm web:build
```

## Test

```text
cd apps/backend
uv run pytest
uv run ruff check src tests migrations

corepack pnpm web:test
corepack pnpm web:lint
corepack pnpm web:typecheck
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

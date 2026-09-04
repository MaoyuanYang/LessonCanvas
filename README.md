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
| Identity | Application-issued anonymous workspace tokens (ADR-0006; no login in Phase 1) | `CONFIRMED` | The application owns authorization and issues per-browser workspace tokens; no password storage |
| Model | One hosted model behind a thin adapter | `CONFIRMED` | Provider selection remains open until the Agent runtime Feature |
| Embeddings | Local in-process model behind a thin adapter (ADR-0007) | `CONFIRMED` | fastembed + bge-small-zh-v1.5; weights baked into the deployed image; semantic source retrieval (F014) with chunk-level citations |
| Model tool calling | Bounded, traced specialist tool loop (F015) | `CONFIRMED` | Whitelisted MCP-compatible tools self-requested by the planning drafting specialist; refusals, caps, deterministic fallback, and per-round cost fully traced; the no-tool orchestration path remains one setting away (`tool_loop_mode`) |
| Specialist division of labor | Source-analysis, activity-design, and quality-review specialists (F016) | `CONFIRMED` | Structured per-source analyses as labeled subordinate context; plans run design→write→review and decks/exercises write→review with one severity-gated revise round; every stage traces its own role label, latency, tokens, and estimated cost under formula-based per-run caps |
| Tool protocol | MCP | `CONFIRMED` | External source consumption and internal tool definitions; no public server |

## Current Stage

- Macro design: `MACRO DESIGN READY`
- Delivered features: all thirteen Phase-1 Features `F001`–`F013` are `DONE` (grounded confirmed brief, confirmed unit blueprint, recoverable lesson plans, editable slide decks, exercises and answers, layered run evidence, versioned targeted regeneration, alignment review and delivery, technical portfolio evaluation, teacher product validation, public multi-account guardrails, deployed portfolio proof, teacher memory; see `specs/ROADMAP.md`)
- Phase-1 close-out: holistic review and full-stack re-verification recorded in `specs/PHASE1-retrospective.md` (2026-09-03)
- Next actionable: none remaining in the Phase-1 Feature Map; sole named follow-up candidate is the public cloud/region/internet exposure deployment Feature (F012 D1 residual)
- Application scaffold: monorepo with `apps/web` (Next.js) and `apps/backend` (FastAPI + Celery) established; infrastructure via `infra/docker-compose.yml`

## Start

```text
docker compose -f infra/docker-compose.yml up -d
```

Starts PostgreSQL+pgvector, Redis, and MinIO with healthchecks.

## Deployed Portfolio Stack (F012)

```text
cp infra/deploy.env.example infra/deploy.env     # fill real values (git-ignored)
infra/scripts/deploy.sh                          # build -> migrate -> start -> smoke
LESSONCANVAS_MODEL_ADAPTER=fake LESSONCANVAS_TASKS_EAGER=true \
  docker compose -f infra/docker-compose.yml --profile app exec api \
  python scripts/seed_sample.py                  # idempotent synthetic sample
infra/scripts/teardown.sh                        # full teardown to clean state
```

Runs the complete stack (Web, API, Celery Worker, PostgreSQL/pgvector, Redis, MinIO) in containers, reachable on the LAN with no login — each browser gets an anonymous workspace token automatically (ADR-0006; see `specs/F012-deployed-portfolio-proof/`). The API runs a single process by design (SSE registry constraint).

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

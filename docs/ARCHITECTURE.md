# Architecture

## Goals and Constraints

- [CONFIRMED] Preserve teacher-owned intent, source evidence, version history, and complete Agent traces across long-running work.
- [CONFIRMED] Demonstrate explicit specialist-Agent orchestration without treating autonomous Agent conversation as a design goal.
- [CONFIRMED] Recover partial work and retries without duplicate runs, duplicate model cost, or stale results overwriting newer versions.
- [CONFIRMED] Isolate every teacher's content and delete user content, artifacts, and traces with the owning project or account.
- [CONFIRMED] Use a modular monolith and asynchronous Worker rather than microservices.
- [RECOMMENDED] Keep vendor integrations behind narrow boundaries. Reason: the provider choices remain open while the product flow is stable; revisit when a second provider is justified by availability or measured quality.

## Overall Architecture

The system is a modular monolith with a separately running asynchronous Worker. The Web application owns teacher interaction. FastAPI exposes authenticated commands, queries, and progress streams. LangGraph owns semantic Agent state and human interruption points. Celery and Redis deliver background execution; PostgreSQL remains the authoritative business and run-state store.

```text
Teacher browser
    |
    v
Next.js Web application
    |
    | REST commands/queries + SSE progress
    v
FastAPI modular monolith ---------------- Managed identity
    |        |        |
    |        |        +------------------ Controlled official sources
    |        +--------------------------- PostgreSQL + pgvector
    |                                     S3-compatible object storage
    |
    +-- Celery task dispatch --> Redis --> Async Worker
                                         |
                                         +-- LangGraph workflow/checkpoints
                                         +-- Hosted model adapter
                                         +-- Local embedding adapter (F014)
                                         +-- Document generation tools
```

## Tech Stack

| Concern | Choice | Status | Rationale / constraint |
| --- | --- | --- | --- |
| Architecture | Modular monolith plus asynchronous Worker | `CONFIRMED` | Clear boundaries without distributed-service overhead |
| Backend | Python and FastAPI | `CONFIRMED` | Fits the Agent/document ecosystem and explicit API boundary |
| Agent workflow | LangGraph | `CONFIRMED` | Stateful graphs, human gates, specialist composition, and checkpoints |
| Task execution | Celery and Redis | `CONFIRMED` | Queueing, retry, and concurrency for complete-unit generation |
| Database | PostgreSQL with pgvector | `CONFIRMED` | One transactional system of record plus bounded retrieval support |
| File storage | S3-compatible object storage | `CONFIRMED` | Private source and generated binary lifecycle |
| Frontend | Next.js, React, TypeScript | `CONFIRMED` | Public deployability and a rich project workspace |
| Communication | REST and SSE | `CONFIRMED` | Request/response commands plus one-way long-task progress |
| Identity | Managed identity provider | `CONFIRMED` | Avoids owning password security while preserving app authorization |
| Model | One hosted model through a thin adapter | `CONFIRMED` | Limits the evaluation matrix and avoids premature routing |
| Tool protocol | MCP | `CONFIRMED` | External official-source consumption and internal tool definitions; no public server (ADR-0004) |

## Modules and Responsibilities

| Module / boundary | Responsibility | Owns | Must not own |
| --- | --- | --- | --- |
| Identity and Workspace | Map external identity to private teacher workspaces and enforce ownership | Workspace membership, access decisions, quotas | Password storage, planning content, Agent workflow |
| Sources and Grounding | Accept, validate, parse, retrieve, and cite allowed sources, consuming controlled official sources through MCP | Source lifecycle, extraction status, retrieval evidence | Teacher intent, artifact completion |
| Discovery and Planning | Identify requirement gaps and create teacher-confirmable intent | Requirements brief and unit-blueprint versions | Binary storage, task transport, product-validation claims |
| Artifact Production | Generate lesson plans, decks, exercises, and answers from an immutable approved version using MCP-defined tools | Derived artifact versions and generation outcomes | Source ownership, final validation status |
| Alignment and Evaluation | Trace objectives through plans and artifacts and record findings and evidence | Alignment findings, technical package-validation status, product-validation status, evaluation results | Silent mutation of owning content or intent |
| Run Orchestration and Observability | Coordinate specialists, human gates, checkpoints, idempotency, progress, cost, and traces | Run lifecycle and complete run trace | Domain truth outside a bound intent version |
| Export and Delivery | Package authorized private artifacts for download or printable review | Export lifecycle and authorized delivery | In-browser Office-class editing |
| Teacher Memory and Preferences | Propose, confirm, apply, and manage workspace-scoped memory | Confirmed memory records and applied-context references | Confirmed intent versions, cross-user data, training use |

## Dependencies

- `Identity and Workspace -> managed identity`: trust authenticated subject identity, then apply application-owned workspace authorization.
- `Sources and Grounding -> workspace authorization, object storage, PostgreSQL/pgvector, and controlled official sources`: process only owner-authorized material and keep retrieval inside the approved evidence boundary. F014: the thin embedding adapter (`adapters/embedding.py`, ADR-0007) and the vector-retrieval service live here; planning and all three generation families consume top-k retrieval per item, and retrieved text always travels as labeled user payload, never prompt authority.
- `Discovery and Planning -> Sources and Grounding, Run Orchestration`: consume source evidence and participate in the governed workflow without owning source files or task delivery.
- `Artifact Production -> approved brief and blueprint, Sources and Grounding, Run Orchestration, generation tools`: generate only against an immutable confirmed version and cited evidence.
- `Alignment and Evaluation -> sources, approved intent, artifacts, and runs`: compare evidence and own validation outcomes but never silently rewrite the owning concepts.
- `Run Orchestration -> all Agent-capable modules, PostgreSQL, and Celery`: control sequence and state without making modules or task transport a competing workflow truth.
- `Export and Delivery -> workspace authorization, artifact versions, and object storage`: never expose a storage location without authorization.
- `Teacher Memory and Preferences -> workspace authorization, PostgreSQL, and Discovery and Planning context`: propose from confirmed outcomes, persist only teacher-confirmed records, and supply subordinate context.
- `Discovery and Planning / Artifact Production -> Teacher Memory (context input only)` [F013]: the discovery, planning, and generation graphs read the snapshot-once effective set as a labeled, capped data payload; memory never enters system prompts or gains instruction framing, and the bound confirmed version always wins (deterministic `language_mode` conflict check).
- `Sources and Grounding -> MCP official-source servers`: consume curriculum evidence through the controlled protocol boundary while treating server content and metadata as untrusted.
- `Artifact Production -> MCP tool definitions`: register generation and validation tools once and consume the same definitions from the workflow.

## Main Data and Request Flows

1. The Web application authenticates a teacher, creates a private project, and uploads allowed source material through authorized APIs.
2. The discovery workflow retrieves evidence, asks only material gap questions, and records a structured brief for explicit teacher confirmation.
3. The planning workflow creates a unit blueprint and pauses for the second teacher confirmation gate.
4. Confirmation creates an immutable input version and an idempotent asynchronous run; Celery delivers work while LangGraph writes semantic checkpoints to PostgreSQL.
5. Specialist steps create versioned artifacts. Alignment and evaluation consume the same bound version and report findings.
6. SSE exposes user-safe progress. The teacher may inspect a layered trace, resolve findings, revise upstream intent, or request targeted regeneration.
7. A new confirmed upstream version supersedes the old active run at a safe checkpoint; old results remain historical and cannot overwrite the new version.

## Sync / Async Strategy

- Synchronous: identity checks, workspace commands, source metadata, structured edits, confirmations, queries, and task creation acknowledgements.
- Asynchronous: source parsing when expensive, embeddings, complete-unit planning/generation, document rendering, alignment review, and evaluation.
- Failure / retry direction: transport retries resume the same idempotent run. Domain-invalid input is not retried. Provider and transient failures use bounded retry and preserve the last safe checkpoint. New versions supersede old runs rather than mutating them.

## Consistency and Transactions

- Source of Truth: PostgreSQL for business versions and run state; object storage for referenced binaries; the managed identity service for external identity.
- Strong consistency required for: owner checks, confirmation-to-version transitions, quota reservation, idempotent run creation, current-version selection, and completion status.
- Eventual consistency acceptable for: embeddings, generated files, progress projections, evaluation, and cleanup, provided state remains visible and reconciliation is safe.

## Cache and Messaging

- Cache: no authoritative application cache is planned. Any future cache is derived and must define invalidation and ownership before adoption.
- Messaging: Redis is the Celery broker for task delivery, not a domain event store or Source of Truth. No general event bus is planned for Phase 1.

## External Services

| Service | Purpose | Failure impact | Boundary |
| --- | --- | --- | --- |
| Hosted model provider | Requirements analysis, planning, generation, and supported evaluation | The affected step pauses or fails visibly; completed state remains recoverable | One provider through an application adapter; no silent fallback |
| Local embedding model (ADR-0007) | Chunk/query embeddings for semantic source retrieval (F014) | Chunks persist an explicit `embedding_failed` state and retrieval excludes them with disclosure; generation proceeds honestly ungrounded | In-process fastembed + bge-small-zh-v1.5 with weights baked into the image; no network service, no external data flow |
| Managed identity provider | Registration, login, verification, and identity sessions | New login or session refresh may be unavailable | The application still owns workspace authorization and deletion orchestration |
| S3-compatible storage | Private uploads and generated files | Upload, generation, or download pauses; database state must not claim a missing file is ready | Access only through authorized application flows or scoped signed delivery |
| Controlled official sources | Curriculum-grounding evidence | Missing evidence triggers a question, source warning, or blocked generation | Only configured public authoritative sources; no arbitrary Web search |
| MCP official-source servers | Controlled curriculum evidence via standardized protocol | Missing or failing evidence triggers questions or blocked generation like any source | Application owns authorization; server content and tool metadata remain untrusted |

## Security and Observability

- Authentication / authorization direction: managed authentication, application-owned object-level authorization, strict teacher-workspace isolation, and application-enforced quotas and rate limits, with managed infrastructure controls as defense in depth.
- Sensitive data boundary: reject identifiable student data and real student answers or grades; validate files, source rights acknowledgement, and private object access.
- Logging, metrics and tracing direction: retain complete run traces inside the owning workspace, including prompts and outputs needed for technical evidence. Do not reuse across users or for training. Delete traces with the project or account. Operational access is disclosed, controlled, and audited.
- Injection boundary: source content is untrusted data. It cannot grant tools, change system policy, reveal other workspaces, or bypass source and completion gates. MCP server/tool metadata and teacher memory content follow the same untrusted-input rule.

## Deployment Direction

Local and CI environments must be reproducible once scaffolding exists. The public demo will deploy the Next.js Web application, FastAPI application, Worker, PostgreSQL, Redis, and object storage through managed or container-capable services. Exact providers and topology remain open until deployment refinement; no Kubernetes or multi-region design is justified.

[PARTIALLY RESOLVED, 2026-09-02] F012 selects local full-stack containerization as the deployed portfolio environment (`YMY / Project Owner`, F012 Spec D1): `infra/docker-compose.yml` runs the complete stack behind the `app` profile (single-process Web/API, Celery Worker, PostgreSQL/pgvector, Redis, MinIO) reached over the LAN with application-issued anonymous workspace tokens and no login (ADR-0006); cloud/region deployment stays a follow-up Feature. Deployment-topology constraints: the API runs exactly one process because the per-workspace SSE stream cap uses an in-process registry (F011 M-2) — any scale-out must re-verify that assumption first; the LangGraph Postgres checkpointer is verified restart-safe and cross-process persistent (F012 TS-011). Public cloud provider selection, region, domain, and TLS remain open for the follow-up deployment Feature.

## Architectural Risks and Revisit Triggers

- Multi-Agent is retained for portfolio coverage even without measured superiority. Revisit before production positioning or when cost and maintenance become primary.
- Full-unit, every-lesson generation has high latency, cost, and evaluation surface. Reopen Scope only through `YMY / Project Owner` if it prevents end-to-end evidence.
- Complete trace retention increases private-content exposure. Revisit if regulatory, provider, or operational constraints prevent user-scoped deletion and access control.
- Celery and LangGraph can overlap if responsibilities drift. Revisit if task transport begins to own semantic state or the graph begins to replace reliable task delivery.
- MCP framework coupling. Revisit if the ecosystem or LangGraph integration destabilizes the tool boundary, or if reviewer evidence justifies exposing a read-only evidence server.
- Applied memory biasing generation. Revisit if evaluation shows confirmed memory harms comparability or teacher outcomes. [RESOLVED, 2026-09-01] F009 records a memory-state snapshot on every evaluation pass , so compared passes are memory-comparable by construction (ADR-0005). [UPDATED, 2026-09-02] F013 supplies the structured revision-list snapshot (`memory_state` + `record_ids` + `record_hashes`); harness workspaces stay empty by construction and the snapshot joins the comparability signature (F013 D6).
- [PARTIALLY RESOLVED, 2026-08-24; REVISED 2026-09-02] F001 providers selected: Clerk (identity), DeepSeek (model), local MinIO (object storage). ADR-0006 supersedes the identity item: Phase 1 has no managed identity — the application issues anonymous workspace tokens (`POST /auth/guest-token`) with no login/logout. DeepSeek and MinIO remain. Cloud/region topology stays a follow-up deployment Feature.

## Related ADRs

- `docs/adr/0001-portfolio-first-multi-agent-architecture.md`
- `docs/adr/0002-stateful-agent-and-async-execution.md`
- `docs/adr/0003-user-owned-complete-run-traces.md`
- `docs/adr/0004-mcp-tool-and-source-protocol.md`
- `docs/adr/0005-workspace-scoped-teacher-memory.md`

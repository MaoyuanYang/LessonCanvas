# Use Stateful Agent and Asynchronous Execution for the Phase-1 Application

- Status: `Accepted`
- Date: 2026-08-21
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: None

## Context

Complete-unit generation is long-running, expensive, and partially recoverable. The workflow contains two human confirmation gates, specialist steps, external model calls, document rendering, alignment review, retries, supersession, and user-visible progress. A process restart or duplicate request must not restart all work or create competing truth.

The project also needs a recognizable Agent state model and a public multi-account Web application without introducing microservices, self-built password security, multiple model providers, or competing workflow authorities.

## Decision

Use a modular monolith with a Next.js/React/TypeScript Web application, a FastAPI REST API with SSE progress, and a separately running asynchronous Worker. Use managed identity for authentication while the application owns workspace authorization. Use PostgreSQL with pgvector for transactional business, retrieval, run, and checkpoint truth and S3-compatible object storage for private binaries. Use one hosted model behind a thin adapter and do not add model routing in Phase 1.

LangGraph owns semantic workflow state, specialist sequencing, human interruption points, and recoverable checkpoints. PostgreSQL persists authoritative business versions, run state, and checkpoints. Celery and Redis own task delivery, bounded retry, and Worker concurrency; they do not own business truth. FastAPI exposes REST commands and queries plus SSE progress to the Next.js client.

Each run binds to an immutable confirmed brief/blueprint version. Same-version duplicate submissions return the existing run. Worker retries resume that run. A newly confirmed version supersedes the older active run at a safe checkpoint, retains old history, and prevents stale publication.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Process-local background tasks | Minimal infrastructure | Cannot meet restart, retry, concurrency, and recovery requirements |
| Temporal plus an Agent framework | Strong durable execution | Overlaps workflow responsibilities and increases learning and deployment cost for current scale |
| Database-only custom queue | Fewer infrastructure products | Requires rebuilding leases, delivery, retry, concurrency, and monitoring behavior |
| Microservices per Agent or capability | Independent deployment boundaries | No scale or team evidence justifies distributed-service failure modes |
| Redis as the run Source of Truth | Fast access | Conflicts with transactional versions, deletion, and durable audit requirements |
| Next.js-only full stack or Python-rendered pages | Fewer runtime boundaries | Weakens the confirmed Python Agent/API and rich TypeScript workspace separation |
| GraphQL, WebSocket-only, or polling APIs | Flexible queries or familiar progress mechanisms | Current commands and one-way progress do not justify the additional contract or connection complexity |
| Self-built password authentication | Full implementation control | Adds credential-security scope unrelated to the Agent portfolio objective |
| Separate vector database | Independent retrieval scaling | No Phase-1 scale or isolation evidence justifies another Source of Truth or service |
| Multiple models or silent provider fallback | Potential task specialization and availability | Multiplies evaluation and failure semantics and hides reproducibility |

## Reasoning

The split gives each mechanism one job: managed identity establishes identity; the application owns authorization; PostgreSQL owns relational, retrieval, run, and checkpoint truth; object storage owns referenced binaries; LangGraph owns Agent semantics; Celery/Redis owns reliable task delivery; REST/SSE owns client communication; and the single model adapter owns provider access. It demonstrates production-minded behavior without adopting a distributed architecture unsupported by project scale.

## Consequences

- Positive: semantic checkpoints and transport retries can be tested independently.
- Positive: human gates, partial recovery, and version supersession are explicit.
- Positive: the Web, API, data, file, identity, and model boundaries have one documented Phase-1 direction before Feature implementation.
- Negative / tradeoff: Celery, Redis, LangGraph, and PostgreSQL create a non-trivial local and cloud environment.
- Negative / tradeoff: Next.js, FastAPI, managed identity, object storage, and a hosted model add integration and public-deployment surface.
- Negative / tradeoff: responsibility drift could produce duplicate state or inconsistent recovery.
- Follow-up: reject any implementation that stores authoritative run state only in Celery/Redis, duplicates semantic workflow truth outside LangGraph/PostgreSQL, or introduces another provider/service without the documented revisit evidence.

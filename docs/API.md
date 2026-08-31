# API

## Scope and Consumers

This document governs the project-level HTTP and progress-stream conventions between the Next.js Web application and FastAPI. Concrete business endpoints and payloads are refined only by the owning Feature Specs.

## Style

- Protocol / style: REST over HTTPS for commands and queries; Server-Sent Events for one-way task progress and token-level model responses
- Status: `CONFIRMED`
- Rationale: the user flow is command/query oriented and needs resumable progress, not a general bidirectional socket protocol.

## Global Conventions

- Base URL and versioning: [RECOMMENDED] use an explicit API namespace and version only when a public contract exists. Confirm the exact prefix in the first API Feature.
- Method semantics: [CONFIRMED] safe reads do not mutate state; creation, confirmation, revision, deletion, and retry use methods with matching HTTP semantics.
- Content types / serialization: [CONFIRMED] JSON for structured API data; authorized multipart or direct-upload flows for binaries; SSE for progress events.
- IDs: [CONFIRMED] opaque strings with no embedded user or mutable business meaning.
- Time: [CONFIRMED] ISO 8601 instants normalized to UTC at the interface boundary.
- Pagination: [RECOMMENDED] use cursor-oriented pagination for runs, projects, traces, and artifacts where lists can grow; bounded lists may omit it. Revisit with measured list behavior in the owning Feature.

## Streaming

- Transport: [CONFIRMED] SSE remains the one-way streaming transport for task progress and token-level model responses.
- Event binding: [CONFIRMED] streaming events carry owner-authorized run/correlation context; incremental token events never create new model work.
- Reconnect: [CONFIRMED] reconnects resume from authoritative server state; replay must not duplicate generation or mutate confirmed state.
- Stop: [CONFIRMED] a teacher may stop a streamed response; stopping narration is not run cancellation unless explicitly requested.
- Trace integrity: [CONFIRMED] streamed content is not a separate corpus; the complete response is captured in the workspace's full run trace.
- Idle keepalive: [CONFIRMED, F006 2026-08-31] long-running event streams (generation, decks, exercises, evidence narration) emit SSE comment frames (`: keepalive`) after every silent interval so idle-timeout intermediaries cannot drop the connection mid-run; comment frames carry no id/data and are ignored by replay.
- Exact event envelopes and interruption contracts wait for Feature refinement.

## Authentication and Authorization

- Authentication: [CONFIRMED] validate managed-provider sessions or tokens at the application boundary; do not accept identity claims from client-provided business data.
- Authorization: [CONFIRMED] every project, source, run, trace, evaluation, artifact, and download is authorized by recorded workspace ownership.
- Service-to-service access: [CONFIRMED] internal Worker calls use deployment-controlled identity and still operate on explicit project/run scope; internal status does not bypass data ownership.
- Quotas and rate limits: [CONFIRMED] the application enforces user and operation policy before expensive work; gateway/provider controls are defense in depth and never the quota Source of Truth.

## Response and Error Model

- Success response principle: [CONFIRMED] return the requested resource or accepted operation state with its authoritative version and trace/correlation reference where relevant.
- Error structure: [CONFIRMED] use a stable machine-readable code, safe human message, correlation identifier, and optional field or recovery guidance; never leak prompts, storage locations, provider secrets, or another workspace.
- Error taxonomy: [CONFIRMED] the canonical project-level classes are requirement/input, authentication, authorization/ownership/not-found, stale-version/conflict, source/file-policy, quota/rate-limit, provider/transient, partial-execution/recovery, and unexpected-system errors. Concrete codes belong to Feature contracts.
- Correlation / trace ID: [CONFIRMED] every long task and externally visible failure links to an owner-authorized run or correlation identifier.

## Idempotency, Retry and Concurrency

- Idempotency required for: [CONFIRMED] long-run creation, confirmation-triggered generation, retries, export creation where duplicate model cost or artifacts are possible, and deletion requests.
- Retry policy: [CONFIRMED] the client may retry only documented idempotent operations. Celery retries transient delivery or provider failures against the same run and checkpoint. Domain-invalid work requires teacher action rather than automatic retry.
- Conflict behavior: [CONFIRMED] same-version duplicate generation returns the existing run. A stale edit or confirmation returns an explicit version conflict. A newly confirmed version safely supersedes the older active run and prevents old publication over new state.

## Compatibility and Evolution

The Web application and API evolve in the same repository during Phase 1, but shared contracts remain explicit and tested. Breaking a consumed contract requires an L2/L3 impact review, coordinated frontend change, updated tests, and versioning only when simultaneous compatibility is actually required.

## Feature Contract Rule

Concrete business endpoints, event names, payload fields, and frontend/backend contracts are refined with the owning Feature Spec. Do not predefine the complete API during project initialization.

## Open Items

- [RESOLVED, 2026-08-24] The managed identity token/session integration: Clerk sessions validated at the FastAPI boundary (`YMY / Project Owner`, F001 refinement D1).
- [RESOLVED, 2026-08-29] The SSE resume mechanism and event envelope: PostgreSQL run-event table is authoritative; events carry per-run monotonic ids; reconnect replays from `Last-Event-ID`; replay triggers no model work (`YMY / Project Owner`, F003 refinement D4; implemented in the F003 generation stream).
- [RESOLVED, 2026-08-31] Versioned targeted regeneration API (`YMY / Project Owner`, F007): owner-authorized reads `GET /projects/{id}/impact` (D1-matrix preview of pending drafts vs the confirmed pair; drafts count only when newer than the confirmed version) and `GET /projects/{id}/versions/current-transition` (from/to versions, intent diff, embedded impact, per-lesson x family verdicts with reasons, old/new artifact status). Family starts are transition-aware: runs bind the current pair with an affected-lesson scope fixed at creation, snapshots expose `scope_lesson_indexes` and `retained_artifacts` (prior artifact id + provenance + download), and deck/exercise prerequisites generalize to plan coverage naming uncovered lessons; settled old-pair runs never mask the new pair's start surface.
- [RESOLVED, 2026-08-31] Layered run evidence API (`YMY / Project Owner`, F006): owner-authorized reads under `/projects/{id}/evidence` — run inventory (all five run kinds), per-run teacher summary, and cursor-paginated technical events (stable URL-safe cursors, bounded pages, explicit `未记录` gaps, estimated-cost labeling); explanation narration (`POST .../narrate` + `.../narrate/stream` SSE) is workspace-quota guarded and records its complete text in the trace. The pre-F006 metadata-only `GET /projects/{id}/trace` endpoint is removed (it was never consumed by the Web application).

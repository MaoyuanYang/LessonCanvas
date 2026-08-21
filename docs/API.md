# API

## Scope and Consumers

This document governs the project-level HTTP and progress-stream conventions between the Next.js Web application and FastAPI. Concrete business endpoints and payloads are refined only by the owning Feature Specs.

## Style

- Protocol / style: REST over HTTPS for commands and queries; Server-Sent Events for one-way task progress
- Status: `CONFIRMED`
- Rationale: the user flow is command/query oriented and needs resumable progress, not a general bidirectional socket protocol.

## Global Conventions

- Base URL and versioning: [RECOMMENDED] use an explicit API namespace and version only when a public contract exists. Confirm the exact prefix in the first API Feature.
- Method semantics: [CONFIRMED] safe reads do not mutate state; creation, confirmation, revision, deletion, and retry use methods with matching HTTP semantics.
- Content types / serialization: [CONFIRMED] JSON for structured API data; authorized multipart or direct-upload flows for binaries; SSE for progress events.
- IDs: [CONFIRMED] opaque strings with no embedded user or mutable business meaning.
- Time: [CONFIRMED] ISO 8601 instants normalized to UTC at the interface boundary.
- Pagination: [RECOMMENDED] use cursor-oriented pagination for runs, projects, traces, and artifacts where lists can grow; bounded lists may omit it. Revisit with measured list behavior in the owning Feature.

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

- [UNKNOWN, NON_BLOCKING] The managed identity token/session integration is not selected. Resolve before the identity and workspace Feature reaches `SPEC READY`.
- [UNKNOWN, NON_BLOCKING] The exact SSE resume mechanism and event envelope are not selected. Resolve with the first long-running generation Feature.

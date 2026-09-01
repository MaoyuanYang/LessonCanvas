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
- [RESOLVED, 2026-09-01] Alignment review and delivery API (`YMY / Project Owner`, F008): owner-authorized, model-free reads `GET /projects/{id}/alignment` and `GET /projects/{id}/alignment/report` (deterministic coverage and findings for the current confirmed pair, technical package status, separate not-evaluated product-validation status); reasoned overrides `POST /projects/{id}/alignment/overrides` (disputed conflict-class severe findings only; required reason; version-pair bound; duplicate returns the existing decision) and withdrawal `DELETE /projects/{id}/alignment/overrides/{override_id}`; delivery `POST/GET /projects/{id}/delivery/exports` (labelled draft/validated; validated requires zero unresolved severe findings and names blockers otherwise; idempotent per version pair + label + manifest digest), authorized ZIP download `GET .../exports/{export_id}/download` (byte-identical artifacts + honest metadata.json), and the export-time report snapshot `GET .../exports/{export_id}/report`. Requirement errors carry the `confirmed_pair` gate; a version-pair switch during a build settles the export failed instead of delivering a mixed package.
- [RESOLVED, 2026-09-01] Technical evaluation API (`YMY / Project Owner`, F009): owner-authorized reads under `/projects/{id}/technical-evaluation` — overview (dataset revision, per-unit × per-pass states with `superseded_configuration` marking), idempotent pass creation `POST .../technical-evaluation/runs` (unit + pass index + mode `live|deterministic` + scenario `full_pipeline|fault:<name>`; unique per project + dataset revision + unit + pass + mode + scenario; concurrent duplicates converge on one record and one pipeline execution; mode eligibility is checked against the active adapter before any model spend), per-pass detail `GET .../runs/{evaluation_id}` (blocking criteria with `pass|fail|missing_evidence` outcomes and evidence links; diagnostic metrics carry no outcome), and the report read `GET .../technical-evaluation/report` (per-pass outcomes, comparison availability with precise reasons, set-level outcome that never masks a failed or missing blocking criterion; since F010 the `product_validation_status` field carries the live derived value, never merged with the technical outcome). Dataset governance failures and ineligible modes return requirement errors naming the rule; live-provider unavailability settles the pass `provider_unavailable` with partial evidence retained.
- [RESOLVED, 2026-09-01] Product-validation API (`YMY / Project Owner`, F010): owner-authorized, model-free endpoints under `/projects/{id}/product-validation` — overview `GET /projects/{id}/product-validation` (fixed rubric revision, per-unit assignment states with derived staleness, overall status `not_evaluated|in_progress|not_complete|passed|failed` per the D6 precedence, bounded-conclusion sentence); idempotent assignment creation `POST .../product-validation/assignments` (unit key; fixes dataset revision + confirmed version pair + per-lesson artifact ids/checksums as the immutable package identity, unique per project + unit + package digest; rejects technically incomplete packages naming the per-lesson family gaps; duplicate returns the existing assignment with `created: false`); structured-evidence import `POST .../assignments/{assignment_id}/evidence` (multipart: submission revision label + rubric JSON + the evaluator's original document, required and stored privately; validates the full fixed schema and lists every violating field at once, persists nothing on violation; idempotent per assignment + submission revision, a newer revision supersedes the prior which stays historical; blocked on stale assignments with the supersession reason); honest conclusion `POST .../assignments/{assignment_id}/conclusion` (records `not_complete` with a required reason; terminal states immutable); detail `GET .../assignments/{assignment_id}` (package identity, evidence history with outcomes and capture channel `owner_mediated_import`, fixed rubric-sheet data for the hand-out); owner-authorized original-document download `GET .../assignments/{assignment_id}/evidence/{evidence_id}/document` (private evidence; report surfaces never expose the evaluator reference). The alignment read, alignment report, technical-evaluation report, and delivery report snapshot all carry the same live `product_validation_status` value, always displayed separately from technical status.
- [RESOLVED, 2026-09-01] Public multi-account guardrail API (`YMY / Project Owner`, F011): PostgreSQL-authoritative limits enforced before model spend. Every authenticated route passes the general request-rate guard (fixed 60 s window, 240/min per workspace); run starts, uploads, evidence import, and evidence narration additionally pass the stricter expensive-write window (120/min) — the caps nest, so an expensive request consumes both windows. Upload volume is capped per workspace per UTC day (200 MB across sources and evaluator documents, 429 naming `upload_daily`). Concurrent generation runs are admitted per workspace (2 across plan/deck/exercise combined; superseded runs free their slot; duplicates still converge on the run-identity constraint): rejection is 409 `RUN_ADMISSION` with the active run ids. Concurrent SSE streams are capped per workspace (6; in-process registry, single-process deployment shape). Rejections return 429/409 with `limit`, `limit_value`, and `retry_after_seconds`/`active_run_ids` — never content. New owner reads: `GET /account/usage` (every limit with current consumption and window reset) and `GET /account/audit` (cursor-bounded sensitive-action list: kind + target id + time, never payloads). Artifact/evidence downloads write owner-visible `download.*` audit events. Uploads are content-sniffed against the declared extension/type (magic bytes, truncation-safe UTF-8 probe), size-capped before buffering, decompression-bomb guarded (bounded docx extraction, bounded pdf page count), and filenames with path separators or control characters are rejected. Source delete that fails at object storage settles a visible `delete_failed` state (HTTP 200 body `{deleted: false}`) repairable by re-issued delete; project/account deletion verify completeness (governed tables, checkpoints, both buckets) and stay visibly `deleting`/`purge_failed` with a metadata-only residual ledger until a retry converges them.

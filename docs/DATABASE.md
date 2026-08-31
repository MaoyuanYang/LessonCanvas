# Database

## Scope

This document governs project-level ownership, persistence, versioning, consistency, deletion, and audit direction. It intentionally does not define tables, fields, SQL, or a complete Schema.

## Database Selection

- Choice: PostgreSQL with pgvector, plus S3-compatible object storage for binary content
- Status: `CONFIRMED`
- Rationale and constraints: relational transactions protect ownership, confirmations, versions, quotas, and idempotency; pgvector keeps Phase-1 retrieval in the same governed data boundary; object storage handles source and Office files without making URLs authoritative.

## Sources of Truth

| Data concept | Owning boundary / system | Authority rule |
| --- | --- | --- |
| External user identity | Managed identity provider | Provider subject identity wins for authentication; the application decides workspace authorization |
| Teacher workspace and ownership | Identity and Workspace in PostgreSQL | The recorded owner must authorize every project, run, trace, and file operation |
| Source material | Sources and Grounding metadata plus private object storage | Teacher-owned uploaded content is authoritative as evidence; it cannot silently override confirmed intent |
| Teaching intent | Confirmed requirements-brief and unit-blueprint versions in PostgreSQL | The explicitly confirmed current version wins over chat history and derived output |
| Run state, semantic checkpoints, and complete trace | Run Orchestration in PostgreSQL | A run is bound to one immutable intent version; retries append to or resume that run |
| Generated artifacts | Artifact metadata in PostgreSQL plus private object storage | Artifact identity and status come from PostgreSQL; binary content must match the referenced version |
| Alignment, package validation, and product evaluation | Alignment and Evaluation in PostgreSQL | Status and results describe a particular source, intent, artifact, and run version and cannot silently mutate them |
| Official curriculum evidence | Controlled external source, with application citation/snapshot metadata | The external source remains authoritative; the application records enough evidence to explain its use |
| Teacher memory | Teacher Memory and Preferences in PostgreSQL | Only teacher-confirmed proposals persist; memory is subordinate context and never overrides confirmed intent versions |

## Core Entities and Relationships

| Entity / concept | Business meaning | Key relationships |
| --- | --- | --- |
| Teacher workspace | Private ownership boundary for one authenticated teacher | Contains preparation projects and quotas |
| Preparation project | A teacher's continuing unit-preparation workspace | Owns sources, intent versions, runs, artifacts, findings, and evaluations |
| Source material | Teacher-supplied or controlled official evidence | Referenced by discovery, planning, generation, and citations |
| Requirements brief | Structured, teacher-confirmed teaching needs | Versioned upstream input to the unit blueprint |
| Unit blueprint | Teacher-confirmed unit and lesson intent | Versioned upstream input to all lesson artifacts |
| Run | One idempotent orchestration attempt against an immutable intent version | Owns checkpoints, progress, trace, costs, and step outcomes |
| Artifact set | Derived lesson plans, decks, exercises, answers, and exports | Bound to an intent version and producing run |
| Alignment finding | Evidence-backed coverage, conflict, or gap | References objectives, sources, plans, and artifacts without owning them |
| Evaluation result | Technical or product evidence for a fixed version | Never retroactively changes the evaluated version |
| Teacher memory | Workspace-scoped confirmed preferences applied as subordinate context | Owned by the workspace; referenced by runs as applied context |

## Project-level Conventions

- Naming: [RECOMMENDED] use consistent singular business terms in documentation and conventional snake_case in PostgreSQL. Revisit only if adopted tooling imposes a stronger convention.
- IDs: [CONFIRMED] expose opaque application IDs; do not encode teacher identity or mutable business meaning. Select the concrete ID strategy with the first persistence Feature.
- Time: [CONFIRMED] store instants in UTC and present them in the user's interface context; exact display formatting belongs to the UI Feature.
- Unique constraints: [CONFIRMED] enforce ownership and idempotent run identity at the database boundary. Do not rely on Worker or UI checks alone.
- Indexes: [RECOMMENDED] add indexes from observed query, ownership, lifecycle, and retrieval needs rather than predefining a complete list. Validate before public-demo load testing.

## Transactions and Consistency

- Transaction boundaries: confirmation must atomically create or select the immutable current version. Run creation must atomically enforce owner, quota, current version, and idempotency.
- Concurrency / atomicity risks: duplicate submissions, Worker retries, quota consumption, version supersession, and cleanup must be safe under repeated delivery. A new confirmed version marks the older active run superseded; it stops at a safe checkpoint and cannot publish over the new version.
- Cross-boundary consistency: database state leads object and vector processing. Missing or failed derived data remains visible and repairable; no artifact becomes ready until referenced binary creation is confirmed.

## Delete, Retention and Audit

- Delete strategy: deleting a project or account initiates deletion of its sources, artifacts, complete traces, vectors, confirmed memory records, and owned business records across PostgreSQL and object storage. The UI must expose progress or failure when deletion is not immediate.
- Retention / privacy: full prompts, materials, outputs, and traces persist only inside the owning workspace while that workspace exists. They are not shared across accounts or used for training.
- Audit requirements: owner changes, sensitive access, operator troubleshooting access, quota decisions, deletion, severe-finding overrides, and security-relevant actions require auditable evidence without creating a second content corpus.

## Cache Relationship

Redis is a non-authoritative Celery transport. No business fact, quota balance, current version, or run checkpoint may exist only in Redis. Any future cache must be derived from an authoritative source and define invalidation before adoption.

## Evolution Rules

- Concrete Schema evolves with Feature Specs and migrations.
- A Feature may not silently change Source of Truth, ownership, deletion, or shared conventions.
- L2/L3 changes require impact analysis and documentation sync.
- Retrieval may move to a separate vector service only when measured scale, isolation, or operational evidence justifies the additional system.

## Open Items

- [RESOLVED, 2026-08-24] The concrete opaque ID strategy: UUIDv7 primary keys, opaque string form in APIs (`YMY / Project Owner`, F001 refinement D6).
- [RESOLVED, 2026-08-29] Trace events reference runs polymorphically across discovery, planning, and generation runs (F003 migration `e7a2c50b9d31` drops the discovery-only foreign key on `trace_events.run_id`); generation runs, per-lesson artifacts, and the authoritative run-event log live in their own tables (F003 Spec Data Changes).
- [RESOLVED, 2026-08-30] Generation runs carry an `artifact_kind` (`lesson_plan` | `slide_deck`) with run identity unique per project + bound versions + kind, plus a nullable `prerequisite_run_id` binding each deck run to the complete lesson-plan run it consumes; per-lesson slide-deck artifacts (incl. slide count) live in `slide_deck_artifacts` (F004 migration `b41d6c0f7a2e`).
- [RESOLVED, 2026-08-31] Exercise runs extend `artifact_kind` with `exercise` and record the teacher-selected difficulty tier on the run (`generation_runs.difficulty`, nullable, deliberately outside the unique run identity per F005 D9); per-lesson exercise/answer pairs (both object keys and checksums, item and category counts) live in `exercise_artifacts` (F005 migration `d5a9c1f3b7e4`).
- [UNKNOWN, NON_BLOCKING] The identity provider's account-deletion callback is resolved for F001 (Clerk user-deletion API), and local MinIO deletion is synchronous; hosted object-store deletion guarantees remain open. Resolve before public multi-account deployment.
- [UNKNOWN, NON_BLOCKING] Minimum non-content security-audit retention is not selected. Resolve during the security and operations Feature without retaining deleted teacher content.

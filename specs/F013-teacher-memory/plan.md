# F013 Implementation Plan — Teacher Memory

- Plan ID: `plan-f013-r1`
- Inputs (Gate-validated): Spec @ `75ee61c2cf0b` (`SPEC READY`), UX/UI @ `ux-ui-f013-r1` / `8b39aeebb9a9` (`UI READY`), Test Design @ `test-design-f013-r1` (TS-001..TS-027)
- This Plan answers only how to implement; requirements live in the Spec. It adds no rule, no Scope, and no contract change.

## Architecture fit

- New module `apps/backend/src/lessoncanvas/modules/teacher_memory/` owning records, proposals, project overrides, pass pipeline, effective-set assembly, and the memory read model — the "Teacher Memory and Preferences" module of `docs/ARCHITECTURE.md`.
- Dependency directions: teacher_memory → identity_workspace (authorization, audit), PostgreSQL, discovery_planning (reads confirmed brief/blueprint versions and brief language field as trigger evidence/conflict input). Discovery/planning/artifact graphs consume teacher_memory's effective-set function as a context input (ADR-0005-decided application surface; ROADMAP Sequencing Notes anticipated F003–F005 adoption). Trace writes go through the existing run trace/event helpers (Run Orchestration boundary).
- New Celery task `lessoncanvas.generate_memory_proposals` (best-effort, idempotent per pass identity) on the existing Redis transport; no new service, cache, queue, or framework.
- Configuration via `settings.py`: `memory_max_records` (20), `memory_record_max_chars` (300), `memory_injection_budget_chars` (2500), `memory_max_candidates_per_pass` (3) — Spec-fixed defaults, environment-overridable like other bounds.

## Data and migration

- One Alembic migration (head after `f012a7c9d2e4`) adding:
  - `memory_records`: workspace FK, category enum (4 values), content text, normalized content hash, evidence polymorphic references (brief_version_id / blueprint_version_id / generation_run_id, nullable), created/updated timestamps; unique (workspace_id, category, content_hash).
  - `memory_proposals`: workspace FK, category, content, content_hash, evidence references, status (`pending|rejected|superseded`), pass FK, decided_at; partial unique pending-slot guard enforced transactionally.
  - `memory_passes`: workspace FK, trigger kind + evidence identity (unique), state (`scheduled|running|completed|failed`), cost fields, timestamps.
  - `memory_project_overrides`: project FK + record FK + enabled bool, unique (project_id, record_id).
- `TechnicalEvaluation.memory_state_json` keeps its Text shape; content upgrades to the structured revision-list snapshot (Spec D6).
- `tests/conftest.py` truncate list extended; F011 `PROJECT_SCOPED_TABLES` / workspace sweep extended (T4).

## API flow (target)

- `GET /memory` → records (with conflict summaries and applied counts), proposals (all visible states), passes (with retryable failures); `POST /memory/proposals/{id}/confirm` (optional edited text), `POST /memory/proposals/{id}/reject`, `POST /memory/passes/{id}/retry`, `PATCH /memory/records/{id}`, `DELETE /memory/records/{id}` — all `WorkspaceDep`-guarded, `require_general_rate`.
- `GET /projects/{project_id}/memory` → effective set (applied/disabled/conflicted lists); `POST /projects/{project_id}/memory/records/{record_id}/override` → project-scoped enable/disable.
- Evidence surfaces: `run_summary` gains the applied-memory section; `memory.applied` trace events flow through the existing merged events endpoint — no new parallel authority.
- Error classes: `MEMORY_LIMIT` (count vs length copies), stale/proposal-decided, existing authorization/auth taxonomy.

## Model-call contracts

- Proposal pass: one `adapter.complete` call, user payload `{"kind": "memory_propose", "confirmed_evidence": {...capped excerpts...}, "existing": [...category summaries...]}`; system prompt states JSON-only output, category enum, candidate limit; response validated (unknown category / over-length / malformed dropped per TS-004).
- Injection: existing discovery/planning/generation user payloads gain `memory_context` (array of `{category, text}` records, capped/ordered per U6); system prompts unchanged in authority; `FakeModelAdapter` echoes the new keys deterministically for CI (existing echo contract extended).

## Tasks (vertical slices)

- **T0 — Branch, migration, models, sweep registration**: branch `feature/F013-teacher-memory`; migration + SQLAlchemy models + conftest truncation; deletion-sweep table registration with the project/workspace cascades; proof: migrated test DB + extended deletion suites green (TS-014 structure), full suite still green.
- **T1 — Pass pipeline and proposal state machine**: `memory_passes` scheduling from the three trigger hooks (brief/blueprint confirm, run settlement), Celery task with identity idempotency, adapter contract + validation + normalization + dedupe + pending-slot supersede; tests TS-001..TS-006 (backend).
- **T2 — Management API, caps, audit**: memory endpoints, cap enforcement with race safety, audit events (content-free, pass cost estimate), retry action; tests TS-011 (API), TS-016, TS-017.
- **T3 — Application, conflict, budget, trace**: effective-set assembly consumed by discovery/planning/generation payload builders; `memory.applied` trace event + run-summary section; language_mode conflict rule; U6 budget order; tests TS-007..TS-010, TS-012.
- **T4 — Deletion semantics complete**: record-deletion cascade (overrides, referencing proposals), historical-trace honesty, project/workspace completeness assertions; tests TS-013, TS-014 finalized.
- **T5 — F009 pinning upgrade**: structured snapshot, comparability signature, `C-MEM-1` on the new shape, legacy rendering; tests TS-018, TS-019 (backend + web rendering).
- **T6 — Web client + account memory section**: typed `lib/api.ts` functions; `/account` 教师记忆 section (records, quota, edit modal with live counter, delete confirm, pending list); tests TS-020.
- **T7 — Workspace proposal region + badge**: shared proposal-card component hosted in brief/blueprint/artifact panels; header badge with count/link; tests TS-021.
- **T8 — Evidence applied-context region**: 教师记忆（本项目） region with applied list, conflict/budget disclosure, per-project toggles, account link; tests TS-022.
- **T9 — E2E, accessibility, responsive**: `memory-journey.spec.ts` covering the full deterministic journey, keyboard/label assertions, 420px spot; tests TS-023, TS-024, TS-025.
- **T10 — Live evidence, regression, review, docs sync**: TS-026 single owner-authorized live pass (evidence appended to test design); TS-027 full sweep; Self Review (`review.md`); documentation sync (API, DATABASE, ARCHITECTURE module table consumer note, UX, UI, TESTING, FRONTEND as affected; README only if commands change — none expected).

## Transaction / consistency notes

- Pass identity uniqueness makes scheduling idempotent; the Celery task transitions state under row lock; a completed pass short-circuits retries (TS-002/TS-003).
- Record confirm/edit/delete and proposal decisions run in single transactions with explicit stale errors; the pending-slot supersede is one transactional swap.
- Effective-set assembly happens once per run/pass start inside the owning transaction and is snapshotted to the trace; later memory mutations never rewrite an in-flight or completed run's applied context.

## Verification cadence

- Per task: focused `uv run pytest` slices + `corepack pnpm web:test` for web tasks; full sweep (TS-027) before review.
- Exit conditions: all TS NOT RUN rows evidence-backed (except TS-026 pending authorization), suites green, review findings fixed or dispositioned, docs synced.

## Risks / unknowns

- Fake-adapter proposal quality is synthetic by construction — the live pass (TS-026) is the quality signal; deterministic tests assert contract, not plausibility.
- Four host panels share one proposal component; drift risk handled by the shared component and TS-021.
- The module-table consumer wording in AGENTS/ARCHITECTURE gains an explicit memory-context note at docs sync (planned adoption, not a new L3 decision; ADR-0005 already decided the application surface).

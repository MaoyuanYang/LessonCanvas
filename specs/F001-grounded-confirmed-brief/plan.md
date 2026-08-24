# Implementation Plan: F001 Grounded Confirmed Brief

## Ready Inputs

- Spec: `specs/F001-grounded-confirmed-brief/spec.md` / `SPEC READY Status: PASS` / revision `d7ae5094c490`
- UX/UI: `specs/F001-grounded-confirmed-brief/ux-ui.md` / `UI READY Status: PASS` / revision `c4cd127cb372`
- Test Design: `specs/F001-grounded-confirmed-brief/test-design.md` / `TEST DESIGN READY Status: PASS` / revision `dc6978dfefc8`
- Complete controlling-input manifest: see Spec Gate Record and UI READY Record (base `de9306d`; AGENTS `2ee6dba879b1`; ROADMAP `44047060e23b`; API `1a10877df315`; DATABASE `9623b9c222b4`; ARCHITECTURE `a3118a75d52b`; PRODUCT `2ec972e941fc`; ADRs 0001–0005 at base)
- Plan revision/change-log ID: `plan-f001-r1`
- Plan Status: `CURRENT`
- Issue/work item: [GitHub Issue #1](https://github.com/MaoyuanYang/LessonCanvas/issues/1)
- Applicable AGENTS/architecture docs: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DATABASE.md`, `docs/TESTING.md`, `docs/FRONTEND.md`, `docs/DESIGN_SYSTEM.md`

## Requirement Guardrail

- Scope/Acceptance changes proposed by this Plan: `NONE`
- If not NONE: `STOP`; update Spec/Test Design through Design Change before continuing.

## Current and Target Flow

### Current

No application exists. Repository holds documentation, ADRs, and Specs only. No build, test, or runtime commands are established.

### Target

Monorepo with:

```text
apps/web      Next.js + React + TypeScript (Clerk sign-in, workspace UI, SSE consumer)
apps/backend  Python package: FastAPI modular monolith + Celery worker entrypoints
              modules: identity_workspace, sources_grounding, discovery_planning,
                       run_orchestration, export (unused in F001), adapters
              adapters: clerk, deepseek (thin), s3/MinIO, mcp standards tool
infra/        docker-compose.yml (PostgreSQL+pgvector, Redis, MinIO), .env.example
```

Request flow: browser -> Next.js -> FastAPI (owner-authorized commands/queries + SSE) -> PostgreSQL (truth) / MinIO (objects) / Celery+Redis (parsing, embeddings) -> LangGraph discovery workflow -> DeepSeek adapter. Confirmed brief version is the authoritative intent output.

## Affected Surface

| Module/page/file | `Add/Modify/Delete` | Responsibility/change | Constraint/reuse |
| --- | --- | --- | --- |
| `infra/` compose + env | Add | Local PostgreSQL+pgvector, Redis, MinIO | No managed services in F001 (D3) |
| `apps/backend` scaffold | Add | FastAPI app factory, settings, error model, Alembic, Celery app | API.md taxonomy; DATABASE.md conventions |
| identity_workspace module | Add | Clerk session validation, workspace, projects, quotas, audit rows | No password storage; PG boundary enforcement |
| sources_grounding module | Add | Upload policy, student-data screening, parsing, retrieval, citation records | Untrusted-input rules; MCP-compatible tool definitions (ADR-0004) |
| discovery_planning module | Add | Gap analysis, questioning limits, brief draft revisions, confirmation | Seven required fields (D8); 6x3 cap (D9) |
| run_orchestration module | Add | Discovery run lifecycle, idempotency, checkpoints, trace capture | LangGraph owns semantic state; Celery owns delivery (AGENTS) |
| adapters (clerk/deepseek/storage/mcp) | Add | Thin provider boundaries + scripted fakes for tests | One model, thin adapter (AGENTS) |
| standards snapshot corpus | Add | Bundled versioned snapshot + MCP-compatible retrieval tool | D5; untrusted content treatment |
| `apps/web` scaffold | Add | Next.js app, Clerk integration, API client, SSE hook | FRONTEND.md structure |
| web screens | Add | Public entry, project list, new preparation, workspace shell (sources/discovery/brief), account & usage, safe not-found | ux-ui.md surfaces; DESIGN_SYSTEM contracts |
| design tokens/components | Add | Tailwind semantic token layer implementing DESIGN_SYSTEM values from ux-ui.md | No library default theme |
| test harness | Add | pytest suites, Vitest+Testing Library, Playwright, fakes | Test Design levels |
| docs | Modify | AGENTS/README/TESTING commands once T0 lands; DESIGN_SYSTEM token values at sync | Update together (AGENTS rule) |

## Implementation Approach

### Domain / Application

- Python domain layer per module with explicit services; API routers are thin. LangGraph graph for discovery: `gap_analysis -> question_rounds(loop, cap 6x3) -> draft_building`, with human interrupt points for teacher answers; semantic checkpoints persisted to PostgreSQL.
- Brief revisioning: draft revisions chain per project; confirmation selects/creates the immutable version row atomically.

### Data / Migration

- Alembic migrations: workspaces, projects, sources, discovery_runs, interaction_messages, brief_draft_revisions, brief_versions, citations, quota_counters, audit_events; UUIDv7 PKs; UTC timestamps; ownership and idempotency constraints at DB boundary (unique active discovery run per project; unique confirmed version per base revision).
- pgvector for source chunks; MinIO for originals/extracted text; owner-scoped keys.

### API / Integration

- Endpoints and error semantics per Spec API Behavior; DTO schemas frozen schema-first (Zod on web, pydantic in backend) in T1/T3/T5 — deviations from Spec semantics are Design Changes.
- SSE stream endpoint with owner-authorized run context; reconnect resumes from authoritative run state.
- Clerk JWT verification at FastAPI boundary; Next.js uses Clerk hosted sign-in.

### Transaction / Idempotency / Concurrency / Consistency

- Confirmation and run creation in single PostgreSQL transactions; advisory/unique constraints enforce single active run and single version per base revision.
- Answer submissions idempotent via client-generated message identity; stop-narration idempotent no-op after first.

### Cache / Messaging / Retry / Timeout

- Redis only as Celery broker; no app cache.
- Celery tasks: source parsing, embedding; bounded transient retries for DeepSeek (timeouts/5xx only); domain-invalid input never retried.
- Provider timeout configured per call class; failures surface as provider/transient errors preserving state.

### Frontend State / Components / UI States

- TanStack Query for server state; React Hook Form + Zod forms; Tailwind token layer with ux-ui.md proposed values (contrast-verified in T2/T12); Radix primitives; lucide icons.
- SSE hook with reconnect-from-server; stop control; streamed text rendered with throttled semantic batches for assistive tech.
- Components implement DESIGN_SYSTEM foundational contracts (button, input, status marker, alert, modal, list, skeleton/empty, disclosure, progress tracker).
- 1024px boundary enforced by layout guards rendering desktop-required notices (D10).

### Security / Validation / Error Handling

- Ownership checks in shared dependency; non-owner -> safe not-found.
- Upload pipeline: extension+MIME allowlist, size/count limits, student-data screening (deterministic patterns + model-assisted classification, content untrusted), rights acknowledgement recorded.
- Injection posture: sources/snapshot/model output treated as data; tool allowlist fixed; no dynamic tool grants.
- Error mapping per ux-ui.md table; correlation IDs on all failures.

### Observability

- Per-run trace records: prompts, responses, citations, tool usage, latency, cost (DeepSeek usage), retries; owner-scoped; deleted with project.
- Audit rows for confirmation, deletion, sensitive access (non-content).

## Test Execution Plan

| Scenario IDs | Test target/path | When to run | Required result |
| --- | --- | --- | --- |
| TS-001 | backend integration `tests/backend/identity/` | T1, then full suite | PASS |
| TS-002 | backend API `tests/backend/projects/` | T1 | PASS |
| TS-003 | backend API adversarial `tests/backend/isolation/` | T1, then every suite run | PASS |
| TS-004, TS-005, TS-006 | backend `tests/backend/sources/` + worker integration | T3 | PASS |
| TS-016 | backend `tests/backend/mcp_standards/` (incl. adversarial metadata) | T4 | PASS |
| TS-007, TS-008, TS-009 | backend unit `tests/backend/discovery_rules/` + workflow integration | T5 | PASS |
| TS-014, TS-015 | backend concurrency `tests/backend/concurrency/` | T5/T7 | PASS |
| TS-020 | backend integration provider-failure suite | T5 | PASS |
| TS-021 | backend unit+API quota suite | T5 | PASS |
| TS-010 | backend SSE suite `tests/backend/streaming/` | T6 | PASS |
| TS-011, TS-012, TS-013 | backend brief suite `tests/backend/brief/` | T7 | PASS |
| TS-022 | web component suites `apps/web/**/__tests__` | T8 (incremental from T2) | PASS |
| TS-018, TS-019 | backend deletion suites with injected failures | T9 | PASS |
| TS-026 | backend trace suite + deletion assertions | T10 | PASS |
| TS-023, TS-024, TS-025 | Playwright `apps/web/e2e/` + a11y checks | T11 | PASS |
| All | full deterministic suite + lint/type checks | every Task exit; final before Review | PASS |

Live DeepSeek checks are excluded from deterministic CI (Test Design TQ-001); a recorded manual live smoke run is performed once during T5 with cost capped, as separate evidence.

## Rollout, Compatibility, and Rollback

- Migration/backfill: `N/A - Greenfield; initial migrations only`
- Feature flag/staged rollout: `N/A - first Feature; no prior behavior`
- Breaking change: `NO`
- Rollback: revert the delivery branch; drop local compose volumes (no production data in F001)

## Risks and Decisions

| Risk/decision | Level | Mitigation/choice | Needs confirmation/ADR? |
| --- | --- | --- | --- |
| LangGraph + Celery responsibility drift | Medium | Celery only delivers parsing/embedding tasks; semantic state stays in graph checkpoints (AGENTS rule) | No (existing constraint) |
| DeepSeek fake fidelity vs live behavior | Medium | Scripted fakes for logic; one capped live smoke in T5; provider error paths tested via injected failures | No |
| Clerk dependency in tests | Low | Dev instance + verifiable test tokens (TQ-002) | No |
| Standards snapshot licensing | Low | Official publicly published curriculum document; snapshot records provenance/version | No |
| Student-data screening false negatives | Medium | Deterministic + model-assisted layers; documented residual risk (TQ-003); F011 revisit | No |
| Toolchain bootstrap size | Medium | T0 is dedicated scaffold slice with its own exit criteria before business code | No |
| Tailwind token values unverified | Low | Contrast verification in T2/T12; DESIGN_SYSTEM updated with evidence at sync | No |

## Interleaved Tasks

- [x] T0 Scaffold + infra: monorepo layout; docker compose (PostgreSQL+pgvector, Redis, MinIO); FastAPI app + Alembic + Celery skeletons; Next.js app skeleton; ruff/eslint/prettier/tsc; pytest/vitest/playwright configs boot; health endpoints. Exit: compose up -> backend health PASS -> web home renders; commands persisted to AGENTS/README/TESTING. — DONE 2026-08-24: 3 services healthy; `/health` live `{"status":"ok","database":"ok"}`; pytest 3 passed; vitest/tsc/eslint/prettier/build all pass; commands synced.
- [x] T1 Identity + projects: migrations (workspaces, projects, quotas, audit); Clerk validation middleware; project CRUD API; TS-001/002/003 PASS; TS-021 quota base. — DONE 2026-08-24: migration `ef4874404c48` applied; JWT verifier adapter (Clerk JWKS when configured, signed dev tokens otherwise); 12 tests green incl. cross-account non-disclosure and quota.
- [x] T2 Web shell + project list: Clerk Next.js integration; public entry; project list with loading/empty/error; new preparation modal; safe not-found; token layer + 1024px guards; TS-022 (project surfaces) PASS. — DONE 2026-08-24: @clerk/nextjs v7 middleware + server guard; project list/create/delete with state matrix and desktop gate (6 component tests); backend ClerkJwksVerifier covered by 4 RS256 tests; lint/typecheck/build green. Live browser sign-in pending Clerk instance "new device verification" setting.
- [x] T3 Sources: upload endpoint + MinIO storage; format/size/count policy; student-data screening; Celery parsing + states; TS-004/005/006 PASS; sources panel UI + TS-022 (source states) PASS. — DONE 2026-08-24 (backend slice): policy/screening/parsing/service/tasks + S3 adapter; migration 572e28894610; 24 backend tests green. Sources UI deferred to T8 workspace surfaces.
- [ ] T4 Standards snapshot + MCP tool: bundle versioned snapshot; internal MCP-compatible retrieval tool; citation records; TS-016 PASS incl. adversarial metadata.
- [x] T5 Discovery core: LangGraph workflow with 6x3 cap + gap rules; DeepSeek adapter + scripted fake; run model, idempotency constraints, trace capture; TS-007/008/009/014/015/020/021 PASS. — DONE 2026-08-24: StateGraph analyze/ask(interrupt)/build_draft with Postgres checkpointer (memory seam in tests); migration a8db34479c31; 37 backend tests green. Capped live DeepSeek smoke deferred until an API key is provided.
- [x] T6 Streaming: SSE endpoint, answers, stop-narration, re-ask, reconnect-from-state; TS-010 PASS. — DONE 2026-08-24: /discovery/stream with offset reconnect, stop preserves completing model call and full trace, re-ask quota-counted; 41 backend tests green.
- [x] T7 Brief + confirmation: draft revisions, PATCH with base revision, atomic immutable confirmation; TS-011/012/013 + confirm-race PASS. — DONE 2026-08-24: brief drafts/versions with unique constraints, 409 stale conflict, 422 missing fields, idempotent and concurrent-safe confirm; migration 3877a2b5d4ed; 46 backend tests green.
- [x] T8 Discovery/brief UI: conversation panel (streaming/stop/re-ask), brief panel (citations, gap markers, correction, confirm modal), stale-conflict banner; TS-022 (workspace surfaces) PASS. — DONE 2026-08-24: workspace tabs (sources/discovery/brief), SSE narration with stop/re-ask, desktop gating, stale banner, confirm gating; 11 web tests green; lint/typecheck/build pass.
- [x] T9 Deletion: project cascade + account deletion with Clerk ordering; audit rows; failure states; TS-018/019 PASS; account & usage UI. — DONE 2026-08-24: synchronous cascade (PG rows, chunks, MinIO objects) with retryable failure state; account purge-then-Clerk ordering with recorded clerk_failed status; migration 35338f02204a; account page with destructive confirm; 50 backend tests green; web checks pass.
- [ ] T10 Trace surface: owner-scoped trace read + cost/latency evidence; TS-026 PASS.
- [ ] T11 E2E + accessibility: Playwright happy path + failure/reconnect; keyboard pass; streamed-batch announcements; visual baseline (shell + brief panel); TS-023/024/025 PASS.
- [ ] T12 Review + docs sync: fix Review findings; sync DESIGN_SYSTEM token values + contrast evidence; confirm AGENTS/README/TESTING commands current; update ROADMAP/Issue; prepare delivery record.

## Start Checklist

- [x] All required Gates are PASS, or UI has a complete `SKIPPED (N/A)` decision record with revision, evidence, time, authority, approval source, and scope. — SPEC/UI/TEST DESIGN all PASS (records in artifacts)
- [x] Gate input manifests match current working-tree artifact revisions, not only the base commit. — hashes listed in Ready Inputs and Gate Records
- [x] Plan MUST NOT redefine Scope, rules, contract, or Acceptance. — Requirement Guardrail `NONE`
- [x] Major dependency/architecture/migration decisions are confirmed. — D1–D11, D-STACK/D-BP/D-FONT, toolchain approved by `YMY / Project Owner`
- [x] Tasks interleave code, tests, and docs. — each Task lists TS coverage; T0/T12 carry docs
- [x] Each Task has a verification point. — Exit criteria per Task

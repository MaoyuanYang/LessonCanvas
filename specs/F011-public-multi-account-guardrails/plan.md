# Feature Implementation Plan: F011 Public Multi-Account Guardrails

## Metadata

- Spec/Issue: `specs/F011-public-multi-account-guardrails/spec.md` / [GitHub Issue #22](https://github.com/MaoyuanYang/LessonCanvas/issues/22)
- Validated inputs: Spec @ `d27deee5bfc8` (`SPEC READY` PASS), UX/UI @ `ux-ui-f011-r1` / `ab827a69abd6` (`UI READY` PASS), Test Design @ `test-design-f011-r1` (hash in `STAGE.md` Gate Snapshot; `TEST DESIGN READY` PASS)
- Plan revision: `plan-f011-r1`
- Branch: `feature/F011-public-multi-account-guardrails` (from `main @ 683172b`)
- This Plan answers only how to implement; it changes no requirement, AC, or contract. Deviations return to Design Change.

## Affected Modules and Boundaries

| Change | Module / path | Boundary notes |
| --- | --- | --- |
| Limit settings + enforcement core | `apps/backend/src/lessoncanvas/settings.py`; new `api/rate_limits.py` + `modules/identity_workspace/limits.py` | PostgreSQL-authoritative counters; one FastAPI dependency applied via existing `deps.py`; no middleware framework, no Redis truth |
| Usage read | `api/account.py` (+ `identity_workspace` service read) | Read-only aggregation |
| Admission control | `modules/run_orchestration/service.py` start paths | Transactional count of active runs per workspace before insert |
| Count-quota atomicity | `modules/identity_workspace/service.py`, `modules/sources_grounding/service.py` | Row-lock (workspace/project `SELECT ... FOR UPDATE`) then count-then-insert inside one transaction |
| Upload hardening | `modules/sources_grounding/policy.py` + `api/sources.py` streaming read; `product_validation/service.py` document path reuses helpers | Magic-byte sniff vs extension; declared/streamed size cap before buffering; bounded docx extraction (cumulative uncompressed-size check via zip directory before parse) |
| SSE stream cap | stream generators in `api/generation.py`, `api/discovery.py`, `api/evidence.py` narration stream | In-process per-workspace active-stream registry with try/finally release (single-process deployment assumption, Spec D1) |
| Audit + retained ledger | `models.py` new `RetainedSecurityEvent`; download endpoints across `api/generation.py`, `decks.py`, `exercises.py`, `delivery.py`, `product_validation.py`; new `GET /account/audit` | Existing `AuditEvent` pattern for lifetime events; ledger rows survive account deletion (content-free) |
| Deletion completeness | `modules/identity_workspace/deletion.py` | Raw-SQL delete of LangGraph checkpoint rows (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) by `thread_id` in the project's run ids, inside the cascade transaction; completeness verification (governed-table residual query + both-bucket prefix listing); repair = idempotent re-issue; source object-failure visibility (new source status value) |
| Worker fast-fail | `modules/artifact_production/{graph,deck_graph,exercise_graph}.py` | Vanished-run/stale-update exception class → immediate terminal settle (`missing_run` path); transient errors keep bounded retry; negative control keeps retry |
| Adversarial corpus | new `src/lessoncanvas/adversarial_datasets/` (manifest + fixtures, F009 governance pattern) | Synthetic, self-authored, checksummed; fails closed |
| Account cascade + ledger | `modules/identity_workspace/deletion.py` | Workspace audit rows still deleted; `RetainedSecurityEvent` rows persist |
| Web surfaces | `app/(authed)/account/page.tsx` (+ sections component), `lib/api.ts` (label maps, error classes), generation/deck/exercise panels (limit alerts), sources panel (partial-delete state), project list/workspace (deletion states) | Existing patterns only; no new visual language |
| Docs sync | `docs/API.md`, `docs/DATABASE.md`, `docs/TESTING.md` (+ `README.md`/`AGENTS.md` only if commands change) | Actual impact only |

## Data and Migration

- New tables: `rate_window_counters` (workspace_id, limit_class, window_start, count, bytes_accum optional; unique (workspace_id, limit_class, window_start)) — fixed-window atomic upsert increment; `retained_security_events` (id, workspace_id, action, occurred_at; no content columns) — survives workspace deletion.
- No domain-table semantic changes; `Source.status` gains one value (object-delete-failed display state) if Plan-level review confirms a status beats a derived flag — decided in T5 with migration if needed.
- One Alembic migration; tests auto-upgrade (existing pattern); rollback = downgrade (additive only).

## Transactions / Consistency / Idempotency

- Window upsert uses `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` with a conditional reject when the new count exceeds the limit (atomic admit/reject).
- Admission and count-quota checks run inside the creating transaction; admission counts `queued/executing` runs per workspace.
- Deletion keeps single-transaction cascade + verification outside the transaction; repair re-uses delete idempotency.
- Ledger writes join the audited action's transaction.

## Task Breakdown (vertical slices; every task ends green on its tests)

| ID | Task | Tests / evidence | Done condition |
| --- | --- | --- | --- |
| T0 | Branch; limit settings + env overrides; migration (two tables); baseline suites green | TS-019 baseline | `uv run pytest` + `web:test` green pre-change parity |
| T1 | Rate-limit core: dependency, window arithmetic, atomic upsert, 429 payload (limit name, retry_after), per-class limits (general/expensive), `GET /account/usage` read | TS-002 | Rate tests green; usage read returns every D2 limit + consumption |
| T2 | Upload volume cap + content sniffing + oversize-before-buffer + bounded docx extraction on both upload paths | TS-003 (volume), TS-007 | Policy tests green; no unbounded reads |
| T3 | SSE per-workspace stream cap with release-on-close | TS-003 (streams) | 7th stream rejected named; existing streams unaffected |
| T4 | Concurrent-run admission + count-quota row-lock atomicity | TS-004, TS-013 | Admission + race tests green; existing idempotency unchanged |
| T5 | Deletion completeness: checkpoint cascade, verification + repair ledger, source-failure visibility, account partial states | TS-009, TS-011 | Deletion tests green incl. fault variants |
| T6 | Worker fast-fail on vanished runs (three families) + negative control | TS-010 | Immediate terminal settle; provider retry preserved |
| T7 | Adversarial corpus + injection/screening/tool-metadata/inert-rendering suites | TS-005, TS-006 (backend), TS-008 | Corpus governance fail-closed; all suites green |
| T8 | Download audit events + `GET /account/audit` + retained ledger write/survive | TS-012 (backend) | Audit list bounded; ledger content-free and post-deletion present |
| T9 | Cross-account inventory sweep suite + bounded multi-account journey | TS-001, TS-015 | Sweep derives routes from app; journey invariants green |
| T10 | Web: account sections (usage/disclosure/audit), limit/admission feedback mapping, deletion partial states, small-screen gates | TS-016, TS-017, TS-006 (web) | Component + a11y tests green; lint/typecheck/build clean |
| T11 | E2E journey (env-gated + substitute), full regression, dependency/secret evidence | TS-018, TS-019, TS-014 | Evidence recorded; suites green |
| T12 | Documentation sync (API/DATABASE/TESTING; README/AGENTS only if commands change) + review.md | — | Docs match implementation; no untruthful claim |

## Verification Commands (per task and completion)

```text
cd apps/backend && uv run pytest && uv run ruff check src tests migrations
corepack pnpm web:test && corepack pnpm web:lint && corepack pnpm web:typecheck && corepack pnpm web:build
(corepack pnpm --filter web test:e2e  where environment permits, CLERK_E2E gated)
uv audit; corepack pnpm audit  (evidence recorded; documented fallback if unavailable)
```

## Risks / Unknowns / Exit Conditions

- Rate-limiter keying must not break parallel suites (TQ-001): verified in T1 before touching other suites.
- LangGraph checkpoint table names must be confirmed against the installed version in T5 (raw SQL pinned to the installed schema; test asserts actual cleanup).
- SSE in-process registry assumes the documented single-process API deployment (Spec D1 assumption); recorded in code constraint comment and docs.
- Exit: all TS-* executed or explicitly environment-gated with substitute + resume condition; AC matrix complete; review recorded; docs synced.

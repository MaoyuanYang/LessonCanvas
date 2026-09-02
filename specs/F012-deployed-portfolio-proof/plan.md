# Implementation Plan: F012 Deployed Portfolio Proof

- Plan ID: `plan-f012-r2` (r1 superseded by the 2026-09-02 ADR-0006 Design Change; adds T4b/T6b identity-removal slices)
- Bound inputs: Spec @ `8c033df6a4e6` (SPEC READY), UX/UI @ `ux-ui-f012-r1` / `36d3aa65cfaa` (UI READY), Test Design @ `test-design-f012-r1` (TEST DESIGN READY)
- Last Updated: 2026-09-02

## Approach

Containerize the existing application unchanged in behavior: packaging, seeding, one bounded sample-read surface, deployed verification scripts, and documentation. No new framework, service, or business truth (Spec rules; AGENTS). All guardrail behavior is verified, never modified.

## Tasks

| ID | Task | Scope | Verification |
| --- | --- | --- | --- |
| T0 | Branch `feature/F012-deployed-portfolio-proof` from `main` | git branch (local) | branch exists |
| T1 | Backend image + worker/compose service: uv-based multi-stage Dockerfile for FastAPI app, compose service `api` (replicas: 1, healthcheck `GET /health`) and `worker` (Celery), env-driven config wiring | `infra/`, backend packaging | image builds; local compose brings api+worker healthy; TS-014 suites still pass |
| T2 | Web image + compose service: Next.js standalone build Dockerfile, compose service `web`, `NEXT_PUBLIC_API_BASE_URL` wiring for LAN origin | `infra/`, `apps/web` config | image builds; web serves on LAN interface; TS-014 web suites pass |
| T3 | Deployment chain scripts: one documented entry running build → migrate → start → smoke; teardown/redeploy script; smoke script (health + core read checks) | `infra/scripts/` | TS-001, TS-002 executed and recorded |
| T4 | Sample read surface (server-enforced): implement the Implementation-choice access rule bounded by UX U1 (dedicated read path or demo-workspace designated access; server-side authorization, never client-only) with read-only semantics on write attempts | backend router/service + tests | TS-005 |
| T5 | Seeding script: idempotent synthetic sample project from the governed corpus pattern (manifest/checksums/revision), demo workspace, synthetic metadata marking | `infra/scripts/` or backend seed module + tests | TS-006 (missing/stale), seeding idempotency in TS-002 |
| T6 | Web `/sample` shell + write suppression + landing portfolio-review section; reuse panels, Alert/EmptyState per UX doc | `apps/web` | TS-003, TS-004, TS-006 unit/e2e |
| T7 | Postgres LangGraph checkpointer investigation (B-001): lifecycle/recovery/deletion behavior in deployed topology; verified record or fix with regression test | backend + tests | TS-011 |
| T8 | Deployed verification execution: deployment chain + smoke (TS-001/002), representative journey with recovery (TS-007), deletion completeness (TS-008), SSE single-process + cap (TS-010), D10 constraint re-verification (TS-012), reviewer limits journey (TS-013); write `deployment-evidence.md` binding command/date/outcome | deployed environment + evidence record | evidence rows complete; no placeholder |
| T9 | Accessibility + reduced-screen deployed spot check; record result | evidence record | TS-015 |
| T10 | Documentation sync: README quick entry, `docs/TESTING.md` (deployed verification layer), `docs/ARCHITECTURE.md` (deployment topology, single-process constraint), `docs/API.md`/`DATABASE.md` only if T4/T7 touch them, UX/UI docs if landing/sample copy affects shared docs | docs | review checklist |
| T11 | Self Review (`review.md`), full suites, docs check; prepare PR | review record | Review checklist |

## ADR-0006 Identity-Removal Slices (added in r2)

| ID | Task | Scope | Verification |
| --- | --- | --- | --- |
| T4b | Backend identity swap: `POST /auth/guest-token` (HS256, random subject, 30d); delete `ClerkJwksVerifier`/`clerk_admin`/clerk settings; account deletion stops after purge; new tests `test_guest_token.py`; delete `test_clerk_verifier.py` | backend + tests | TS-016; isolation sweep green |
| T4c | DB rename `clerk_user_id`→`subject` (workspaces + account_deletion_events, constraint/index rebuild); ~25 call sites | migration + code | pytest green on migrated schema |
| T6b | Web identity swap: delete sign-in route/middleware/ClerkProvider/UserButton; `lib/auth.ts` guest token; replace `useAuth` in 18 files; account page identity/deletion rework; remove `@clerk/*`; unit tests; e2e rewrite (drop clerkSetup/CLERK_E2E, delete authenticated.spec, public.spec direct entry) | web + e2e | vitest/tsc/lint + e2e green |

## Sequencing and Slices

T0 → T1 → T2 → T3 (stack deployable) → T4 → T5 → T6 (sample vertical slice) → **T4b → T4c → T6b (ADR-0006)** → T7 → T8 → T9 → T10 → T11. Each of T1–T7 lands with its tests in small vertical commits; T8 requires the deployed environment and is the single largest evidence slice; T9–T11 close delivery.

## Risks and Constraints

- [REMOVED 2026-09-02, ADR-0006] The former Clerk LAN-origin prerequisite no longer exists; B-003 reduces to docker access and `infra/deploy.env` (passwords + model key).
- Live-model spend is bounded to the representative journey evidence (TQ-001).
- Secrets only in untracked env; evidence records must be reviewed for credential absence before commit.
- If T7 finds a defect requiring schema change, it goes through a normal migration and Documentation Sync within this Feature.

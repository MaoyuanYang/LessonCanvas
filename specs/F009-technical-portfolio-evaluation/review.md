# F009 Review Record

- Work item: [GitHub Issue #18](https://github.com/MaoyuanYang/LessonCanvas/issues/18) · Spec: `specs/F009-technical-portfolio-evaluation/spec.md` @ `15803bdc1837` · Branch: `feature/F009-technical-portfolio-evaluation`
- Review stage: 2026-09-01, `YMY / Project Owner` driving via feature-dev session

## Changed Surfaces

| Surface | Change |
| --- | --- |
| Dataset package | New `apps/backend/src/lessoncanvas/evaluation_datasets/` (three CC0-1.0 synthetic units + SHA-256 manifest, revision `eval-datasets-r1`) with fail-closed loader `modules/technical_evaluation/dataset.py` |
| Evaluation module | New `modules/technical_evaluation/` (`criteria.py` deterministic engine, `harness.py` scripted pipeline client, `service.py` idempotent creation/execution/reads) |
| Persistence | Migration `f009a1b2c3d4`: `technical_evaluations`, `technical_evaluation_results`; deletion cascade extended |
| API | New router `api/technical_evaluation.py` (overview / idempotent create / detail / report) registered in `main.py` |
| Worker | New task `lessoncanvas.run_technical_evaluation` |
| Fault injection | `FakeModelAdapter` eval-gated fault profiles (`provider_persistent`, `truncated_json`) honored only with fake adapter + `LESSONCANVAS_EVAL_FAULT_PROFILE` |
| Model adapter | `stream_with_usage` on both adapters (DeepSeek `stream_options.include_usage`); both narration paths record tokens + estimated cost; NULL stays NULL (F006 L-1 closed) |
| Lesson graph | Unparseable model responses reclassified as per-lesson validation failure with bounded retry and explicit failed-event (Spec D6/AC-007; previously misclassified as provider exhaustion) |
| Web | `技术评估` region in `evidence-panel.tsx` (new `technical-evaluation-region.tsx`), print-styled report route `technical-evaluation/report/`, `lib/api.ts` client + label maps, E2E journey spec `e2e/evaluation-journeys.spec.ts` |
| Docs | API/DATABASE/TESTING/ARCHITECTURE F009 resolutions; ROADMAP/STAGE projections |

## Self-Review Findings

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| SF-1 | High | Truncated/unparseable model JSON was misclassified as a provider failure (F003-era): bounded Celery retries exhausted with reason "provider retries exhausted", no explicit per-lesson validation-failure event — AC-007's explicit failure could never be recorded | Fixed in delivery: per-lesson `LessonValidationError` with bounded in-node retry, explicit lesson-failed event, parse-failure trace recorded; TS-009 green; deck/exercise graphs noted as candidate follow-up (M-3) |
| SF-2 | High | Concurrent duplicate evaluation creation surfaced `IntegrityError` (race between existence check and insert) — Spec D10 requires convergence | Fixed: converge-on-conflict (rollback → re-query → return existing), same pattern as generation-run identity; concurrent test green |
| SF-3 | High | `C-IDEM-1` initially counted all runs of the kind in the project, failing when other passes existed | Fixed: identity scoped to the evaluation's bound version pair |
| SF-4 | Medium | TestClient SSE consumption deadlocks for idle keepalive streams in this environment (reproduced on the F008 baseline; not an F009 regression) | F006 keepalive test now consumes the generator in-process with unchanged assertions (M-1 residual recorded); all other streaming tests unchanged and green |
| SF-5 | Low | Two narration test stubs implemented only the legacy `stream()` adapter contract | Upgraded to `stream_with_usage` (D9 contract) with delegating `stream` |

## Checklist Results

- Spec/Scope: all D1–D11 decisions implemented as specified; no scope expansion. Evaluation reads are version-bound; the harness is a scripted client of existing services (no second workflow authority).
- AC coverage: AC-001..AC-015 all evidenced (see Test Design Execution Evidence Snapshot). AC-009 satisfied by the owner-authorized live protocol: six live passes (3 units × 2), five pass and one honest fail (travelling-around p2, C-ART-1 slide-deck lesson 3 not downloadable) — per-pass outcomes recorded side by side, the failure explicit and unmasked (Spec D3/AC-010). AC-006 live half satisfied by the real-worker stop/restart recovery demonstration; AC-012 live half satisfied by narration usage capture inside the live passes' cost evidence.
- Architecture/module rules: new code sits in Alignment-and-Evaluation ownership (`modules/technical_evaluation`); dependencies point at sources/planning/run services as allowed; PostgreSQL remains the only truth (evaluation rows + read-side derivations); no new infrastructure product, cache, queue, or second model.
- Data/concurrency/idempotency: unique identity + converge-on-conflict (tested concurrent); terminal evaluation rows immutable; deletion cascade tested.
- Security/privacy: workspace-authorized endpoints; non-disclosure sweep green; dataset is synthetic CC0-1.0 with fail-closed governance; fault profiles unreachable in production configuration (gate-asserted).
- Error mapping: requirement (governance/eligibility), provider-unavailable settling, quota class; no internals leaked.
- Docs sync: API/DATABASE/TESTING/ARCHITECTURE updated; UX/UI/DESIGN_SYSTEM unchanged (composition only — no new tokens or shared variants; the report composes the documented F008 print pattern); FRONTEND unchanged (no new pattern introduced).
- Tests target observable behavior: API payloads/status, trace accounting, component/E2E user-visible states.

## Verification Evidence

- Backend: `uv run pytest` — 221 passed (197 prior + 24 F009), `uv run ruff check src tests migrations` clean (2026-09-01).
- Web: `corepack pnpm web:test` 63/63; `web:lint` 0 errors (7 pre-existing e2e warnings); `web:typecheck` clean; `web:build` clean.
- E2E: evaluation journey spec delivered (`E2E_EVAL_FAULT=1` gated); browser execution environment-blocked this session (no Clerk E2E credentials / running stack) — substitute coverage green (M-1/L-2 class residual, resume condition recorded).
- Live protocol (TS-017): PASS — owner-authorized execution 2026-09-01 with real DeepSeek; evidence files `live-evidence.json` / `live-evidence-summary.txt` / `worker-recovery-evidence.json` in the spec directory; per-pass cost $0.0097–$0.0141; environment residuals L-3/L-4 recorded in the Test Design snapshot.

## Delivery

- Status: delivery flow authorized by `YMY / Project Owner` on 2026-09-01 (commit + push + PR; merge separately authorized later).
- PR-ready summary: F009 adds the governed synthetic evaluation dataset, the deterministic criteria engine with blocking/diagnostic honesty, the idempotent scripted evaluation harness with eval-gated fault injection, the owner-facing technical-evaluation API and report, the evidence-panel evaluation region, narration stream usage capture (F006 L-1), and the truncated-response validation reclassification fix with regression coverage.
- Rollback: additive migration (drop two tables); no data transformation of existing rows; revert restores prior behavior except the (intended) validation-classification and usage-capture improvements.

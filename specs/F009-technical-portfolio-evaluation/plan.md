# Implementation Plan: F009 Technical Portfolio Evaluation

## Inputs and Validated Revisions

- Spec: `specs/F009-technical-portfolio-evaluation/spec.md` @ `15803bdc1837` (`SPEC READY` PASS)
- UX/UI: `ux-ui-f009-r1` @ `d3860c7a8c05` (`UI READY` PASS)
- Test Design: `test-design-f009-r1` @ `5a7fc2df6b13` (`TEST DESIGN READY` PASS)
- Base: `main @ 13dbee6`; branch `feature/F009-technical-portfolio-evaluation`
- This Plan adds no requirement and changes no approved contract; deviations return to Design Change.

## Architecture Placement

- New backend module `apps/backend/src/lessoncanvas/modules/technical_evaluation/` (Alignment-and-Evaluation ownership): `dataset.py` (fail-closed loader + manifest verification), `criteria.py` (deterministic criterion engine; zero model calls), `harness.py` (scripted pipeline client calling existing module services exactly as the teacher-facing API does — sources upload, scripted discovery/planning answers, brief/blueprint confirm, generation/deck/exercise starts with wait/resume, alignment read; emits run-events for progress), `service.py` (idempotent creation, status transitions, overview/detail/report reads), `schemas.py`.
- Evaluation set is project-scoped: the owner designates one project as the evaluation anchor (typically a fresh project); each pass accumulates its own immutable confirmed version pair inside it; all evaluation reads are version-bound, never "current"-bound. No quota change is required (one anchor project per evaluation set); the Spec's quota-raise allowance stays unused.
- New router `api/technical_evaluation.py` (`/projects/{id}/technical-evaluation...`), registered in `main.py`; ownership via the existing `WorkspaceDep` + `get_owned_project` pattern; errors via `api/errors.py`.
- Migration `f009<hash>`: additive tables `technical_evaluations` (id, project_id, dataset_revision, unit_key, pass_index, mode live|deterministic, scenario `full_pipeline|fault:<name>`, model_config_json, memory_state_json, brief_version_id, blueprint_version_id, status queued|active|partial_evidence|completed|provider_unavailable|failed, failure_reason, overall_outcome, created_at/started_at/completed_at; uq (project_id, dataset_revision, unit_key, pass_index, mode, scenario)) and `technical_evaluation_results` (id, evaluation_id cascade, criterion_key, classification blocking|diagnostic, outcome pass|fail|missing_evidence|NULL for diagnostics, measured_json, evidence_json, created_at; uq (evaluation_id, criterion_key)). Audit via the existing `audit_events` pattern; deletion cascades from `projects`.
- Celery task `lessoncanvas.run_technical_evaluation` (max_retries small; resume-safe: re-invocation continues from recorded pass state, same idempotent identity).
- Dataset package `apps/backend/src/lessoncanvas/evaluation_datasets/` shipping inside the distribution: `units/<unit_key>/` (synthetic source documents + `unit.json` with output mode, scripted interview answers, expected-evidence direction; license header in every file) + `manifest.json` (dataset_revision + per-file SHA-256); loader via `importlib.resources`; tamper/unlicensed → fail closed.
- Eval fault profiles: settings key `eval_fault_profile` honored only when `model_adapter == "fake"`; `FakeModelAdapter` extended with profile-driven behaviors (provider transient, in-task worker-death hook consumed by the harness, truncated JSON) beyond the existing title-marker scripting; production configurations can never activate them.
- Narration usage capture (F006 L-1): adapter stream contract extended to report usage — `DeepSeekAdapter.stream` sends `stream_options: {"include_usage": true}` and surfaces the final usage chunk; `FakeModelAdapter.stream` emits deterministic usage; both narration call sites (`discovery_planning/narration.py`, `run_orchestration/evidence.py`) record prompt/completion tokens and estimated cost (existing price table) into the owning `trace_events`; provider-not-reported stays NULL → surfaces as 未记录/missing-evidence, never zero.
- Web: typed client additions + evaluation label maps in `lib/api.ts`; 技术评估 summary region in `components/evidence-panel.tsx` (states, chips, criterion groups, comparison columns, 启动评估 modal with live cost sentence + duplicate notice); print-styled report route composing the F008 pattern.

## Task Breakdown (interleaved code + tests)

- T0 — Migration + models + dataset package + governance tests: alembic revision, ORM models, cascade; dataset package with the three authored units + manifest; fail-closed loader. Tests TS-001, TS-013 (deletion half). Exit: migration applies; tests green.
- T1 — Criteria engine + snapshots: criterion definitions (C-TRACE-1, C-GROUND-1, C-ART-1, C-IDEM-1, C-SUPER-1, C-RECOV-1, C-RENDER-1, C-MEM-1) and diagnostics (M-LAT, M-COST, M-VAR, M-COVER, M-JUDGE); deterministic outcome computation over recorded state; memory/config snapshot recording; no model calls. Tests TS-002, TS-003, TS-010. Exit: unit/integration tests green.
- T2 — Harness + fault profiles + Celery task: scripted pipeline client; eval-gated fault profiles (fake-adapter gate assertions); duplicate-submission and stale-version scenario orchestrations; idempotent service creation; `run_technical_evaluation` task; version-pair binding per pass. Tests TS-004, TS-005, TS-006, TS-007, TS-008, TS-009. Exit: integration/concurrency tests green.
- T3 — API + report reads: overview/create/detail/report endpoints, ownership + error mapping (requirement/provider/quota/stale classes), audit events. Tests TS-012, TS-013 (sweep), TS-004 API half. Exit: API tests green; ruff clean.
- T4 — Narration usage capture: adapter stream usage contract (both adapters), trace-event recording at both narration call sites, NULL-honesty. Tests TS-011. Exit: tests green; F006 narration/E2E regression untouched.
- T5 — Web client + 技术评估 region: api.ts types/functions/labels; region with full state vocabulary, criterion groups with 非阻断 labels, comparison columns with comparison-unavailable, 启动评估 modal (validation, cost sentence, duplicate notice, error mapping); F006 surfaces below intact. Tests TS-014. Exit: Vitest green; eslint/tsc clean.
- T6 — Report route + small-screen: print-styled report route (bound versions, revision, config, memory state, per-unit per-pass outcomes, fault outcomes, cost/latency, 未评估 product status), 1024px boundary, a11y semantics. Tests TS-015, TS-016 a11y parts. Exit: tests green.
- T7 — E2E + regression + docs sync: Playwright evaluation journey TS-016 (keyboard, states, report); regression TS-018 over existing journeys; full backend/web suites; documentation sync (API/DATABASE/TESTING/ARCHITECTURE/UX/UI/DESIGN_SYSTEM/FRONTEND/README as affected); Gate/Roadmap/Stage/Issue updates. Exit: all suites green; docs synchronized.
- T8 — Live evidence protocol (owner-authorized): TS-017 execution on the controlled live stack (six passes + one real-worker stop/restart demonstration; requires owner-provided DeepSeek credentials and real worker); record the Execution Evidence Snapshot with raw per-pass metrics; deviations/residuals owner-visible. Exit: snapshot recorded; honest outcomes (including any provider-unavailable evidence).

## Verification Commands

- Backend: `uv run pytest` (incl. `tests/test_evaluation_dataset.py`, `tests/test_technical_evaluation.py`), `uv run ruff check src tests migrations`
- Web: `corepack pnpm web:test`, `web:lint`, `web:typecheck`, `web:build`
- E2E: existing Playwright config, new evaluation journey on the deterministic stack; live protocol T8 per TESTING.md separation (manual harness execution, evidence recorded)
- Migration: `uv run alembic upgrade head` (test DB upgrades automatically in conftest)

## Risks / Exit Conditions

- Risk: stream-usage contract change regresses narration SSE → keep the token-yield generator shape (usage surfaced via a holder, not interleaved events); full F006 narration/E2E regression in T4 and T7.
- Risk: fault profiles leak outside evaluation → hard gate (fake adapter + profile key) with explicit gate assertions in TS-006; no production default.
- Risk: harness runtime in tests → deterministic passes run eager/fast against the fake adapter; only bounded scripted scenarios hit the DB-heavy path.
- Risk: live evidence window provider instability → provider-unavailable recording is itself valid honest evidence (Spec alternative flow); resume reuses the same idempotent pass.
- Exit: TS-001..TS-018 recorded PASS (or honest provider-unavailable evidence) in the Execution Evidence Snapshot; full suites green; docs synced; review and delivery follow.

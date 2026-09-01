# F009: Technical Portfolio Evaluation

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #18](https://github.com/MaoyuanYang/LessonCanvas/issues/18) — bound 2026-09-01 (authorized)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F008` (DONE) for complete versions, artifacts, alignment status, delivery, and layered evidence; `F006` (DONE) for trace/cost telemetry (L-1 narration token capture inherited here)
- Last Updated: 2026-09-01

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-01
- Decision Authority: `YMY / Project Owner` — approved via interactive session (D1 self-authored synthetic dataset, D2 blocking/diagnostic split, D3 two live passes per unit with no cross-pass normalization, D4 deterministic-only injection, D6 unit topics selected interactively 2026-09-01; D5, D7–D11 resolved from repository evidence and confirmed with Spec approval), scope: F009 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-015, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F009-technical-portfolio-evaluation/spec.md` @ (this file, final working-tree hash recorded in `STAGE.md` Gate Snapshot)
  - `specs/F008-alignment-review-and-delivery/spec.md` @ `0e1e911d1158`
  - `specs/F006-layered-run-evidence/spec.md` @ `a9b445a541cf`
  - `specs/F007-versioned-targeted-regeneration/spec.md` @ `ae06a143e088`
  - `AGENTS.md` @ `f68a2ee15654`
  - `specs/ROADMAP.md` @ `a431f66680c9` (pre-READY projection)
  - `docs/API.md` @ `5a6799e0b9dd`
  - `docs/DATABASE.md` @ `c14d56a2a079`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/TESTING.md` @ `927a4a06f691`
  - `docs/adr/0005-workspace-scoped-teacher-memory.md` @ `1db4a620df31`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Evaluation dataset source and governance | Self-authored synthetic units shipped in-repo: three complete representative units — `travelling-around` (English output mode), `natural-disasters` (Chinese output mode), `cultural-heritage` (bilingual output mode). Each unit packages synthetic source documents, a scripted teacher interview answer sequence, and expected-evidence direction. The dataset carries an explicit permissive license dedication, a versioned dataset revision, and a SHA-256 manifest over every file; loading fails closed on any manifest mismatch. No private teacher or student content may enter the dataset. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D2 | Blocking vs diagnostic evidence classes | Blocking (any unmet criterion fails the evaluation pass): trace completeness, citation resolvability, artifact family completeness and structural/pairing validation, duplicate-submission idempotency, supersession safety, injected-failure recovery without duplicate billing, partial-render explicitness, memory-state pinning recorded. Diagnostic (recorded and displayed, never pass/fail, never sole authority): latency distributions, per-pass/per-artifact cost, alignment coverage depth, cross-pass variance magnitude, optional model-assisted quality opinion. A model-judge opinion can never prove a blocking criterion. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D3 | Live-model evidence scale and variance representation | Two complete live passes per unit (six live passes total), each a full pipeline execution against the live model provider. Every criterion is judged per pass; raw per-pass metrics are displayed side by side with no cross-pass normalization, averaging, or best-of masking. A criterion failed on any pass remains visible as failed for that pass. Provider/model configuration is snapshotted per pass; results from different configurations are never merged into one comparison. | `YMY / Project Owner`, 2026-09-01 (interactive selection; 2-pass value pinned interactively) |
| D4 | Fault-injection boundary | Faults are injected only in deterministic evaluation profiles (fake model adapter, eval-gated fault profiles honored only when the adapter is the fake one and an evaluation environment flag is set). Injected classes: provider transient failure, mid-run worker failure (in-task fault hook simulating process death, then Celery retry/resume), concurrent duplicate submission, stale-version supersession during an active run, and truncated-JSON partial render. Live passes are observe-only: real provider behavior is recorded, never induced. A real-worker stop/restart recovery demonstration runs once in the controlled live environment at delivery and is recorded as evaluation evidence, not as an automated CI case. | Resolved from evidence (TESTING.md risk map; AGENTS constraints); confirmed with Spec approval |
| D5 | Comparison baseline | Criterion-anchored absolute evaluation: blocking criteria are all-or-nothing against the definitions in this Spec, bound to (dataset revision, unit, confirmed versions, model configuration snapshot). No A/B model benchmark and no superiority claim; Multi-Agent retention is a Phase-1 portfolio requirement independent of measured superiority (ADR-0001). Diagnostic metrics are compared only across passes of the same unit, dataset revision, and configuration. | Resolved from evidence (ADR-0001; macro Spec open question); confirmed with Spec approval |
| D6 | Representative unit topics and criteria detail | Topics: Travelling Around (English), Natural Disasters (Chinese), Cultural Heritage (bilingual) — senior-high English course themes, entirely self-authored synthetic content. Detailed criteria are the D2 class definitions made concrete as C-TRACE-1, C-GROUND-1, C-ART-1, C-IDEM-1, C-SUPER-1, C-RECOV-1, C-RENDER-1, C-MEM-1 and diagnostic metrics M-LAT, M-COST, M-VAR, M-COVER, M-JUDGE (see Business Rules). | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D7 | Evaluation execution model | An evaluation pass is an asynchronous, owner-created run that sequences the existing module entrypoints exactly as the teacher-facing API would (source upload with dataset documents, scripted discovery/planning answers, brief/blueprint confirmation, lesson/deck/exercise generation, alignment read) and then computes criterion outcomes deterministically from recorded state (versions, runs, artifacts, trace events). It introduces no second workflow authority: LangGraph/Celery/PostgreSQL ownership is unchanged; the evaluation executor is a scripted client of existing services. Fault scenarios execute inside the evaluation task through eval-gated fault profiles. | Resolved from evidence (ARCHITECTURE.md module rules); confirmed with Spec approval |
| D8 | Teacher-memory pinning (ADR-0005) | Every evaluation pass records its memory configuration in the result: Phase 1 records `memory_state: empty (F013 not implemented)` — the harness neither creates nor consumes memory records. When F013 lands, the pinning field binds to a recorded memory-set revision or explicit empty state, and comparability rules require identical memory state across compared passes. | Resolved from evidence (ADR-0005; F013 Spec); confirmed with Spec approval |
| D9 | Narration stream token capture (F006 L-1) | The live model adapter requests stream usage (`stream_options.include_usage` or provider equivalent) for narration streams and records captured token usage and estimated cost into the existing trace-events pattern, completing per-pass cost evidence. If the provider cannot report stream usage, the affected component records explicit missing-evidence instead of zero. | Resolved from evidence (F006 review L-1; DATABASE.md NULL-means-not-recorded rule); confirmed with Spec approval |
| D10 | Result persistence and idempotency | Evaluation passes and their per-criterion outcomes are persisted rows bound to (project, dataset revision, unit, pass index, mode, scenario), created idempotently — a duplicate create returns the existing record and never re-executes the pipeline. Derived views (report, comparison) are read-side computations; stored rows are immutable once terminal. | Resolved from evidence (API.md idempotency rule; DATABASE.md authority rules); confirmed with Spec approval |
| D11 | Evidence surface | Technical-evaluation status and outcomes surface inside the existing layered evidence experience (summary region in the evidence panel) plus a dedicated print-styled technical evaluation report view, composing the F008 printable-report pattern. No new top-level workspace tab; no new visual language. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |

## Goal

Produce reproducible, version-bound technical evaluation evidence across three representative complete units — grounding, specialist orchestration, artifact integrity, alignment, idempotency, concurrency, cost, latency, and failure recovery — so the project's engineering claims are falsifiable through inspectable runs, traces, and criterion outcomes rather than a curated demo.

## Business Value

The portfolio becomes defensible: a reviewer can see, for fixed inputs and recorded configuration, exactly which technical claims passed, failed, or lack evidence, what resources they consumed, and how the system behaved under injected failure — without any teacher-usability claim being implied.

## User Story

As a portfolio reviewer or project owner, I want repeatable technical evaluation tied to complete traces, artifacts, and recorded configuration, so that I can assess the system's Agent and application engineering claims honestly.

## Scope

- Ship the self-authored synthetic evaluation dataset (D1) — three units, license-dedicated, manifest-verified, versioned — reused later by deployed portfolio samples (F012).
- Execute controlled evaluation passes: two live full-pipeline passes per unit (D3) plus deterministic fault-injection scenarios (D4), all sequenced through existing module entrypoints (D7).
- Compute and persist per-criterion outcomes: blocking classes C-TRACE-1, C-GROUND-1, C-ART-1, C-IDEM-1, C-SUPER-1, C-RECOV-1, C-RENDER-1, C-MEM-1 and diagnostic metrics M-LAT, M-COST, M-VAR, M-COVER, M-JUDGE (D2, D6), each bound to immutable sources, intent versions, runs, artifacts, model configuration snapshot, dataset revision, and trace references.
- Capture narration-stream token usage in the live adapter to complete cost evidence (D9).
- Record memory pinning state per pass (D8).
- Present evaluation status, per-criterion outcomes, cross-pass raw comparison, and cost/latency evidence through the layered evidence experience and a dedicated report view (D11).

## Out of Scope

- External teacher product validation or teacher-usability claims (`F010`).
- Replacing deterministic, integration, accessibility, or security tests with an LLM judge.
- Multi-model benchmarking, routing, fine-tuning, or generalized academic benchmarking.
- Public multi-account hardening and cloud-release proof (`F011`, `F012`); the dataset is reused by `F012` but not deployed here.
- Fault injection into live provider traffic (D4: live is observe-only).
- Any second workflow authority: evaluation never re-implements generation, planning, or recovery logic.

## Actors / Preconditions

- Actor: the authenticated workspace owner (project owner/evaluator). Evaluation is an owner surface, not a teacher classroom flow.
- Preconditions for creating an evaluation pass: the dataset package loads with a valid manifest; for live passes the model adapter is the live provider with valid credentials; for fault scenarios the deterministic profile (fake adapter + eval fault flag) is active.
- Preconditions for reading results: ownership of the evaluating workspace.

## Main Flow

1. The owner requests an evaluation pass for a dataset unit (and pass index); the system creates the idempotent evaluation record and executes the scripted pipeline (D7), snapshotting dataset revision, model configuration, and memory state (D8).
2. As each stage completes, the evaluation records evidence bindings (source ids, confirmed versions, run ids, artifact ids, trace references) and observes the recorded state.
3. On completion, the criteria engine computes blocking outcomes and diagnostic metrics deterministically (D2) and persists per-criterion results with evidence links (D10).
4. The owner inspects outcomes in the evidence experience summary and the evaluation report: per-criterion pass/fail/missing-evidence, side-by-side pass comparison, cost/latency evidence, and fault-scenario recovery outcomes (D3, D11).

## Alternative Flows

- Dataset manifest mismatch or unreadable unit: dataset loading fails closed; no evaluation pass starts; the error states the governance rule.
- Live provider unavailable mid-pass: the pass settles in the explicit provider-unavailable state with partial evidence retained; criteria that could not be evaluated record missing-evidence, not failure or success.
- Duplicate pass creation: the existing evaluation record is returned; the pipeline is not re-executed; no duplicate model cost (D10).
- Fault scenario produces an unexpected transition: the criterion records fail with the violating trace; the harness never repairs or retries around it silently.
- Dataset revision superseded: older evaluation results remain readable and display the superseded-configuration state; comparison across revisions or configurations displays comparison-unavailable (D3, D5).
- Evaluation while unrelated generation runs exist in the workspace: evaluation is isolated inside its own evaluation project; it never reads or mutates other projects' runs.

## Business Rules / Invariants

- Blocking criteria (evaluated per pass; any unmet criterion fails that pass):
  - C-TRACE-1 trace completeness: every model call, artifact write, retry, and recovery event in the pass is traceable through recorded trace/run events with correlation ids; no unattributed stage.
  - C-GROUND-1 citation resolvability: every citation recorded in the confirmed brief, blueprint, and artifacts resolves to an existing source chunk of the evaluating project.
  - C-ART-1 artifact family completeness: every lesson in confirmed blueprint scope has a complete, structurally validated lesson plan, slide deck, and exercise+answer pair that passes pairing validation.
  - C-IDEM-1 duplicate-submission idempotency: a concurrent duplicate generation start against the same confirmed versions returns the existing run; exactly one billed execution exists.
  - C-SUPER-1 supersession safety: a newer confirmed version during an active run supersedes at a safe checkpoint; the stale run never publishes over the newer version's artifacts.
  - C-RECOV-1 injected-failure recovery: an injected worker/provider failure resumes the same run from its checkpoint, preserves completed scope, and bills no duplicate model work for completed scope.
  - C-RENDER-1 partial-render explicitness: truncated or invalid model output produces an explicit validation failure and bounded recovery, never a fabricated success.
  - C-MEM-1 memory pinning recorded: the pass records its memory configuration (D8); missing recording is itself a failure of this criterion.
- Diagnostic metrics (recorded, displayed, never pass/fail): M-LAT per-stage latency distributions from trace events; M-COST per-pass and per-artifact estimated cost including narration streams (D9); M-VAR cross-pass variance magnitude per metric (same unit, revision, configuration only); M-COVER alignment findings severity distribution (F008 read model); M-JUDGE optional model-assisted quality opinion, always labeled, never load-bearing.
- Evaluation never mutates the sources, intent, runs, artifacts, or findings it measures; it creates its own evaluation project and reads recorded state.
- Every result is bound to dataset revision, unit, confirmed brief/blueprint versions, run ids, artifact ids, model configuration snapshot, memory state, and trace references sufficient for later inspection (D5).
- A failed or missing-evidence blocking criterion remains explicitly visible; no aggregate score may mask it; M-JUDGE can never prove a blocking criterion (D2).
- Technical evaluation outcomes say nothing about teacher product validation, which remains a separate, not-evaluated-until-F010 status.
- Evaluation passes persist within the owning workspace and are deleted with it; no cross-user evaluation corpus exists.
- Fault profiles are honored only when the fake adapter and the evaluation environment flag are both active (D4); production configurations can never inject faults.

## State Transitions

- Evaluation pass: `queued -> active -> partial_evidence -> completed | provider_unavailable | failed`. `completed` carries per-criterion outcomes and an overall pass/fail derived only from blocking criteria. Terminal states are immutable; provider_unavailable retains partial evidence and explicit resume guidance.
- Criterion outcome: `pass | fail | missing_evidence` with evidence links; missing_evidence never counts as pass.
- Display states over the recorded truth: not run, queued, active, partial evidence, pass, fail, missing evidence, provider unavailable, superseded configuration (a newer dataset revision or configuration exists), comparison unavailable (passes differ in revision/configuration/unit).
- Dataset revision: immutable once published; a new revision creates new passes and renders older results superseded-configuration, never rewritten.

## Data Changes

- New persisted owner data: evaluation pass records (project, dataset revision, unit key, pass index, mode live/deterministic, scenario `full_pipeline` or `fault:<name>`, model configuration snapshot, memory state, status, evidence bindings, timestamps) and per-criterion result rows (criterion key, classification, outcome, measured values, evidence references). Audit follows the existing audit-events pattern.
- No changes to existing domain tables other than the narration-usage capture extension of trace events (D9, additive columns or equivalent within the existing trace pattern).
- Exact table names, columns, indexes, and migration steps are finalized by the Implementation Plan; deletion cascades with the project cover all F009-added rows.

## API Behavior

- `GET /projects/{id}/technical-evaluation` — owner-authorized overview: dataset revision, units, passes with states, latest overall outcomes, comparison availability.
- `POST /projects/{id}/technical-evaluation/runs` — create an evaluation pass (unit key, pass index, mode); idempotent per (project, dataset revision, unit, pass index, mode, scenario) (D10).
- `GET /projects/{id}/technical-evaluation/runs/{evaluation_run_id}` — per-criterion outcomes with evidence links, diagnostic metrics, fault-scenario results.
- `GET /projects/{id}/technical-evaluation/report` — report data across the evaluation set for the print-styled report view (D11).
- Progress exposure follows the existing run-event/SSE pattern; evaluation events carry owner-authorized context and never stream private content of other projects.
- Error semantics follow the project taxonomy: requirement (unknown unit, malformed pass request, dataset governance failure), authorization-not-found (cross-workspace), provider-transient (live provider unavailability recorded explicitly), quota (evaluation project creation subject to workspace quota; the evaluation environment may raise quotas via configuration without changing product defaults).

## Error Cases

- Dataset manifest mismatch or unlicensed file: requirement error naming the governance rule; no pass starts.
- Live pass without live adapter/credentials: requirement error before any model spend.
- Provider failure mid-pass: pass settles provider_unavailable with partial evidence; resume reuses the same idempotent pass (D10), never a silent fresh pass.
- Criterion cannot be evaluated (e.g., stream usage unsupported by provider): outcome missing_evidence with the precise reason (D9); never zero, never pass.
- Cross-workspace read of any evaluation endpoint: authorization-denied without existence disclosure.

## Idempotency / Concurrency / Transactions

- Evaluation pass creation is DB-enforced idempotent on its identity tuple; concurrent duplicate creates converge on one record and one pipeline execution (D10).
- Duplicate-submission observation (C-IDEM-1) itself exercises the existing generation-run uniqueness under concurrency inside the evaluation project.
- Criterion computation is a deterministic read-side computation over recorded state; identical recorded state always yields identical outcomes.
- A dataset revision publish while passes are active does not mutate active passes; new passes bind the new revision.

## Security / Privacy / Authorization

- All F009 endpoints and evidence are workspace-authorized; evaluation records, reports, and metrics never cross workspaces and are deleted with the project.
- The dataset contains only self-authored synthetic content (D1); no teacher or student private material may enter it, enforced by the manifest governance rule.
- Fault profiles are configuration-gated to deterministic evaluation environments and cannot be activated in production settings (D4).
- No public MCP surface, no cross-user evaluation data, no model-training use of dataset or run content.

## Non-functional

- No new infrastructure product, cache, queue, second database, or second model: the harness is code plus configuration over existing FastAPI/Celery/LangGraph/PostgreSQL/storage components (D7).
- Deterministic evaluation scenarios (fake adapter) run in the standard test environment; live passes run in the controlled live environment separately from deterministic suites (TESTING.md separation rule).
- Live evidence cost is bounded by definition: exactly two passes per unit plus one real-worker recovery demonstration (D3, D4).
- Report rendering composes the F008 printable-report pattern; no new rendering dependency.

## UI Impact

- UI involved: `YES`
- Affected screens: technical-evaluation summary region inside the existing evidence panel; dedicated print-styled technical evaluation report view (D11).
- Primary flow: view evaluation overview -> inspect pass outcomes and evidence -> compare passes -> open report (print).
- Major UI states: not run, queued, active, partial evidence, pass, fail, missing evidence, provider unavailable, superseded configuration, comparison unavailable.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given the evaluation dataset package, when loaded, then each of the three units (`travelling-around` English, `natural-disasters` Chinese, `cultural-heritage` bilingual) carries its license dedication, dataset revision, and SHA-256 manifest; any manifest mismatch or unlicensed file fails loading closed.
- AC-002: Given a completed evaluation pass, when its result is read, then it is bound to its dataset revision, unit, immutable source records, confirmed brief and blueprint versions, run ids, artifact ids, model configuration snapshot, memory state, and trace references.
- AC-003: Given a completed pass, when the criteria engine runs, then every blocking criterion yields `pass | fail | missing_evidence` with deterministic evidence links, and identical recorded state always produces identical outcomes.
- AC-004: Given a concurrent duplicate generation start inside an evaluation pass, when both submissions land, then exactly one run is created and billed, and C-IDEM-1 records the duplicate-submission evidence.
- AC-005: Given a newly confirmed version while a generation run is active in an evaluation scenario, when supersession executes, then the stale run never publishes over the newer version and C-SUPER-1 records the safe-checkpoint evidence.
- AC-006: Given an injected worker or provider failure during an evaluation scenario, when recovery executes, then the same run resumes from its checkpoint, completed scope is preserved, no duplicate billing occurs for completed scope, and C-RECOV-1 records the recovery trace.
- AC-007: Given a truncated or invalid model response injected in a deterministic scenario, when the pipeline processes it, then an explicit validation failure with bounded recovery is recorded and C-RENDER-1 never records success for fabricated content.
- AC-008: Given any evaluation pass, when configuration is snapshotted, then the memory pinning state is recorded (Phase 1: empty, F013 not implemented) and C-MEM-1 evaluates the recording itself.
- AC-009: Given the live evaluation set, when execution completes, then each unit has exactly two live passes recorded with per-pass criterion outcomes and raw side-by-side metrics, with no cross-pass normalization and no failure masked by another pass.
- AC-010: Given any failed or missing-evidence blocking criterion, when the report or evidence view is opened, then the failure remains explicit and is not masked by any aggregate value, and diagnostic metrics are visibly labeled non-blocking.
- AC-011: Given a model-assisted opinion recorded as M-JUDGE, when outcomes are computed, then it is labeled diagnostic and no blocking criterion outcome derives from it alone.
- AC-012: Given narration streams in a live pass, when token usage is reported by the provider, then usage and estimated cost are captured into trace events; where the provider cannot report stream usage, the component records explicit missing-evidence instead of zero.
- AC-013: Given the evidence experience, when evaluation data exists, then the summary region shows pass states and latest outcomes with the full state vocabulary, and the report view renders per-criterion outcomes, comparison availability, and cost/latency evidence in a print-styled layout bound to the evaluated versions.
- AC-014: Given comparison requests across differing units, dataset revisions, or model configurations, when the report computes comparison, then it displays comparison-unavailable instead of merging incomparable passes.
- AC-015: Given a non-owner or unauthenticated requester, when any F009 endpoint is called, then no content or existence is disclosed; given project deletion, all F009 rows and derived objects are removed with the workspace.

## Open Questions

All five DRAFT open questions and the blocking refinement questions are resolved (D1–D11 above; Issue #18 bound 2026-09-01). Non-blocking residuals:

- [DEFERRED, Implementation Plan] Exact table shapes, dataset package placement, harness CLI surface, and fault-profile configuration keys.
- [DEFERRED, revisit at F013] Bind memory pinning to recorded memory-set revisions once teacher memory exists.
- [DEFERRED, revisit at F012] Reuse of the dataset as deployed portfolio sample input.
- [DEFERRED, delivery-time evidence] The single real-worker stop/restart recovery demonstration executes in the controlled live environment at delivery (D4), recorded in the Test Design execution evidence snapshot.

## Risks and Assumptions

- [CONFIRMED] Technical success is independent from teacher product validation; both statuses stay separately visible (ADR-0001).
- [CONFIRMED] Multi-Agent retention is not contingent on measured superiority; no A/B benchmark is attempted (ADR-0001, D5).
- [CONFIRMED] Deterministic suites and live-model evidence stay separated; fake adapter is mandatory for injected scenarios (TESTING.md, D4).
- [ASSUMED] The live provider reports stream usage for narration (D9); if not, missing-evidence is recorded honestly and cost evidence is partial-by-provider-limitation, not by omission.
- [ASSUMED] Two passes per unit give adequate Phase-1 variance evidence; no statistical generalization is claimed (D3).
- [ASSUMED] The evaluation environment may raise workspace project quotas by configuration for its dedicated evaluation projects without changing product defaults.

## Deliberately Deferred Detail

- DTO shapes, exact response schemas, and error code strings (Implementation Plan + API doc sync)
- Table/column definitions, indexes, and migration steps (Implementation Plan)
- Dataset file layout, harness CLI commands, and fault-profile key names (Implementation Plan)
- Pixel-level UI and complete Test Design (`ux-ui.md`, `test-design.md`)

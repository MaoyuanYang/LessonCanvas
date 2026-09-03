# F016: Specialist Role Expansion

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P1`
- Owner: `YMY / Project Owner`
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F014` (chunk-level retrieval and hash-bound citations are what make grounded review meaningful); may additionally consume `F015` when available (soft)
- Last Updated: 2026-09-03 (initial draft, Phase-2 planning)

## Goal

Make the specialist division of labor real: add source-analysis, activity-design, and quality-review specialists so that grounding, design, drafting, and review are distinct model roles with their own contracts, traces, and gates — instead of one writer call per workflow with everything else as deterministic code.

## Business Value

Each stage of preparation gets a role whose output is inspectable and improvable on its own: sources are analyzed before they are used, lesson activities are designed against objectives and evidence rather than being a side-effect field of a plan draft, and drafts receive a model-assisted quality review before delivery — with every stage's cost and latency visible in the existing evidence panel.

## User Story

As a senior-high English teacher, I want the system to analyze my materials, design each lesson's activities deliberately, and review the drafted plan against my objectives and sources before I see it, so that what reaches me has already been checked for coverage and grounding — and I can see who did what, at what cost.

## Background

Baseline observed on `main` (capability audit, 2026-09-03):

- The lesson-plan graph's "three-specialist split" is unit-context assembler (code), lesson-plan writer (the single model call), renderer/validator (code) — `modules/artifact_production/graph.py`; deck and exercise graphs have one writer each.
- Sources and Grounding is fully deterministic (parsing, regex privacy screening, fixed 1000-character chunking); no model role ever analyzes a source. The nearest thing is discovery's requirements-side gap analysis over the corpus.
- Activities are a field of the plan writer's output, not a designed intermediate artifact.
- Quality review today is deterministic structural validation (the renderers' own validators state they "do not judge content quality") plus imported external teacher reviews (F008 alignment and F010 product validation are deliberately zero-model-call modules — their authority is unchanged by this Feature).

## User Flow

1. A teacher's uploaded source, once parsed and embedded (F014), receives a structured analysis from the source-analysis specialist — topics, language points, suitability flags, key passages with chunk references — stored per source and visible in the workspace (timing per D1).
2. Discovery and planning consume the analyses as labeled subordinate context alongside retrieved chunks.
3. Lesson-plan generation becomes designer → writer: the activity-design specialist produces a per-lesson structured activity/assessment design bound to blueprint objectives and cited evidence; the plan writer assembles the full plan from that design.
4. After the writer, the quality-review specialist produces structured findings (objective coverage, grounding against cited chunks, internal consistency) with severity; on failure the draft gets exactly one bounded revise round carrying the findings back to the writer.
5. Deterministic structural validation remains the final gate before rendering; review findings and stage costs surface in the layered evidence panel.

## Requirements

- Source-analysis specialist: one bounded model call per source (or chunk cluster, per D1), output server-side normalized as untrusted input, stored in a `source_analyses` table with version-free latest-wins semantics (per D1), registered in the F011 deletion sweep; analysis failure never blocks source availability.
- Activity-design specialist: per-lesson structured design (activities, assessment, timing) validated against blueprint objectives; the design becomes a first-class intermediate artifact of the run with its own trace events.
- Quality-review specialist: structured findings with severity classes; at most one revise round per draft (policy per D3); the final state honestly distinguishes review-passed from failed-after-revise; review cannot alter confirmed intent or skip deterministic validation.
- Each new stage carries its own role label, latency, token, and estimated-cost trace attribution; per-run model-call caps and quota classification are updated so the added calls are bounded and explicit (F003 cap contract, F011 quotas; values per D5).
- Memory context (F013) injection extends to the new specialists as subordinate, budgeted context (per D6).
- F009: the pass-comparability signature includes the specialist stage set; deterministic criteria extended only where judgment stays deterministic (e.g. stages executed and traced, revise-round count) — no model-judged evaluation criteria (per D7).
- Teacher-visible honesty: stage progress, review findings, and per-stage cost render through the existing evidence surfaces; no stage is reported as another.

## Edge Cases

- Source-analysis call fails (provider/transient): the source remains usable; analysis shows a visible failed state with retry; discovery/planning proceed without analyses (disclosed).
- Designer output fails objective validation: one bounded designer retry, then an honest stage failure following the existing run failure taxonomy; existing per-lesson checkpoint semantics preserve completed lessons.
- Reviewer finds severe issues twice: draft settles as failed-after-revise with findings visible; the run's failure state names the review stage; no infinite revise loop.
- Cost cap reached mid-stages: existing cap semantics apply; the run settles honestly (partial failure) with per-stage accounting intact.
- Deck/exercise families before D2 resolution: unchanged single-writer behavior (no silent divergence from their Specs).

## API / Data Changes

- New table family `source_analyses` (workspace/project-scoped, deletion-swept); artifact-run surfaces gain the design intermediate and review findings in existing run/artifact payloads; no new top-level API areas expected (contract updates recorded in `docs/API.md` at SPEC READY).

## Acceptance Criteria

- [ ] AC-001 A parsed source receives a structured analysis (or a visible failed state with retry) that discovery/planning consume as labeled context; analyses are deleted with the workspace.
- [ ] AC-002 Lesson-plan generation executes design → write → review as separately traced stages, each with its own role label, latency, tokens, and estimated cost.
- [ ] AC-003 Review findings with severity are recorded per draft; at most one revise round runs; final states distinguish review-passed and failed-after-revise honestly.
- [ ] AC-004 Deterministic structural validation is unchanged and still mandatory before rendering; review never modifies confirmed intent.
- [ ] AC-005 Per-run caps and quotas bound the added stage calls with explicit errors; per-stage cost is visible in the evidence panel.
- [ ] AC-006 The F009 comparability signature includes the specialist stage set, and deterministic evaluation scenarios cover stage failure and revise-round paths.

## Incremental Development Roadmap

### Step 1: Source-analysis specialist

- **Goal:** analyzed sources feed discovery/planning as visible subordinate context.
- **Scope:** `source_analyses` table + migration, analysis call in the sources pipeline (timing per D1), normalization, evidence surface, deletion sweep registration.
- **Tests:** analysis contract, failure/retry, injection discipline, deletion completeness.
- **Verification:** an uploaded source shows an analysis (or honest failure) in the workspace.

### Step 2: Activity-design stage in the lesson-plan path

- **Goal:** designer → writer split with the design as a traced intermediate.
- **Scope:** lesson-plan graph node insertion, design schema normalization, objective validation.
- **Tests:** design contract, validation failure paths, checkpoint semantics preserved.
- **Verification:** a generation run's trace shows design and write stages separately.

### Step 3: Quality-review stage + bounded revise

- **Goal:** structured review findings, one revise round, honest terminal states.
- **Scope:** reviewer node, findings schema, revise wiring, run-state integration.
- **Tests:** pass/fail-after-revise paths, cap interplay, no-bypass of deterministic validation.
- **Verification:** a seeded weak draft (fake adapter) is revised once and its findings are visible.

### Step 4: Caps, memory, evaluation, docs

- **Goal:** bounded cost, memory injection, F009 signature/scenarios, documentation sync.
- **Scope:** cap/quota updates, memory-context extension (D6), technical_evaluation updates, docs.
- **Tests:** cap exhaustion mid-stages; F009 deterministic scenarios; adversarial re-checks.
- **Verification:** owner-authorized live evidence at delivery; all docs match behavior.

## Test Plan

Deterministic backend tests per stage (contract, failure, revise, caps, deletion, injection); F009 deterministic scenarios extended for stage set and revise paths; web component tests for any evidence-panel additions; owner-authorized live evidence at delivery. Commands: `uv run pytest`, `uv run ruff check src tests migrations`, `corepack pnpm web:test` (+ `web:typecheck`, `web:lint`) if web surfaces change.

## Open Questions

- D1 Source-analysis trigger and shape: upload-time async vs lazy at first discovery; per-source vs per-chunk-cluster; storage semantics (latest-wins vs versioned).
- D2 Reviewer scope: lesson plans only (leading) vs extending to deck and exercise families (and whether they also consume the activity design).
- D3 Revise policy: always one revise round on any failed review vs severity-gated (only severe findings trigger).
- D4 Designer/writer contract granularity and whether the design becomes teacher-visible/editable before writing (leading: visible in evidence only; not teacher-editable in Phase 2).
- D5 Per-lesson call growth (design + write + review ± revise): cap values and quota classification for the new calls.
- D6 Memory-context injection into the new specialists (budget priority relative to the F013 order).
- D7 F009 re-baselining and whether any new deterministic criterion (e.g. "review stage executed and traced") joins the blocking set.

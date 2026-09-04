# F016: Specialist Role Expansion

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P1`
- Owner: `YMY / Project Owner`
- Decision Authority: `YMY / Project Owner`
- Work Item: [GitHub Issue #32](https://github.com/MaoyuanYang/LessonCanvas/issues/32) — bound 2026-09-04 (authorized); work-status authority.
- Dependencies: `F014` (chunk-level retrieval and hash-bound citations are what make grounded review meaningful); consumes `F015` capabilities softly (the tool-loop primitive exists but no new specialist binds tools in this Feature)
- Last Updated: 2026-09-04 (SPEC READY approved; D1–D7 resolved)

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-04
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-04 (question-form answers: D5 cap formula confirmed with recommended values, D6 memory injection into designer **and reviewer** selected (owner override of the designer-only recommendation), D7 F009 signature/criteria/re-baseline confirmed, D4 leading adopted with explicit SPEC READY approval; D1–D3 owner-selected at selection the same day), scope: F016 Spec @ `f37d7519f8f9`
- Baseline re-verified on `main` during refinement: backend full suite exit-0 + ruff clean (run against the isolated `lessoncanvas_test` database with `infra/deploy.env` credential overrides — the currently running local services are the F012 deployed stack and `apps/backend/.env` credentials are stale against it); web 114/114 + tsc clean + eslint 0 errors (3 pre-existing warnings).
- Checklist: 11/11 YES (Goal/Scope incl. explicit Out-of-Scope, Flows incl. analysis-failure, design-retry, revise and failed-after-revise paths, Rules/States incl. severity-gated revise rule and `reviewing` status, Data/API incl. `source_analyses` table + design/findings columns + new trace event kinds + formula-cap settings with no new top-level API areas, Errors/Security incl. untrusted-input discipline on analyses/design/findings, Idempotency/Concurrency incl. one-in-flight analysis and revise-round bound with existing per-run cap accounting, Dependencies/Migration incl. deploy-time analysis backfill and `lessoncanvas_test` reuse, Non-functional incl. per-stage cost attribution and F009 comparability, unique observable ACs AC-001..AC-006, OBSERVED baseline inventory retained in Background, no unresolved conflicts, no Critical Open Question OPEN/DEFERRED; UI presentation details routed to the UI READY gate)
- Related artifacts: work item [Issue #32](https://github.com/MaoyuanYang/LessonCanvas/issues/32)

## Goal

Make the specialist division of labor real: add source-analysis, activity-design, and quality-review specialists so that grounding, design, drafting, and review are distinct model roles with their own contracts, traces, and gates — instead of one writer call per workflow with everything else as deterministic code.

## Business Value

Each stage of preparation gets a role whose output is inspectable and improvable on its own: sources are analyzed before they are used, lesson activities are designed against objectives and evidence rather than being a side-effect field of a plan draft, and drafts receive a model-assisted quality review before delivery — with every stage's cost and latency visible in the existing evidence panel.

## User Story

As a senior-high English teacher, I want the system to analyze my materials, design each lesson's activities deliberately, and review the drafted artifacts against my objectives and sources before I see them, so that what reaches me has already been checked for coverage and grounding — and I can see who did what, at what cost.

## Background

Baseline observed on `main` (capability audit, 2026-09-03):

- The lesson-plan graph's "three-specialist split" is unit-context assembler (code), lesson-plan writer (the single model call), renderer/validator (code) — `modules/artifact_production/graph.py`; deck and exercise graphs have one writer each.
- Sources and Grounding is fully deterministic (parsing, regex privacy screening, fixed 1000-character chunking); no model role ever analyzes a source. The nearest thing is discovery's requirements-side gap analysis over the corpus.
- Activities are a field of the plan writer's output, not a designed intermediate artifact.
- Quality review today is deterministic structural validation (the renderers' own validators state they "do not judge content quality") plus imported external teacher reviews (F008 alignment and F010 product validation are deliberately zero-model-call modules — their authority is unchanged by this Feature).
- F015's bounded tool loop (`discovery_planning/tool_loop.py`) is generic over tools but bound only to the planning drafting specialist; F014's retrieval (`sources_grounding/retrieval.py`) returns top-k chunks with budget trim, exclusion disclosure, and hash-bound server-injected citations.

## User Flow

1. A teacher's uploaded source, once the parse task settles successfully (chunks exist; per-chunk embedding attempts complete), receives a structured analysis from the source-analysis specialist — topics, language points, suitability flags, key passages with chunk references — stored per source (latest-wins) and visible in the workspace with its own cost line (D1).
2. Discovery and planning consume the analyses as labeled subordinate context alongside retrieved chunks; absent or failed analyses are disclosed, never fabricated.
3. Lesson-plan generation becomes designer → writer: the activity-design specialist produces a per-lesson structured activity/assessment design bound to blueprint objectives and the lesson's retrieved evidence; the plan writer assembles the full plan from that design. The design is a traced intermediate visible in evidence, not teacher-editable in Phase 2 (D4).
4. After the writer, in every artifact family (plans, decks, exercises), the quality-review specialist produces structured findings (objective/plan coverage, grounding against the artifact's cited chunks, internal consistency) with severity; only severe findings trigger exactly one bounded revise round carrying the findings back to the writer, followed by one re-review; a second severe round settles the draft as failed-after-revise (D2, D3).
5. Deterministic structural validation remains unchanged and mandatory after rendering; review never skips it. Review findings, stage progress, and per-stage cost surface through the existing layered evidence surfaces.

## Requirements

### Source-analysis specialist (D1)

- One bounded model call per source, enqueued asynchronously via Celery when the parse task settles successfully; per-chunk embedding failures do not gate the analysis (it reads chunk text, not vectors) and remain disclosed through the F014 retrieval-exclusion path.
- One analysis in flight per source; a manual retry action re-enqueues after failure. Latest-wins storage; no version history.
- New `source_analyses` table (project-scoped): status (`pending` / `analyzing` / `ready` / `failed`), normalized analysis payload, latest-attempt telemetry (model label, latency, prompt/completion tokens, estimated cost — same honesty rules as TraceEvent: missing tokens ⇒ cost not recorded), finished-at.
- Output normalized server-side as untrusted input: bounded field lengths and counts; key passages must reference chunk positions that exist in the source; nothing from the payload enters a system prompt. Analyses are model output over untrusted source text and inherit the untrusted-input discipline of retrieved text (labeled JSON user payload only).
- Analysis failure never blocks source availability; discovery/planning proceed without the analysis, with the absence disclosed (`source_analyses_state`: `ready` / `partial` / `none` with reasons).
- Discovery and planning payloads gain a bounded `source_analyses` section (per ready source, within a settings char budget) consumed as labeled subordinate context; analysis content never overrides confirmed intent.
- Registered in the F011 deletion sweep; deleted with the workspace/project. Not run-owned: no TraceEvent rows; cost surfaces on the source's analysis surface, not in run summaries.
- Deploy-time idempotent backfill (F014 D2 precedent): existing ready sources without an analysis are analyzed once at deploy, skipping sources already settled; the F009 seeded sources are covered by the same path so live re-baseline passes run with analyses present.

### Activity-design specialist (lesson-plan path, D4)

- New per-lesson design stage before the writer in the plans graph: structured design covering objectives covered (blueprint objective ids), activities (name, type, description, timing), assessment approach, and evidence references drawn from the lesson's retrieved chunk set.
- Deterministic design validation: every referenced objective id exists in the lesson's blueprint objective set; activity count and per-activity timing within settings bounds; evidence references resolve to the retrieved set for that lesson. Validation failure ⇒ one bounded designer retry (a corrective second call), then an honest stage failure under the existing run-failure taxonomy; completed lessons keep their per-lesson checkpoints.
- The design is a first-class intermediate of the run: stored on the lesson-plan artifact row (`design_json` + design status), traced as `model.generation_design_lesson` with role label, latency, tokens, estimated cost.
- The design is teacher-visible in evidence only; not teacher-editable and not confirmable in Phase 2 (D4).
- Memory context (F013) injected as subordinate, budgeted context with the existing priority order (D6).

### Quality-review specialist (all three artifact families, D2/D3)

- A review stage between the writer draft and rendering in the plans, decks, and exercises graphs. Deck and exercise writers keep their existing input contracts; they do not consume the activity design (D2).
- Reviewer output: structured findings, each with a fixed dimension (`objective_coverage` / `plan_coverage` for decks and exercises / `grounding` / `consistency`), severity (`severe` / `minor`), bounded message, and optional reference (blueprint objective id or cited chunk hash); findings count bounded; server-side normalized as untrusted input. Reviewer receives the draft, the owning confirmed intent digest (blueprint objectives for plans; the prerequisite plan content for decks/exercises), the artifact's retrieved chunk set with citations, and the same budgeted memory context as the writer (D6 — subordinate, never overriding confirmed intent or evidence anchors).
- Review rule (D3): no severe findings ⇒ `review-passed` (minor findings recorded and disclosed). Any severe finding ⇒ exactly one revise round: the writer receives the original draft plus the labeled findings and produces a revised draft, then one re-review call. Severe findings in the re-review ⇒ the draft settles `failed-after-revise`; the artifact's failure state names the review stage; the run settles under the existing per-lesson failure semantics (completed lessons preserved). No further revise rounds under any condition.
- Trace events: `model.generation_review_lesson` / `model.generation_review_deck` / `model.generation_review_exercises` (payload round 1/2), `model.generation_revise_lesson` / `model.generation_revise_deck` / `model.generation_revise_exercises`; findings stored on the artifact row (latest round) and surfaced in run/artifact payloads.
- Review never modifies confirmed intent (brief/blueprint versions), never alters source ownership, and never replaces or defers deterministic structural validation, which stays mandatory after rendering. Artifact status set gains `reviewing` (covers review and revise rounds); no status is ever reported as another.

### Caps, quotas, and cost (D5)

- Every new stage model call (design, review, revise, re-review included in the revise round) is preceded by the existing per-run `reserve_model_call` reservation; exhaustion keeps the existing cap semantics (`capped_failure`, honest partial failure with per-stage accounting intact).
- Per-run caps become formula-based at run creation: plans `5 × lesson_count + slack`, decks `4 × lesson_count + slack`, exercises `4 × lesson_count + slack` (design+write+review+revise+re-review = 5; write+review+revise+re-review = 4), with multipliers and slack (2) as settings; the existing flat settings remain as a floor (20). Values confirmed at SPEC READY.
- Source-analysis calls are not run-owned and outside per-run caps: bounded by construction (one call per source per trigger, one in flight per source, manual retry only). Classified under upload processing like F014 embedding (no new quota class); retries are re-billed and disclosed (latest-wins telemetry shows the current attempt).

### F009 technical evaluation (D7)

- `model_config_snapshot()` gains a `stage_set` entry describing the per-family stage composition (e.g. plans `["design","write","review","revise","re_review"]`, decks/exercises `["write","review","revise","re_review"]`); existing passes become visibly incomparable with new ones through the existing signature mechanism.
- The evaluation pass pins a source-analysis state snapshot of the seeded sources (per source: analysis status) alongside the existing memory-state snapshot, so passes with divergent analysis availability cannot compare silently (F013 precedent); the evaluation harness settles seeded-source analyses before running passes.
- Deterministic criteria only, no model-judged evaluation: a new blocking criterion verifies per completed artifact that the family's stages executed and were traced, revise rounds ≤ 1, and review strictly precedes render; new fault scenarios (`fault:review_fail` — severe findings twice, honest failed-after-revise; `fault:design_invalid` — invalid design, one retry, honest stage failure) join the deterministic scenario set.
- Full live re-baseline of the six F009 passes under the new stage set at delivery, under separate owner authorization.

### Honesty

- Stage progress, findings, revise disclosure, and per-stage cost render through the existing evidence surfaces and per-family panels; the reviewing state, revise rounds, and the failed-after-revise terminal state are explicit and never folded into another status.

## Edge Cases

- Source-analysis call fails (provider/transient): the source remains usable; analysis shows a visible failed state with retry; discovery/planning proceed without analyses (disclosed).
- Designer output fails objective validation: one bounded designer retry, then an honest stage failure following the existing run failure taxonomy; existing per-lesson checkpoint semantics preserve completed lessons.
- Reviewer finds severe issues twice: the draft settles failed-after-revise with findings visible; the artifact failure state names the review stage; no infinite revise loop.
- Reviewer returns minor-only findings: recorded and disclosed; the draft proceeds review-passed without a revise round.
- Reviewer/revise output itself fails to parse or normalize: treated as a retryable stage failure under the existing taxonomy (bounded per-attempt retry, then honest failure); never silently accepted as a pass.
- Cost cap reached mid-stages: existing cap semantics apply; the run settles honestly (`capped_failure` / partial) with per-stage accounting intact.
- Duplicate analysis trigger (retry while analyzing, or parse settling twice): rejected by the one-in-flight rule; latest-wins on completion.

## Out of Scope

- Teacher-editable or confirmable design/findings: evidence-visible only in Phase 2 (D4).
- Binding tools to any new specialist (F015 loop stays planning-only) and making semantic retrieval model-callable (stays orchestration-issued).
- Any change to F008 alignment or F010 product-validation authority (still zero-model-call, imported judgment).
- Agent-to-Agent conversation, specialist-chosen orchestration, or any second model/provider.
- Model-judged F009 evaluation criteria.
- Source-analysis consumption inside the generation families (generation keeps per-lesson retrieval + design as its grounding inputs).
- Deck/exercise consumption of the activity design (their writer input contracts are unchanged).
- New top-level API areas, new top-level UI surfaces, or a design/finding editing surface.

## API / Data Changes

- New table `source_analyses` (project-scoped, deletion-swept) with status, normalized payload, latest-attempt telemetry; a retry action on the source's analysis surface.
- Lesson-plan artifact rows gain `design_json` + design status; all three families' artifact rows gain review findings (latest round) + round count; artifact status vocabulary gains `reviewing`.
- New trace event kinds: `model.generation_design_lesson`, `model.generation_review_lesson|deck|exercises`, `model.generation_revise_lesson|deck|exercises`.
- Source read surfaces expose the analysis state/digest/telemetry; run/artifact payloads expose design and findings; the F009 pass signature gains `stage_set` and a pinned source-analysis state snapshot.
- Contract details recorded in `docs/API.md` and `docs/DATABASE.md` at implementation; no new top-level API areas.

## Acceptance Criteria

- [ ] AC-001 A parsed source receives a structured analysis (or a visible failed state with retry) that discovery/planning consume as labeled, disclosed context; analyses are deleted with the workspace.
- [ ] AC-002 Lesson-plan generation executes design → write → review as separately traced stages, and deck/exercise generation executes write → review, each stage with its own role label, latency, tokens, and estimated cost.
- [ ] AC-003 Review findings with severity are recorded per draft; at most one revise round runs and only severe findings trigger it; final states distinguish review-passed (possibly with minor findings) and failed-after-revise honestly.
- [ ] AC-004 Deterministic structural validation is unchanged and still mandatory after rendering; review never modifies confirmed intent.
- [ ] AC-005 Formula-based per-run caps and the one-call-per-source bound cap the added calls with explicit errors; per-stage cost is visible in the evidence panel and source-analysis cost on its own surface.
- [ ] AC-006 The F009 comparability signature includes the specialist stage set (plus the pinned source-analysis state); deterministic evaluation scenarios cover design-failure, review-failure, and revise-round paths.

## Incremental Development Roadmap

### Step 1: Source-analysis specialist

- **Goal:** analyzed sources feed discovery/planning as visible subordinate context.
- **Scope:** `source_analyses` table + migration, analysis prompt/normalization/fake-adapter kind, Celery trigger at parse settlement, one-in-flight + retry, telemetry, discovery/planning labeled consumption with disclosure, deletion sweep, sources web surface.
- **Tests:** analysis contract, failure/retry, injection discipline, consumption disclosure, deletion completeness.
- **Verification:** an uploaded source shows an analysis (or honest failure with retry) in the workspace, with its cost line.

### Step 2: Activity-design stage in the lesson-plan path

- **Goal:** designer → writer split with the design as a traced intermediate.
- **Scope:** plans-graph stage insertion, design schema normalization, objective/evidence validation with one bounded retry, artifact-row design storage, memory injection.
- **Tests:** design contract, validation failure paths, checkpoint semantics preserved, memory budget.
- **Verification:** a generation run's trace shows design and write stages separately with per-stage cost.

### Step 3: Quality-review stage + severity-gated revise (all three families)

- **Goal:** structured review findings, one severe-gated revise round, honest terminal states.
- **Scope:** reviewer stages in the plans/decks/exercises graphs, findings schema, revise + re-review wiring, `reviewing` status, run-state integration.
- **Tests:** review-passed (incl. minor-only), revise-pass, failed-after-revise paths, parse-failure of reviewer output, cap interplay, no-bypass of deterministic validation.
- **Verification:** a seeded weak draft (fake adapter) is revised once and its findings are visible; a twice-severe draft settles failed-after-revise naming the review stage.

### Step 4: Caps, memory, evaluation, web, docs

- **Goal:** bounded cost, memory injection, F009 signature/scenarios, evidence surfaces, documentation sync.
- **Scope:** formula caps at run creation, upload-processing classification, F009 `stage_set` + analysis-state snapshot + criteria + fault scenarios, evidence-panel stage labels/chips and findings display, sources-surface analysis region, narration sentences, docs.
- **Tests:** cap exhaustion mid-stages; F009 deterministic scenarios; adversarial re-checks; web component tests.
- **Verification:** owner-authorized live evidence at delivery (full F009 re-baseline); all docs match behavior.

## Test Plan

Deterministic backend tests per stage (contract, failure, revise, caps, deletion, injection, memory); F009 deterministic scenarios extended for stage set, design/review faults, and revise paths; web component tests for evidence-panel/sources-surface additions; owner-authorized live evidence at delivery (F009 re-baseline + a live source-analysis/design/review journey). Commands: `uv run pytest`, `uv run ruff check src tests migrations`, `corepack pnpm web:test`, `corepack pnpm web:typecheck`, `corepack pnpm web:lint`.

## Decision Log

| ID | Question | Resolution | Authority | Date |
| --- | --- | --- | --- | --- |
| D1 | Source-analysis trigger and shape | Parse-settlement async trigger (Celery), one bounded call per source, latest-wins, one in flight, manual retry; embedding failures do not gate it | `YMY / Project Owner` (selected at F016 selection, interactive question form) | 2026-09-04 |
| D2 | Reviewer scope | Reviewer in all three artifact families; designer stays in the plans path; deck/exercise writers keep existing inputs and do not consume the design | `YMY / Project Owner` (selected at F016 selection, interactive question form) | 2026-09-04 |
| D3 | Revise policy | Severity-gated: only severe findings trigger the single revise round (writer revise + one re-review); second severe round settles failed-after-revise; minor-only findings recorded and disclosed without revise | `YMY / Project Owner` (selected at F016 selection, interactive question form) | 2026-09-04 |
| D4 | Design visibility/editability | Evidence-visible only; not teacher-editable or confirmable in Phase 2 | Leading option adopted in refinement; confirmed with SPEC READY (`YMY / Project Owner`) | 2026-09-04 |
| D5 | Cap values and quota classification | Formula caps: plans `5×lessons+slack`, decks/exercises `4×lessons+slack` (slack 2; settings-driven multipliers/slack, flat settings as floor of 20); source-analysis under upload processing, no new quota class, one call per source per trigger | Maintainer recommendation with concrete values; confirmed with SPEC READY (`YMY / Project Owner`) | 2026-09-04 |
| D6 | Memory injection into new specialists | Designer **and reviewer** receive the existing budgeted memory context (unchanged F013 priority, subordinate to confirmed intent); source-analysis receives none (document-anchored) | `YMY / Project Owner` (selected at SPEC READY gate, interactive question form — owner override of the designer-only recommendation) | 2026-09-04 |
| D7 | F009 re-baselining and new criteria | `stage_set` joins the comparability signature; per-pass source-analysis state snapshot pinned (F013 memory precedent); new blocking stage-trace criterion + `fault:design_invalid` / `fault:review_fail` scenarios; full live re-baseline at delivery under separate authorization | Maintainer recommendation; confirmed with SPEC READY (`YMY / Project Owner`) | 2026-09-04 |

## Gate Record: REVIEW

- Status: `PASS` (implementation and deterministic evidence under review; live evidence + delivery pending authorization)
- Validation time: 2026-09-04
- Implementation (plan `plan-f016-r1`, T0–T7 + T9): source-analysis specialist (`sources_grounding/analysis.py` + `source_analyses` + Celery task at parse settlement + one-in-flight/stale-takeover retry endpoint + labeled discovery/planning consumption with disclosure states + deletion sweep + deploy backfill step 5/6); designer stage (`artifact_production/design.py`: validation-gated design with one corrective retry, artifact-row storage, resume reuse without re-billing, budgeted memory); severity-gated review stage in all three families (`artifact_production/review.py` shared: findings normalization, one revise + re-review, `failed_after_revise` naming the review stage, unparseable-output bounded retry, reviewer memory per D6); shared `CapExhaustedError` + formula caps at run creation; F009 `stage_set` signature + pinned `source_analysis_state` + blocking `C-STAGE-1` + `fault:design_invalid`/`fault:review_fail` with `C-DESIGN-1`/`C-REVIEW-1` + harness analysis settle + F016-aware recovery accounting; web surfaces per ux-ui U1–U5 (incl. the `C-TOOL-1` label registry fix).
- Verification: backend full suite 622 passed + 4 skipped (exit 0) under the recorded environment overrides + ruff clean; web 122/122 + tsc clean + eslint 0 errors (3 pre-existing warnings); E2E TS-021 green (35.8s, deterministic stack, keyboard + 420px). Review `review-f016-r1`: SF-1..SF-6 found and fixed with tests; residuals M-1 (pre-existing journey flake, reproduced on unmodified main) / M-2 (stale local `.env`, owner-side refresh candidate) / M-3 (live evidence deferred to delivery) owner-visible; no Critical/unfixed-High.
- Documentation synced 2026-09-04: README, ARCHITECTURE, API, DATABASE, UX, TESTING (details in review.md). AGENTS unchanged.
- Delivery-time steps: T8 live evidence EXECUTED and recorded 2026-09-04 under the owner's full remaining-flow authorization — `live-evidence.json` captures a real-DeepSeek specialist journey (3 lessons x design+write+review, 4 real source analyses with token/cost telemetry, reviewer passing round 1 with no severe findings, i.e. no revise honestly triggered) and the full F009 six-pass live re-baseline under the new stage set (`retrieval=fastembed`, `tool=model_driven`, `stage_set` pinned; 5 passes pass, travelling-around pass1 fails C-ART-1 honestly and stays explicit; C-STAGE-1 passes on all six). Environment note: `apps/backend/.env`'s DeepSeek key is also stale (401); the run used `infra/deploy.env` credentials.

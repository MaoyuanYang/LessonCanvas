# F007: Versioned Targeted Regeneration

- Spec Status: `SPEC READY`
- Roadmap Status: `REVIEW`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #14](https://github.com/MaoyuanYang/LessonCanvas/issues/14) — bound 2026-08-31 (authorized)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F003`, `F004`, `F005` (all DONE) for the version-bound run, checkpoint, and recovery contract; `F006` (DONE) for layered evidence over affected and retained artifacts
- Last Updated: 2026-08-31

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-31
- Decision Authority: `YMY / Project Owner` — approved via interactive session (D1 impact matrix and D2 regeneration trigger selected interactively 2026-08-31; D3–D7 resolved from repository evidence and confirmed with Spec approval), scope: F007 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-014, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F007-versioned-targeted-regeneration/spec.md` @ `fb351456a2ee`
  - `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `77cac3f8a2c1`
  - `specs/F004-editable-lesson-slide-decks/spec.md` @ `9011ff986157`
  - `specs/F005-lesson-exercises-and-answers/spec.md` @ `807f4c857bf8`
  - `specs/F006-layered-run-evidence/spec.md` @ `a9b445a541cf`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `bf0def1cb66a`
  - `docs/API.md` @ `d523339dfa00`
  - `docs/DATABASE.md` @ `50f4b46db1fa`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/adr/0002-stateful-agent-and-async-execution.md` @ `5145b0ff319f`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Upstream-change impact classification matrix | Field-level conservative matrix, applied to the delta between the current confirmed brief/blueprint pair and the pending draft(s): brief `output_language_mode` and brief unit-level context (`unit_theme`, `teaching_objectives`, `material_position`, `student_context`, `assessment_orientation`) → all lessons × all artifact families; blueprint unit-level (`unit.title`, `unit.objectives`, `unit.assessment_intent`) → all lessons × all families; blueprint lesson-level (`title`, `objective_ids`, `assessment_intent`, `period_count`, `activity_outline`, `material_notes`) → that lesson × plans, with decks and exercises transitively affected (they consume plan content); brief `lesson_count` / blueprint lesson set → structural (added lessons get full generation; removed lessons' artifacts become historical; unchanged lessons retain). Any change the matrix cannot classify widens to the larger scope and the preview states the uncertainty explicitly. | `YMY / Project Owner`, 2026-08-31 (interactive selection) |
| D2 | Regeneration trigger | Teacher-triggered per artifact family: after a new version is confirmed, the teacher starts targeted regeneration per family from the owning view ("再生成受影响课程"), preserving the existing prerequisite gates. Unaffected artifacts are immediately presented as 沿用 (retained) with original provenance; no automatic cascade runs. | `YMY / Project Owner`, 2026-08-31 (interactive selection) |
| D3 | Safe-checkpoint supersession timing | Inherited per-lesson checkpoints (F003 D2): an in-flight lesson finishes its current draft→render→validate step; the run then stops and settles `superseded` without publishing over the newer version. No mid-model-call cancellation in Phase 1 — an in-flight call may finish and its result is discarded for superseded scope. | Inherited from F003–F005 evidence; confirmed with Spec approval |
| D4 | Revision drafts from confirmed versions | The existing draft machinery is reused: a structured revision seeds a new draft revision from the current confirmed brief/blueprint fields; editing never mutates the immutable confirmed version; the F002 `brief_diff`/stale-supersession patterns carry the intent comparison. | Resolved from evidence; confirmed with Spec approval |
| D5 | Retained-artifact semantics | Unaffected artifacts remain owned by their original runs; the current-version package presents them as 沿用 with full provenance (source run, bound versions, checksums) and never re-renders or re-bills them. No copying or migration into the new run. | Confirmed rule (DRAFT); confirmed with Spec approval |
| D6 | Comparison depth | Structured version comparison only: intent diff (brief-diff pattern) + impact scope table (lesson × family, affected/retained, with reasons) + per-lesson old/new artifact status with both downloads. No document content diffing, no in-browser Office editing. | Resolved from evidence; confirmed with Spec approval |
| D7 | Stale-edit conflict | Stale `base_revision` on draft save or confirm returns the explicit version-conflict class (existing 409 pattern); last-write-wins is prohibited; the teacher re-opens from the newer version. | Resolved from evidence; confirmed with Spec approval |

## Goal

Let a teacher change confirmed requirements or unit intent, understand the predicted impact before confirming, and regenerate only affected work — teacher-triggered per artifact family — without stale publication, duplicate model cost, or loss of valid history.

## Business Value

Versioned targeted regeneration makes real teaching iteration safe and demonstrates dependency reasoning, concurrency control, model-cost discipline, and recovery beyond one-shot generation while preserving every confirmed version's traceability.

## User Story

As a senior-high English teacher, I want to revise confirmed intent and rebuild only affected lessons and artifacts, so that valid work remains usable and the current package stays explainable at lower model cost.

## Scope

- Seed structured revision drafts from the current confirmed brief and blueprint without mutating history (D4).
- Compute and present a pre-confirmation impact preview from the D1 matrix: affected lessons × artifact families, per-change reasons, structural additions/removals, and explicit uncertainty when widening.
- Confirm a new immutable version through the applicable teacher gate; older active runs supersede at the next safe checkpoint and cannot publish over the new version (D3, D7).
- Create targeted runs scoped to affected lessons only when a prior generation exists for an older version pair; artifact rows exist only for scoped lessons (D1, D2).
- Present unaffected artifacts as retained (沿用) under the current-version package with original provenance and working downloads (D5).
- Teacher-triggered regeneration per family with the existing prerequisite gates generalized to coverage (a lesson is plan-covered when it has a complete plan in the bound plan run or a retained complete plan under the transition) (D2).
- Structured comparison of the current version transition: intent diff + scope table + per-lesson old/new artifact status with downloads (D6).

## Out of Scope

- Free-form branching of multiple simultaneous current versions.
- Collaborative merge, approval, or school-level review workflows.
- Silent Agent mutation of a confirmed brief, blueprint, or current artifact selection.
- Pixel-level document diffing or in-browser Office editing.
- Mid-model-call cancellation (Phase 1 lets an in-flight call finish; D3).
- Automatic cascading regeneration across families (D2 rejects for Phase 1).
- Re-evaluating or re-validating retained artifacts (they keep their recorded validation outcomes; F008 owns cross-artifact findings).

## Actors / Preconditions

- Actor: the authenticated workspace owner (teacher).
- Preconditions: a confirmed brief and blueprint version pair exists; at least one prior generation run family exists for an earlier version pair (otherwise a start is the ordinary full-scope run from F003–F005); the requester is the recorded workspace owner.

## Main Flow

1. The teacher opens a confirmed version and starts a structured revision (brief or blueprint); the draft is seeded from the confirmed fields (D4).
2. While editing, the system computes the predicted impact from the D1 matrix; before confirmation the teacher inspects the impact preview (affected lessons × families, reasons, structural changes, uncertainty).
3. The teacher confirms the new immutable version; stale-base edits return an explicit conflict (D7); older active runs stop at their next safe checkpoint and settle superseded (D3).
4. The teacher opens a generation family view and triggers 再生成受影响课程; the system creates a run scoped to the affected lessons of that family (D2), reusing nothing and re-billing nothing for unaffected lessons, which immediately show 沿用 with original provenance (D5).
5. After each family's targeted run completes, the teacher inspects the version comparison: intent diff, scope table, and per-lesson old/new artifact status with both downloads (D6).

## Alternative Flows

- Impact preview with uncertainty: an unclassifiable delta widens to the larger scope with a visible uncertainty notice; the teacher may narrow intent explicitly instead of accepting the wider scope.
- Structural lesson change: added lessons are fully generated across families by their targeted runs; removed lessons' artifacts become historical and never appear current; unchanged lessons retain.
- Revision without prior runs: with no prior generation for any earlier version pair, a start is the ordinary full-scope run; retention markers simply do not appear.
- Stale confirm: confirming against a superseded base_revision returns the version-conflict class with the current versions named; nothing is written.
- Active older run at confirm: it finishes its in-flight lesson, settles superseded at the checkpoint, and its completed artifacts remain historical downloads.
- Targeted run failure/resume: the F003–F005 failure taxonomy and per-lesson checkpoint resume apply unchanged, scoped to the affected lessons.
- Duplicate targeted start (same project, same versions, same family): idempotent — the existing run is returned, scoped as originally computed; scope is recorded once at creation and never widened silently by a later request.
- Retained artifact's source project data deleted: impossible cross-project by construction (retention is computed inside the owning project); within the project, artifact deletion only happens with project deletion.

## Business Rules / Invariants

- Confirmed brief and blueprint versions are immutable; revisions create new versions; one version pair is current per project.
- Every generation run binds to exactly one confirmed version pair; a targeted run additionally records its affected-lesson scope, fixed at creation.
- Duplicate start requests for the same project + version pair + family resolve to the same run (DB-enforced identity, unchanged); a new version pair yields a distinct run identity.
- The impact decision is conservative and explainable: every affected/retained verdict names its triggering change; uncertainty widens scope and is disclosed (D1).
- An old run or artifact never overwrites current state; supersession is transactional at confirm time with checkpoint-stop semantics (D3).
- Retained artifacts keep their original run, version binding, checksums, and validation outcomes; they are presented, never re-rendered, re-validated, or re-billed (D5).
- Prerequisite coverage: decks and exercises require every lesson in their scope to be plan-covered (complete plan in the bound run or retained complete plan under the transition) (D2).
- Teacher confirmation, not the system, initiates regeneration; no model call begins without a teacher-triggered start (D2).
- Retained and regenerated states are visually and semantically distinct from each other and from stale/superseded (never collapsed for convenience).

## State Transitions

- Version pair: `current -> superseded-by-confirm` (one-way; history preserved).
- Run: existing F003–F005 machine unchanged; targeted runs add creation-time scope (`affected_lesson_indexes`), terminal behavior identical.
- Artifact, per lesson and family: `retained (from prior run)` | in-run states `pending → drafting → rendering → validating → complete | failed` | `historical (superseded/removed lesson)`. Retained and historical are presentation-level states over authoritative rows (retention is computed from the version transition; history from run status), never separate truth.

## Data Changes

- `generation_runs` gains a nullable affected-lesson scope column (exact representation — JSON integer array vs child table — finalized by the Implementation Plan; null = full scope for pre-F007 rows and ordinary starts).
- Retention mapping is computed at read time by joining prior runs' complete artifacts per (project, family, lesson) across the version transition; no artifact copying, no new ownership, no migration of existing rows.
- Impact computation is a pure function of (confirmed pair, draft pair) per the D1 matrix; it is not persisted as independent truth (the preview may be logged as ordinary run/audit context only).
- Exact column names, indexes, and migration strategy are finalized by the Implementation Plan.

## API Behavior

- `GET /projects/{id}/impact` — pre-confirmation impact preview for the current drafts vs the current confirmed pair: brief diff, unit-level changes, per-lesson changes with affected families and reasons, structural additions/removals, scope summary, uncertainty flag. Owner-authorized; read-only.
- `GET /projects/{id}/versions/current-transition` — the current version transition for comparison: from/to versions, intent diff, scope table (lesson × family with affected/retained/historical verdicts and reasons), and per-lesson old/new artifact status with download availability. Owner-authorized; read-only.
- Existing confirm endpoints (`brief/confirm`, `blueprint/confirm`) gain no new contract beyond supersession already being checkpoint-safe; stale base revisions keep the explicit conflict.
- Existing family starts (`generation/start`, `decks/generation/start`, `exercises/generation/start`) become transition-aware: with a prior run family for an older version pair, the created run carries the D1-computed affected-lesson scope for that family; snapshot responses expose per-lesson `retained` entries (prior artifact id, provenance, download) alongside in-run artifacts, and prerequisite failures name the uncovered lessons and the recovery action.
- Error semantics follow the project taxonomy (requirement for uncovered prerequisites, stale-version for conflicts, authorization-not-found for cross-workspace); no internals leak.

## Error Cases

- Confirm with stale `base_revision`: explicit version conflict naming the current versions; nothing written.
- Deck/exercise start with lessons not plan-covered: requirement error naming the uncovered lessons and recovery (finish or retain plan coverage first).
- Impact computation on a project without confirmed versions: requirement error naming the missing gate.
- Superseded run contacted mid-transition: existing behavior — settles superseded; its artifacts stay historical.
- Cross-workspace access to any F007 endpoint: authorization-denied class without existence disclosure.

## Idempotency / Concurrency / Transactions

- Targeted run creation is atomic and idempotent per (project, version pair, family); scope is computed once inside the creation transaction; concurrent duplicate starts converge on one run (existing unique constraint).
- Confirm is transactional: version creation, current-pair switch, and supersession marking commit together; an in-flight lesson may complete afterwards but cannot publish (existing checkpoint rule).
- Impact preview and transition reads are safe, lock-free reads; retention joins read committed rows only.

## Security / Privacy / Authorization

- Every F007 endpoint is authorized by recorded workspace ownership; impact, transition, and retention data never cross workspaces.
- Drafts, diffs, and previews contain teacher content and stay inside the owning workspace; deletion cascades cover all F007-added data (scope column; retention is derived and leaves no residue).
- No new operator surface; no trace-content exposure beyond F006's rules.

## Non-functional

- No new infrastructure product, cache, queue, or second database; impact computation is in-process over confirmed/draft payloads (bounded by lesson count).
- The D1 matrix and family-scope rules are code constants reviewed at Design-Change level; page sizes and existing caps unchanged.
- Targeted runs reuse the existing per-run model-call caps; a targeted run's cost is proportional to its scope — the start surface shows the scoped lesson count before the teacher triggers.

## UI Impact

- UI involved: `YES`
- Affected screens: brief/blueprint revision entries with pre-confirm impact preview; generation/deck/exercise panels with transition-aware starts, retained markers, and coverage-gated availability; a workspace version-transition comparison view.
- Primary flow: revise intent → inspect impact → confirm → trigger per-family targeted regeneration → inspect comparison.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given a confirmed version pair, when the teacher confirms a material upstream change, then a new immutable version pair is created and the affected scope (lessons × families, with per-change reasons) is visibly identified per the D1 matrix.
- AC-002: Given an older run is active when the new version is confirmed, then the older run stops at its next safe checkpoint, settles superseded, and cannot publish over the new version.
- AC-003: Given unaffected artifacts with valid provenance, when the version transition completes, then they are presented as retained (沿用) under the current package with original provenance and working downloads, without duplicate generation or billing.
- AC-004: Given a stale browser edit, when confirmation is attempted, then an explicit version conflict naming the current versions is returned and nothing is written.
- AC-005: Given the D1 matrix, when the impact preview is computed for any draft delta, then every affected/retained verdict names its triggering change, and an unclassifiable delta widens the scope with a visible uncertainty notice.
- AC-006: Given a lesson-level blueprint change, when impact is previewed, then only that lesson's plans, decks, and exercises are affected and every other lesson is retained across all families.
- AC-007: Given a unit-level brief or blueprint change, when impact is previewed, then all lessons × all families are affected with the change named.
- AC-008: Given a structural lesson-count change, when the transition completes, then added lessons are generated by targeted runs, removed lessons' artifacts are historical and never current, and unchanged lessons retain.
- AC-009: Given a teacher-triggered targeted start for a family, when the run is created, then it binds the new version pair, records its affected-lesson scope once, and duplicate starts return the same scoped run.
- AC-010: Given a targeted run with failed lessons, when the teacher resumes, then the F003–F005 checkpoint resume applies within the scoped lessons and retained lessons are untouched.
- AC-011: Given deck or exercise start with lessons not plan-covered (neither in-run complete nor retained complete), when start is attempted, then a requirement error names the uncovered lessons and recovery action.
- AC-012: Given the current version transition, when the teacher opens the comparison, then intent diff, scope table with verdicts and reasons, and per-lesson old/new artifact status with both downloads are visible.
- AC-013: Given another teacher or an unauthenticated user, when any F007 endpoint is requested, then no content or existence is disclosed.
- AC-014: Given project or account deletion, when complete, then all F007-added data is deleted with the project and no retention residue survives.

## Open Questions

All DRAFT open questions and the three blocking refinement questions are resolved (D1–D7 above; Issue #14 bound 2026-08-31). Non-blocking residuals:

- [DEFERRED, owner-approved] Exact scope-column representation (JSON array vs child table) is Implementation-Plan territory.
- [DEFERRED, revisit with teacher evidence] Auto-cascade regeneration remains rejected for Phase 1 (D2); revisit only with teacher-cost evidence in a later era.
- [DEFERRED, revisit at F008] Cross-version finding propagation is F008's alignment-review concern.

## Risks and Assumptions

- [CONFIRMED] Versioned impact regeneration is required; whole-unit regeneration is not the default recovery from every change (D1 makes scope explicit).
- [CONFIRMED] Historical output remains available but never appears current after supersession.
- [ASSUMED] The D1 matrix covers Phase-1 revision reality; a missed class falls into the conservative widen-with-uncertainty branch instead of silently under-scoping.
- [ASSUMED] Read-time retention joins are sufficient at Phase-1 scale (bounded lessons/runs per project); persistence is revisited only with measured need.

## Deliberately Deferred Detail

- DTO shapes, exact response schemas, and error code strings (Implementation Plan + API doc sync)
- Scope-column representation, indexes, and migration steps (Implementation Plan)
- Components, packages, and internal functions (Implementation Plan)
- Pixel-level UI and complete Test Design (`ux-ui.md`, `test-design.md`)

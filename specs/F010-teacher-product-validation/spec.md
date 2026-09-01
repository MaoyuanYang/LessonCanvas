# F010: Teacher Product Validation

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P1`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #20](https://github.com/MaoyuanYang/LessonCanvas/issues/20) — bound 2026-09-01 (authorized)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F009` (DONE) for representative synthetic units, the evaluation harness that produces complete packages, and separate technical-result reporting; `F008` (DONE) for the technical package-validation status surface this Feature extends
- Last Updated: 2026-09-01

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-01
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-01 ("确认" reply approving D1 five-dimension rubric with 4.0 mean threshold and separate blocking severe-error classes, D2 all three dataset units, D3 controlled structured-evidence import with no new identity surface, D9 real reviews before delivery with honest not_complete fallback; D4–D8 resolved from repository evidence and confirmed together with this approval), scope: F010 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-010, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F010-teacher-product-validation/spec.md` @ (this file, final working-tree hash recorded in `STAGE.md` Gate Snapshot)
  - `specs/F009-technical-portfolio-evaluation/spec.md` @ `38bff6656785`
  - `specs/F008-alignment-review-and-delivery/spec.md` @ `0e1e911d1158`
  - `AGENTS.md` @ `f68a2ee15654`
  - `specs/ROADMAP.md` @ (pre-READY projection, hash recorded in `STAGE.md` Gate Snapshot)
  - `docs/API.md` @ `3ff63f6e27a5`
  - `docs/DATABASE.md` @ `59ea2788758e`
  - `docs/ARCHITECTURE.md` @ `9d26a7199d19`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/TESTING.md` @ `d2288beae040`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Core rubric dimensions and the severe-error boundary | A versioned teacher-review rubric (engineering key `rubric-r1`) with five core dimensions, each scored 1–5 by the evaluator with a required evidence note: `knowledge_correctness`, `language_quality`, `exercise_answer_correctness`, `objective_alignment`, `teaching_usability`. Core-rubric mean = arithmetic mean of the five dimension scores; pass threshold ≥ 4.0. Severe findings are a separate, blocking record with four classes: `knowledge_error`, `language_error`, `answer_error`, `objective_alignment_error`; a finding is severe when it would mislead a teacher or students or make the material unusable without structural rework (wrong facts, English being modeled incorrectly, wrong answer key, objective not actually covered). Ordinary revision feedback (style, depth, preference) influences scores but never blocks. Every severe finding carries a lesson reference and evidence text. One structural-rework question per unit (boolean; `true` requires a reason) completes the rubric. | `YMY / Project Owner`, 2026-09-01 (interactive confirmation) |
| D2 | Representative units to review | All three F009 dataset units — `travelling-around` (English), `natural-disasters` (Chinese), `cultural-heritage` (bilingual) — exceeding the "at least two" minimum and covering every output mode. The package under review for each unit is a complete, technically complete artifact set generated through the existing F009 evaluation harness (live mode) inside the owning evaluation project; the assignment binds dataset revision, confirmed brief/blueprint versions, and per-lesson artifact ids + checksums of all three families. | `YMY / Project Owner`, 2026-09-01 (interactive confirmation) |
| D3 | Evaluator evidence-capture flow | Controlled structured-evidence import, no new identity surface. The evaluator reviews the exported package offline (F008 ZIP export + printable alignment report for the exact package), completes a fixed-schema rubric document (zh-Hans labels for the evaluator; schema identical to D1), and the workspace owner imports the completed structured evidence through an owner-authorized in-app capture form. The system validates the import against the rubric schema and computes outcomes deterministically with zero model calls. Independence is preserved by fixing the rubric before review, retaining the evaluator's original completed document as private evidence, and labeling every result with the owner-mediated-import capture channel. Phase 1 adds no reviewer account, role, or cross-workspace access (PRODUCT.md excludes collaboration). | `YMY / Project Owner`, 2026-09-01 (interactive confirmation) |
| D4 | Publishable evidence boundary | Resolved from evidence (ROADMAP risk note "public portfolio samples remain synthetic-only"; AGENTS privacy constraints; dataset is CC0 synthetic). Public/portfolio surfaces may show: product-validation status, per-dimension scores and severe-finding classes of synthetic units, rubric revision, and a pseudonymous evaluator reference ("one external senior-high English teacher"). Never publishable: evaluator identity or contact, original rubric documents, private workspace traces, or any non-synthetic teacher content. | Resolved from evidence; confirmed with Spec approval |
| D5 | Staleness rule | Resolved from evidence (F007/F008 version-pair semantics). A product-validation result binds to (project, unit key, dataset revision, confirmed brief version, confirmed blueprint version, complete artifact-set identity). It becomes historical when any bound input changes: a newer confirmed pair for the unit, any evaluated artifact superseded by regeneration, or a newer dataset revision producing a new package. Historical results stay readable with an explicit stale state and a pointer to what superseded them; they never transfer and never silently update. A current package with no bound result displays `not_evaluated`. | Resolved from evidence; confirmed with Spec approval |
| D6 | Status vocabulary and computation | Resolved from evidence (DRAFT vocabulary; F008 D6 surface; alignment module pattern of deterministic read-side computation). Per-unit outcome: `pending_evidence | passed | failed | not_complete`. Overall product-validation status per project: `not_evaluated | in_progress | not_complete | passed | failed`, derived with precedence: no assignment for any in-scope unit → `not_evaluated`; any unit definitively failed → `failed` (definitive because overall pass requires every unit to pass; per-unit detail still shows pending units); any unit `not_complete` or stale-superseded → `not_complete`; any unit `pending_evidence` → `in_progress`; otherwise `passed`. Unit passes only with zero severe findings, core mean ≥ 4.0, and `structural_rework_required = false`. Computation is model-free and read-only over imported evidence. | Resolved from evidence; confirmed with Spec approval |
| D7 | Surface integration | Resolved from evidence (F008 D6; F009 report surface). The hardcoded `not_evaluated` constants in the alignment read (`PRODUCT_VALIDATION_STATUS`), the technical-evaluation report, and the delivery print report are replaced by the live per-project product-validation status with the full D6 vocabulary, always displayed separately from technical package validation and technical Phase-1 status. The F009 report's independence note is retained (wording updated: no longer "until F010"). A new owner-operated product-validation region (assignment, evidence import, outcomes) composes the existing evidence/evaluation experience pattern — no new top-level tab, no new visual language (UI refinement decides exact placement). | Resolved from evidence; confirmed with Spec approval |
| D8 | Idempotency and revision supersession | Resolved from evidence (API.md idempotency rule; F009 D10 pattern). Assignment creation is idempotent per (project, dataset revision, unit, package identity); evidence import is idempotent per (assignment, rubric revision) — a duplicate returns the existing record and never recomputes into a second row. A corrected rubric revision supersedes the prior evidence on the same assignment; the prior evidence and outcome remain historical and immutable once terminal. | Resolved from evidence; confirmed with Spec approval |
| D9 | Real-review execution timing | The participating external teacher completes rubric reviews for every selected unit before F010 delivery; the imported evidence plus the retained original documents form the delivery evidence (the F009 live-evidence pattern applied to product validation). If the teacher is unavailable at delivery, the system still delivers with an honest `not_complete` overall status recorded for the missing units, and the pass-path acceptance evidence waits for the follow-up import (owner-visible residual). | `YMY / Project Owner`, 2026-09-01 (interactive confirmation) |

## Goal

Record whether representative complete units meet the independently defined senior-high English teacher-quality threshold — zero severe knowledge, language, answer, or objective-alignment errors, a core-rubric mean of at least 4/5, and no structural rework — through one external teacher's rubric review, and report the resulting passed, failed, or not-complete product-validation status separately from every technical status, without rewriting technical completion or overstating one evaluator's evidence.

## Business Value

The project can distinguish a strong engineering demonstration from a validated teacher product. Failed or incomplete product evidence remains useful learning rather than becoming a hidden or inflated claim; the portfolio's teacher-usability claims become honest and inspectable.

## User Story

As the project owner and a portfolio reviewer, I want the external teacher's rubric evidence recorded, version-bound, and computed into an explicit product-validation status, so that teacher-usability claims are either supported by bounded evidence or visibly absent.

## Scope

- Ship the versioned external-teacher review rubric (D1) with its fixed schema, severe-finding classes, and thresholds.
- Fix complete unit packages for evaluation as immutable, identity-bound assignments (D2, D5).
- Provide the owner-authorized structured-evidence import flow for the external teacher's completed rubric (D3), with schema validation and deterministic, model-free outcome computation (D6).
- Record per-unit outcomes and the overall product-validation status, idempotently and with rubric-revision supersession (D8).
- Display the live product-validation status with the full state vocabulary, separately from technical package validation and technical Phase-1 status, across the alignment view, technical-evaluation report, and delivery print report (D7).
- Preserve evaluator evidence privately and publish only the D4-bounded summary.
- Execute and record the participating teacher's real reviews as delivery evidence (D9).

## Out of Scope

- Generalizing one teacher's result to all schools, regions, textbooks, or English teachers.
- Treating positive feedback, an LLM judge, artifact completeness, or technical evaluation as product validation; model-based opinion may never replace the external teacher decision.
- Student outcomes, classroom experiments, automatic grading, or educational-efficacy research.
- Blocking honest technical completion because product validation failed.
- A generalized reviewer account, public evaluator role, collaboration surface, or cross-workspace evidence corpus (Phase-1 identity scope).
- Automating rubric distribution/collection beyond the owner-mediated import channel.

## Actors / Preconditions

- Actor: the authenticated workspace owner (project owner), who fixes assignments, imports the evaluator's structured evidence, and reads outcomes. The external teacher evaluator is not an application role; they interact with exported materials and the rubric document offline (D3).
- Preconditions for creating an assignment: a complete, technically complete package for the chosen unit exists in the owning evaluation project (all lessons with validated plan, deck, and exercise+answer set), the F008 technical package status is computable for that confirmed pair, and the rubric revision is fixed.
- Preconditions for importing evidence: an assignment exists and is not stale; the submitted evidence satisfies the rubric schema (D1) and carries the evaluator attestation fields (pseudonymous evaluator reference, completed date).
- Preconditions for reading: ownership of the evaluating workspace.

## Main Flow

1. The owner fixes a complete package for an in-scope unit as a product-validation assignment; the system records the immutable package identity (dataset revision, confirmed pair, artifact ids + checksums) idempotently.
2. The owner exports the review materials for that package (F008 ZIP export + printable report) and hands them to the external teacher with the fixed rubric.
3. The teacher reviews every artifact family, scores the five dimensions with evidence notes, records severe findings and the structural-rework answer, and returns the completed rubric.
4. The owner imports the structured rubric evidence; the system validates it against the schema and computes the per-unit outcome deterministically — zero model calls, no mutation of evaluated content.
5. With every in-scope unit concluded, the overall product-validation status derives per D6 and surfaces — separately from technical status — in the alignment view, technical-evaluation report, and delivery print report.

## Alternative Flows

- Incomplete or malformed rubric import: requirement error naming the missing/invalid fields; nothing persists; the assignment remains `pending_evidence`.
- Severe finding without lesson reference or evidence text: rejected as invalid evidence for the same reason.
- Duplicate import for the same rubric revision: the existing evidence record is returned; outcomes are not recomputed into new rows (D8).
- Corrected rubric received after import: a new rubric revision supersedes on the same assignment; the prior evidence and outcome remain historical; the outcome recomputes from the new revision only.
- Package superseded mid-review (regeneration or new confirmed pair): the assignment settles stale; the overall status shows `not_complete` until a new assignment is fixed; the prior result stays historical (D5).
- Evaluator unable to complete a unit: the assignment is concluded `not_complete` with a recorded reason; pass-path evidence for that unit waits (D9).
- Cross-workspace access to any product-validation endpoint: authorization-denied without existence disclosure.

## Business Rules / Invariants

- Product validation is version-bound: an outcome attaches to the exact package identity and never transfers to regenerated or materially changed artifacts (D5).
- Any severe knowledge, language, answer, or objective-alignment error fails the unit threshold; a core mean below 4.0, a required structural rework, a missing in-scope unit, or incomplete rubric evidence prevents pass (D1, D6).
- Technical Phase 1 and technical package validation may pass while product validation fails or stays incomplete; UI and portfolio must prohibit teacher-usability claims in that case.
- One teacher supplies bounded evidence, not market-wide validation; every public mention carries the bounded-conclusion wording (D4).
- Outcome computation is deterministic and model-free; identical imported evidence always yields identical outcomes; the evaluator decision can never be produced or replaced by a model.
- Imported evidence, evaluator documents, filenames, and metadata are untrusted input: they cannot alter rubric thresholds, inject UI behavior, or escape the workspace boundary.
- Evaluated content is never mutated by validation; the evaluation records only read bindings.
- Evaluator identity stays pseudonymous in every publishable surface; original documents remain private workspace evidence, deleted with the workspace.

## State Transitions

- Assignment: `pending_evidence -> passed | failed | not_complete`, plus `stale` as a non-outcome terminal display state when the bound package is superseded (D5). Terminal states are immutable; a stale assignment may be replaced by a new assignment on the new package identity.
- Evidence (per assignment): `imported(rubric revision rN) -> superseded(by rN+1) | current`. Superseded evidence stays readable and historical.
- Overall product-validation status (per project): `not_evaluated -> in_progress -> passed | failed | not_complete`, recomputed read-side as assignments and evidence change; any transition can revert (for example `passed -> not_complete`) only through a new assignment/evidence event, never silently.
- Display states over recorded truth: not evaluated, in progress, pending evidence, passed, failed, not complete, stale (historical result), each mapping to D6 vocabulary.

## Data Changes

- New persisted owner data: product-validation assignments (project, workspace, unit key, dataset revision, confirmed brief/blueprint version ids, per-lesson artifact ids + checksums across the three families, rubric revision, state, timestamps), imported rubric-evidence records (dimension scores + evidence notes, severe findings with class/lesson/evidence, structural-rework answer + reason, evaluator attestation pseudonym + completed date, capture channel `owner_mediated_import`, original-document storage reference), and computed outcome fields. Audit follows the existing audit-events pattern.
- No changes to existing domain tables; existing read surfaces change their `product_validation_status` value from a constant to the computed status.
- Exact table names, columns, and migration steps are finalized by the Implementation Plan; deletion cascades with the project cover all F010-added rows and evidence objects.

## API Behavior

- `GET /projects/{id}/product-validation` — owner-authorized overview: rubric revision, per-unit assignments with states and derived staleness, overall status per the D6 precedence, bounded-conclusion sentence.
- `POST /projects/{id}/product-validation/assignments` — fix a package for evaluation (unit key); idempotent per (project, dataset revision, unit, package identity), returning `created: false` for duplicates (D8); rejects packages that are not technically complete with a requirement error naming the per-lesson family gaps.
- `POST /projects/{id}/product-validation/assignments/{assignment_id}/evidence` — import the evaluator's structured rubric evidence (multipart: submission-revision label, rubric JSON, and the required original document); idempotent per (assignment, submission revision); validates the full schema and lists every violating field at once, persisting nothing on violation; a newer submission revision supersedes the prior, which stays historical.
- `POST /projects/{id}/product-validation/assignments/{assignment_id}/conclusion` — conclude an assignment the evaluator cannot complete, recording the required honest reason (D9 fallback); terminal states are immutable.
- `GET /projects/{id}/product-validation/assignments/{assignment_id}` — detail: package identity, evidence history with outcomes, capture-channel label, and the fixed rubric-sheet data for the evaluator hand-out.
- `GET /projects/{id}/product-validation/assignments/{assignment_id}/evidence/{evidence_id}/document` — owner-authorized download of the evaluator's original document (private evidence; D4).
- Existing surfaces gain the live computed value: `GET /projects/{id}/alignment` (`product_validation_status`), `GET /projects/{id}/alignment/report`, `GET /projects/{id}/technical-evaluation/report`, and the F008 delivery report snapshot. The F009 report note keeps the independence wording without the "until F010" clause.
- Error semantics follow the project taxonomy: requirement (unknown unit, incomplete package, malformed/incomplete rubric evidence with every violating field listed, stale-assignment import), authorization-not-found (cross-workspace), and stale-version conflicts where applicable. All endpoints are synchronous reads/imports with no model spend.

## Error Cases

- Rubric evidence missing fields, out-of-range scores, or severe findings without location/evidence: requirement error listing every violating field; nothing persists.
- Assignment creation against an incomplete package: requirement error naming the missing family/lessons (F008 D3 vocabulary).
- Import against a stale assignment: requirement error stating the supersession; a new assignment must be fixed first.
- Cross-workspace or unauthenticated access: no content or existence disclosure.
- Unexpected system failure during import: transactional rollback; no partial evidence rows.

## Idempotency / Concurrency / Transactions

- Assignment creation and evidence import are DB-enforced idempotent on their identity tuples; concurrent duplicates converge on one record (D8).
- Evidence import and outcome computation run in one transaction; the outcome derives only from committed evidence.
- Overall-status reads are deterministic read-side computations over committed rows; no projection table may contradict them.
- Concurrent imports of different rubric revisions for one assignment: the later-committed revision supersedes; both remain recorded; the current outcome always names its evidence revision.

## Security / Privacy / Authorization

- All F010 endpoints are workspace-authorized; assignments, evidence, and outcomes never cross workspaces and are deleted with the project (D4).
- The evaluator is referenced only pseudonymously; identity and contact data are never recorded in publishable form; original documents live in workspace-private storage.
- Imported documents and fields are untrusted input; rendering escapes them and never interprets markup.
- Zero model calls in the entire Feature; no provider cost surface exists.

## Non-functional

- No new infrastructure, cache, queue, second database, model dependency, or identity surface (D3); the flow composes existing FastAPI/PostgreSQL/storage and the F008 export surfaces.
- Computation is bounded by rubric size; imports and reads are synchronous.
- The rubric document (zh-Hans labels for the evaluator) and its schema ship versioned in-repo.

## UI Impact

- UI involved: `YES`
- Affected screens: alignment view status pair (replace constant `未评估`), technical-evaluation report and delivery print report status lines, and a new owner-operated product-validation region composing the existing evidence/evaluation experience (D7).
- Primary user flow: fix package assignment -> hand materials to evaluator -> import completed rubric -> view per-unit outcomes and overall status -> see separate status display.
- Major UI states: not evaluated, in progress, pending evidence, passed, failed, not complete, stale/historical, permission denied, validation error on import.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given the shipped rubric (`rubric-r1`), when evidence is imported, then the import is validated against the fixed five-dimension schema, severe-finding classes, attestation fields, and structural-rework rule; any violation returns a requirement error naming every violating field and persists nothing.
- AC-002: Given a complete technically-validated package for an in-scope unit, when an assignment is created, then it binds dataset revision, confirmed brief and blueprint versions, and per-lesson artifact ids + checksums of all three families idempotently; a duplicate create returns the existing assignment; a package with any missing family member is rejected with a requirement error naming the gap.
- AC-003: Given complete imported evidence for a unit, when the outcome is computed, then it is derived deterministically with zero model calls and no mutation of evaluated content, and identical evidence always yields the identical outcome; the unit passes only with zero severe findings, core-rubric mean ≥ 4.0, and no required structural rework.
- AC-004: Given any severe finding, core mean below 4.0, or required structural rework on a concluded unit, when status is computed, then that unit records `failed` and teacher-usability claims remain blocked; given any in-scope unit lacking complete evidence, then the overall status is `not_complete` (or `in_progress` before conclusion) and never `passed`.
- AC-005: Given technical evidence passing while product validation fails or is incomplete, when any status surface is opened (alignment view, technical-evaluation report, delivery print report), then technical completion remains visible, the product-validation status displays the live D6 vocabulary equally explicitly, and no surface merges the two.
- AC-006: Given an evaluated package is superseded by regeneration or a newer confirmed pair, when the new package becomes current, then the prior product-validation result remains historical with an explicit stale state and pointer, the overall status reflects `not_complete` until a new assignment concludes, and no result transfers automatically.
- AC-007: Given a duplicate evidence import for the same rubric revision, when processed, then the existing record is returned without recompute or a second row; given a corrected rubric revision, then it supersedes the prior evidence on the same assignment with the prior evidence retained historical and outcomes immutable once terminal.
- AC-008: Given any public or portfolio surface, when product-validation evidence is presented, then only status, per-dimension scores, severe-finding classes of synthetic units, rubric revision, and the pseudonymous evaluator reference appear; evaluator identity/contact, original documents, and private traces never appear; deleting the workspace removes all F010 rows and evidence objects.
- AC-009: Given a non-owner or unauthenticated requester, when any F010 endpoint is called, then no content or existence is disclosed.
- AC-010: Given the participating external teacher's completed reviews for every selected unit (D9), when imported before delivery, then the delivery evidence records the per-unit outcomes, the retained original documents, and the overall status; if any unit's review is unavailable at delivery, then the overall status records `not_complete` honestly and the pass-path evidence waits. (Bound to D9 confirmation.)

## Open Questions

All five DRAFT open questions and the blocking refinement questions are resolved (D1–D9 above; Issue #20 bound 2026-09-01). Non-blocking residuals:

- [DEFERRED, Implementation Plan] Exact table shapes, rubric document file placement, import payload DTOs, and evidence-document storage keys.
- [DEFERRED, revisit at F012] Display of product-validation status on the deployed portfolio surface.

## Risks and Assumptions

- [CONFIRMED] One teacher provides sustained review but cannot support broad product-generalization claims; all conclusions stay bounded (PRODUCT.md).
- [CONFIRMED] Product validation never blocks honest technical portfolio completion (ROADMAP sequencing note).
- [CONFIRMED, D9 2026-09-01] The participating teacher completes the selected reviews within the F010 delivery window; if unavailable, the feature delivers with honest `not_complete` status.
- [CONFIRMED, D3 2026-09-01] Owner-mediated import is the accepted Phase-1 capture channel; the capture channel is labeled on every record so the evidence chain stays honest.
- [RECOMMENDED, DRAFT] Keep the first evaluator workflow controlled rather than build a generalized reviewer-account product; revisit when additional independent evaluators are committed.

## Deliberately Deferred Detail

- DTO shapes, exact request/response schemas, and error code strings (Implementation Plan + API doc sync)
- Table/column definitions, indexes, and migration steps (Implementation Plan)
- Rubric document layout and print formatting for the evaluator (Implementation Plan; labels zh-Hans)
- Pixel-level UI and complete Test Design (`ux-ui.md`, `test-design.md`)

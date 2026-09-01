# F008: Alignment Review and Delivery

- Spec Status: `SPEC READY` (DONE 2026-09-01)
- Roadmap Status: `DONE`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #16](https://github.com/MaoyuanYang/LessonCanvas/issues/16) — bound 2026-09-01 (authorized)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F006` (DONE) for layered evidence; `F007` (DONE) for version transitions, retained artifacts, and targeted regeneration
- Last Updated: 2026-09-01

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-01
- Decision Authority: `YMY / Project Owner` — approved via interactive session (D1 deterministic-only judgment, D2 missing-not-overridable/disputed-overridable, D3 all-three-families required, D4 ZIP + web printable report selected interactively 2026-09-01; D5–D8 resolved from repository evidence and confirmed with Spec approval), scope: F008 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-013, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F008-alignment-review-and-delivery/spec.md` @ (this file, final working-tree hash recorded in `STAGE.md` Gate Snapshot)
  - `specs/F006-layered-run-evidence/spec.md` @ `a9b445a541cf`
  - `specs/F007-versioned-targeted-regeneration/spec.md` @ `ae06a143e088`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `8745d8fad44b` (pre-READY projection)
  - `docs/API.md` @ `bcf156966262`
  - `docs/DATABASE.md` @ `ef37d65ba56f`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Alignment judgment method | Deterministic-only: coverage, gap, and conflict findings are computed from structured links and recorded states (blueprint objectives → lessons via `objective_ids`, artifact family completeness, F003–F005 structural-validation outcomes, F005 exercise/answer pairing validation, F007 version-transition retention). No model-assisted semantic judgment in F008; semantic quality evaluation belongs to `F009`/`F010`. Zero added model cost; every finding is explainable from recorded data. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D2 | Override policy | Gap-class severe findings (a required artifact or upstream prerequisite does not exist) are never overridable — only correction or targeted regeneration resolves them. Disputed conflict-class severe findings (an artifact exists but its recorded validation outcome is disputed by the teacher, e.g., a pairing-validation failure the teacher has verified as acceptable) may be overridden by the workspace owner with a required free-text reason; the override is persisted as an auditable decision bound to (project, version pair, finding key), never mutates the evaluated content, and can be withdrawn by the owner. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D3 | Technical package-validation definition | One current confirmed brief+blueprint version pair where every lesson in scope has: a complete and structurally validated lesson plan, a complete slide deck, and a complete exercise+answer pair that passes pairing validation — all current (in-run complete or F007-retained). All three families are required; any missing family member is a severe gap. Technical validation never implies product validation, which stays a separate status owned by this module but executed by `F010`. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D4 | Delivery form | ZIP package (original DOCX/PPTX artifacts, byte-identical, never re-rendered) plus a printable alignment report as a print-styled web page (browser print / save-as-PDF), no new rendering dependency. Package metadata and the report carry the draft/validated label and bound versions. | `YMY / Project Owner`, 2026-09-01 (interactive selection) |
| D5 | Finding lifecycle across versions | Findings are derived, not independent truth: they are recomputed deterministically from the current version pair and its current artifact set. Overrides persist independently, bound to (project, version pair, finding key); a new confirmed version or regenerated artifact set makes prior overrides and prior export labels historical — a new review reflects the new state, and nothing stale is presented as current. Cross-version propagation (F007 deferred item) needs no special machinery because recomputation is deterministic and cheap. | Resolved from evidence; confirmed with Spec approval |
| D6 | Product-validation status surface | The alignment view displays technical package status and product-validation status as two separate, always-visible statuses. Until `F010` executes an external rubric, product validation displays a persistent not-evaluated state; technical DONE must never render as product validation. | Resolved from evidence (AGENTS Repeated Pitfalls; F010 Spec); confirmed with Spec approval |
| D7 | Review computation model | Alignment review is a synchronous, owner-authorized, read-side computation (bounded by lesson count) — no new run kind, no Celery task, no model calls. Only teacher decisions (overrides) and delivery artifacts (export records, package objects, printable-report snapshots) are persisted. | Resolved from evidence; confirmed with Spec approval |
| D8 | Export idempotency and retention | Export creation is idempotent per (project, version pair, label, artifact manifest): a repeated request with an unchanged manifest returns the existing export record and never re-builds or re-bills. The package object and a report snapshot are written to the private artifacts bucket and stream through authorized FastAPI downloads; exports are deleted with the project. | Resolved from evidence (API.md idempotency rule; storage pattern); confirmed with Spec approval |

## Goal

Let a teacher see how each confirmed objective is supported across the complete current package, resolve findings through correction, targeted regeneration, or a recorded reasoned override, and deliver a selected unit version with an honest, separately reported technical and product status.

## Business Value

This Feature directly addresses the validated teacher problem: it makes cross-artifact coverage and conflict visible before a collection of generated files is treated as a coherent teaching package, and it produces the first owner-authorizable deliverable output of the workflow.

## User Story

As a senior-high English teacher, I want to review how each objective is supported by lessons, slides, exercises, and answers, so that I can correct gaps and deliver a package with an honest status.

## Scope

- Compute and present a unit-level alignment view for the current confirmed version pair: per-objective coverage across brief, blueprint, lesson plans, slide decks, exercises, and answers, using the deterministic D1 rules.
- Produce a deterministic finding taxonomy (coverage / gap / conflict, each info/warning/severe) where every finding links to its evidence (owning versions, artifact rows, validation outcomes) and affected scope, and names the recovery action (correct upstream, targeted regeneration, or override where allowed).
- Let the teacher record or withdraw owner-authorized reasoned overrides for disputed conflict-class severe findings (D2), persisted as auditable decisions that never mutate evaluated content.
- Maintain and display technical package-validation status per D3 and product-validation status as a separate not-evaluated-until-F010 status (D6).
- Allow a clearly labelled draft export while severe findings remain; block validated export until the package is technically validated (D3, D2).
- Deliver the selected current version as a ZIP of byte-identical artifacts plus a printable web alignment report carrying the same label and bound versions (D4, D8).

## Out of Scope

- Model-assisted or teacher-rubric semantic quality evaluation (`F009`, `F010`).
- Claiming or implying that technical package validation proves classroom usability.
- Silent mutation of sources, confirmed intent, artifacts, or their recorded validation outcomes by the alignment process.
- In-browser Office editing or document re-rendering during export.
- School approval, collaboration, or LMS publication.
- Automatic cross-version finding propagation beyond deterministic recomputation (D5).

## Actors / Preconditions

- Actor: the authenticated workspace owner (teacher).
- Preconditions for viewing alignment: a confirmed brief+blueprint version pair exists for the project.
- Preconditions for validated export: technical package-validation status is validated for the current version pair.
- Preconditions for any override or export action: the requester is the recorded workspace owner.

## Main Flow

1. The teacher opens the alignment view for the current unit version; the system computes coverage and findings deterministically (D1, D7) and presents objective-level relationships, package status, and the separate product status.
2. The teacher inspects a finding's evidence and affected scope, then chooses: correct upstream intent, trigger targeted regeneration (delegating to the F007-aware family starts), or — only for an overridable disputed severe finding — record a reasoned override (D2).
3. The system recomputes alignment against the same version pair (after override) or the newly confirmed pair (after correction/regeneration); prior overrides and export labels become historical when the evaluated state changes (D5).
4. The teacher exports: a labelled draft ZIP at any time, or the validated package once D3 is satisfied; the printable report carries the same label, bound versions, findings summary, and override record.

## Alternative Flows

- No confirmed version pair: the alignment view shows the missing-prerequisite state with the recovery path (confirm brief and blueprint first); no findings are invented.
- Package partially generated: the view presents per-family per-lesson coverage with gaps; draft export includes only complete artifacts and lists gaps in package metadata and the report.
- Override withdrawn: the owner withdraws a previously recorded override; the finding returns to unresolved and status recalculates immediately.
- Regeneration superseded a run mid-review: recomputation reflects the transition (retained artifacts count as current per F007 D5); findings never reference superseded artifacts as current.
- Export with unchanged manifest repeated: the existing export record is returned; no rebuild, no new storage object (D8).
- Artifact storage miss during package build: the export fails with the explicit provider-failure class; partial packages are never delivered as success (storage-miss-must-not-fake-success pattern).
- Cross-workspace request to any F008 endpoint: authorization-denied class without existence disclosure.

## Business Rules / Invariants

- Alignment and Evaluation owns findings, technical package-validation status, product-validation status, and evaluation records; it never silently mutates the content it evaluates.
- Every finding is derived from and bound to explicit brief version, blueprint version, artifact rows, and their recorded validation outcomes (D1, D5).
- Findings are deterministic and explainable: the same evaluated state always yields the same findings, each naming its triggering rule and recovery action.
- A gap-class severe finding blocks validated completion and is never overridable; only correction or regeneration resolves it (D2).
- A disputed conflict-class severe finding blocks validated completion until corrected or overridden by the owner with a recorded reason; overrides and withdrawals are auditable and never change evaluated content (D2).
- Technical package validation per D3 requires all three families complete, validated, and current for every lesson in scope (in-run complete or F007-retained).
- Technical package status and product-validation status are distinct and both always visible; product validation remains not-evaluated until `F010` (D6).
- Draft export is always available and clearly labelled; a draft can never be represented as technically or product validated.
- Only the workspace owner may view alignment, record or withdraw an override, create exports, or download the package (D4, D8).
- Exported artifacts are byte-identical to the stored objects; export never re-renders, re-validates, or re-bills (D4, D8).
- Selected delivery is always bound to one immutable version pair plus its artifact manifest; a later version never silently re-labels an earlier export (D5, D8).

## State Transitions

- Technical package status per version pair: `unevaluated-not-applicable | incomplete (severe findings unresolved) | draft-exportable | validated`. Validated requires zero unresolved severe findings per D3; any state change is a pure recomputation of (version pair, artifact set, overrides).
- Finding: `open | resolved-by-recompute | overridden | override-withdrawn`. Resolution always comes from state change or owner decision, never from the evaluation itself.
- Product-validation status: `not-evaluated` until `F010` defines its execution; no other value is producible by F008.
- Export: `building -> ready | failed`; once `ready`, immutable (label, manifest, object keys fixed); superseded only in the sense that newer exports exist for newer versions.

## Data Changes

- New persisted owner data: alignment overrides (project, version pair, finding key, reason, owner identity, recorded/withdrawn timestamps, audit events) and export records (project, version pair, label draft/validated, artifact manifest with checksums, package object key, report snapshot object key, status, timestamps). Audit uses the existing audit-events pattern.
- Findings, coverage, and both status values are derived at read time; they are not stored as independent truth (D5, D7).
- Exact table names, columns, indexes, and migration steps are finalized by the Implementation Plan; deletion cascades with the project cover all F008-added rows and objects.

## API Behavior

- `GET /projects/{id}/alignment` — owner-authorized read: per-objective coverage relationships, findings with severity/evidence/recovery, technical package status, product-validation status, bound versions. Synchronous; no side effects.
- `POST /projects/{id}/alignment/overrides` — record an override (finding key, version pair, required reason); `DELETE /projects/{id}/alignment/overrides/{override_id}` — withdraw. Gap-class or wrong-version override attempts return the requirement error class.
- `GET /projects/{id}/alignment/report` — owner-authorized printable report data for the current version (or a named export's snapshot), print-styled on the web side.
- `POST /projects/{id}/delivery/exports` — create an export (label draft or validated); validated label requires D3-satisfied status; idempotent per (version pair, label, manifest) (D8).
- `GET /projects/{id}/delivery/exports` and `GET /projects/{id}/delivery/exports/{export_id}/download` — list and authorized ZIP stream; report snapshot downloadable alongside.
- Error semantics follow the project taxonomy (requirement for missing prerequisites and ineligible overrides, stale-version for version-pair mismatch, authorization-not-found for cross-workspace, provider-transient for storage failures during build); no internals leak.

## Error Cases

- Alignment view without a confirmed pair: requirement error naming the missing gate and recovery.
- Override of a gap-class finding, empty/too-short reason, or version-pair mismatch: requirement/stale errors; nothing written.
- Validated export while severe findings are unresolved: requirement error naming the blocking findings and recovery actions; draft remains available.
- Storage failure during package build: provider-failure class; export record settles failed with retry guidance; no partial success.
- Deleted artifact referenced by a manifest (within-project impossible except project deletion; cross-project impossible by construction): 404-without-disclosure pattern.

## Idempotency / Concurrency / Transactions

- Override and withdrawal are owner-serialized writes with audit; duplicate identical override submission returns the existing decision rather than duplicating it.
- Export creation is idempotent per (version pair, label, manifest): the build runs once; concurrent duplicate creates converge on one record (DB-enforced identity per the project pattern).
- Alignment reads are safe, lock-free, read-committed computations; a review never blocks generation or regeneration.
- A confirmed-version switch or regeneration during export build settles that export failed (manifest no longer current) rather than delivering a mixed-version package.

## Security / Privacy / Authorization

- Every F008 endpoint is authorized by recorded workspace ownership; alignment, override, and export data never cross workspaces.
- Findings, overrides, reports, and packages contain teacher content and stay inside the owning workspace's storage and trace boundaries; deletion cascades remove all F008 rows and objects with the project.
- No new operator surface, no public MCP exposure, no cross-user evaluation data.

## Non-functional

- No new infrastructure product, cache, queue, second database, or model dependency (D1, D7); alignment computation is in-process and bounded by lesson and objective counts.
- ZIP building uses the existing storage adapter and artifacts bucket; package size bounded by existing artifact sizes.
- The finding-rule set is a code constant reviewed at Design-Change level; per the AGENTS architecture constraints no routing or second model is introduced.

## UI Impact

- UI involved: `YES`
- Affected screens: a unit workspace alignment/delivery surface (coverage matrix, findings with evidence and recovery actions, override dialog, package/export status), plus the print-styled report view.
- Primary flow: open current version → inspect coverage/findings → correct / regenerate / override → review statuses → export selected package (draft or validated).
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given a complete current version pair, when the teacher opens the alignment view, then each confirmed objective shows its supported/missing/conflicting relationships across brief, blueprint, plans, decks, exercises, and answers, each linking to owning versions and evidence.
- AC-002: Given any evaluated state, when alignment is recomputed, then the same deterministic findings with severity, triggering rule, affected scope, and recovery action are produced, with no model call.
- AC-003: Given a lesson in scope without a complete validated plan, deck, or exercise+answer pair, when alignment is computed, then a gap-class severe finding names the missing family member and blocks validated status.
- AC-004: Given an artifact with a recorded failed structural or pairing validation, when alignment is computed, then a conflict-class severe finding appears and names the dispute.
- AC-005: Given an unresolved severe finding of either class, when the teacher requests a validated export, then it is refused with the blocking findings named, while a labelled draft export remains available.
- AC-006: Given a gap-class severe finding, when an override is attempted, then it is refused with the reason that only correction or regeneration resolves gaps.
- AC-007: Given a disputed conflict-class severe finding, when the owner records an override with a reason, then the decision and reason are auditable, the evaluated content is unchanged, and status recalculates without the finding blocking validation.
- AC-008: Given a recorded override, when the owner withdraws it, then the finding returns to unresolved and the package status recalculates immediately.
- AC-009: Given a new confirmed version or regenerated artifact set, when alignment is recomputed, then prior overrides and export labels are historical, nothing stale is presented current, and findings reflect only the new state.
- AC-010: Given the package satisfies D3 with zero unresolved severe findings, when recomputed, then technical package status is validated while product-validation status remains separately displayed as not-evaluated.
- AC-011: Given a validated (or draft) export request, when the export is created, then the ZIP contains byte-identical current artifacts for the bound version pair, package metadata carries the honest label, and a repeat request with an unchanged manifest returns the same export without rebuilding.
- AC-012: Given the printable report (screen or export snapshot), when printed, then it shows bound versions, label, objective coverage summary, findings with overrides, and both statuses in a print-styled layout.
- AC-013: Given a non-owner or unauthenticated user, when any F008 endpoint is requested, then no content or existence is disclosed; given project deletion, all F008 data and objects are removed.

## Open Questions

All DRAFT open questions and the four blocking refinement questions are resolved (D1–D8 above; Issue #16 bound 2026-09-01). Non-blocking residuals:

- [DEFERRED, Implementation Plan] Exact override/export table shapes, indexes, and migration steps.
- [DEFERRED, revisit at F010] Product-validation status execution and threshold — displayed as not-evaluated until then.
- [DEFERRED, revisit with teacher evidence] Whether an objective lacking exercise coverage should escalate from warning to severe — current rule keeps it warning-level; revisit after F010 rubric evidence.

## Risks and Assumptions

- [CONFIRMED] Teacher authority can resolve a disputed severe finding with a recorded reason; Agent review cannot silently overrule the teacher (D2).
- [CONFIRMED] Product validation remains independent even when the technical package is validated (D6).
- [ASSUMED] The deterministic D1 rule set covers Phase-1 alignment reality; an unclassifiable state surfaces as an explicit warning finding instead of silence.
- [ASSUMED] Read-side recomputation is sufficient at Phase-1 scale (bounded objectives/lessons/artifacts per project).
- [ASSUMED] Browser print of the report view satisfies the printable requirement; a generated-document report stays out of scope (D4).

## Deliberately Deferred Detail

- DTO shapes, exact response schemas, and error code strings (Implementation Plan + API doc sync)
- Table/column definitions, indexes, and migration steps (Implementation Plan)
- Components, packages, and internal functions (Implementation Plan)
- Pixel-level UI and complete Test Design (`ux-ui.md`, `test-design.md`)

## Gate Record: DONE

- Status: `PASS`
- Validation time: 2026-09-01
- Decision Authority: `YMY / Project Owner` — full delivery flow (commit/push/PR/Issue update 2026-09-01, then merge) explicitly authorized in the interactive session ("全部授权"); merge performed as merge commit `1982ac9`
- Conditions met:
  - All 13 ACs satisfied with automated or E2E evidence (backend 197 passed incl. 17 alignment tests; web 57/57; see test-design Execution Evidence Snapshot)
  - E2E green on the fault stack: TS-016 validated-path journey (alignment view → status pair → validated export → keyboard ZIP download → print report) and TS-017 family-banner link; M-1/M-2/L-1 residuals owner-visible in the snapshot
  - Review: no Critical findings; SF-1 (failed-export retry) fixed with a regression test before delivery; SF-2..SF-4 recorded
  - Documentation sync: API/DATABASE/TESTING/UX/UI/DESIGN_SYSTEM updated; ROADMAP/STAGE/Issue synchronized (Issue #16 auto-closed by merge)
  - Delivery: PR [#17](https://github.com/MaoyuanYang/LessonCanvas/pull/17) merged `1982ac9`; main re-verified (backend exit-0 + ruff clean + web 57/57)
- DONE evidence manifest (working-tree SHA-256 prefixes at gate time):
  - `spec.md` @ `865244341a9e` (pre-DONE content; this record appended after)
  - `ux-ui.md` @ `817e9fcfa4a3`
  - `test-design.md` @ `d9feba15621d`
  - `plan.md` @ `cd47f7a23a05`
  - `review.md` @ `f1212fbc6698`
  - `specs/ROADMAP.md` @ `ad8c1ea0f128` (pre-DONE)

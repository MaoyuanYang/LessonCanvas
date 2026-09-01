# Project Stage

## Project Snapshot

| Field | Value |
| --- | --- |
| Snapshot Revision | `STAGE-65` |
| Parent Snapshot | `STAGE-64` @ `c0618ca56a6e` (pre-write read, no external change) |
| Last Reconciled At | `2026-09-01T20:25:15+08:00` |
| Reconciled By | `ZCode feature-dev session (YMY / Project Owner driving)` |
| Repository Ref | `main @ 683172b` (PR #21 merge) |
| Write Coordination | `SINGLE_WRITER:ZCode feature-dev session` |
| Lifecycle Path | `GREENFIELD` |
| Project Phase | `COMPLETE` |
| Overall State | `ACTIVE` |
| Current Milestone | F010 Teacher Product Validation DONE (PR #21 merge `683172b`; real-teacher reviews deferred by owner per D9, follow-up import pending); next actionable F011 (P0) / F012 / F013 — F010 completes their dependency surface where applicable |
| Tracking Mode | `REMOTE` |

## Lifecycle Progress

| Area / Milestone | State | Authoritative Evidence | Next Condition |
| --- | --- | --- | --- |
| Macro design and Feature Map | `COMPLETE` | `specs/ROADMAP.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` | N/A |
| F001 Grounded Confirmed Brief | `COMPLETE` | Issue #1 (closed), PR #2 merge `1253ca2`, `specs/F001-grounded-confirmed-brief/` | N/A |
| F002 planning workflow delivered | `COMPLETE` | Issue #3 (closed), PR #4 merge `8f90bb6`, `specs/F002-confirmed-unit-blueprint/` | N/A |
| F003 Recoverable Unit Lesson Plans | `DONE` | Issue #6 (closed), PR #7 merge `ad81c82`, `specs/F003-recoverable-unit-lesson-plans/` | F004/F005 refinement |
| F004+ remaining Feature map | `IN_PROGRESS` | `specs/ROADMAP.md` Feature Map + Issue [#14](https://github.com/MaoyuanYang/LessonCanvas/issues/14) (closed) | F009 delivery (A-009) |

## Active Work

| Activity ID | Work Item | Member | Type | Skill | Skill Stage | Activity State | Work Status | Branch / Worktree | Status Authority | Next Checkpoint | Updated At |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A-010` | `F010 Teacher Product Validation` | `ZCode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `COMPLETE` | `DONE` | `DONE` | `N/A` | `https://github.com/MaoyuanYang/LessonCanvas/issues/20` | N/A - terminal (PR #21 merge `683172b`) | `2026-09-01T20:25:15+08:00` |
| `A-003` | `F003 Recoverable Unit Lesson Plans` | `ZCode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `COMPLETE` | `DONE` | `DONE` | `N/A` | `https://github.com/MaoyuanYang/LessonCanvas/issues/6` | N/A - terminal (PR #7 merge `ad81c82`) | `2026-08-29T00:24:37+08:00` |
| `A-002` | `F002 Confirmed Unit Blueprint (DONE reconciliation)` | `opencode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `COMPLETE` | `ACTIVE` | `DONE` | `N/A` | `https://github.com/MaoyuanYang/LessonCanvas/issues/3` | N/A - terminal | `2026-08-28T19:10:00+08:00` |

## Gate Snapshot

| Work Item | Gate | Projection | Authoritative Record / Revision |
| --- | --- | --- | --- |
| F001 | `SPEC READY` | `PASS` | `specs/F001-grounded-confirmed-brief/spec.md` Gate Record @ `d7ae5094c490` |
| F001 | `UI READY` | `PASS` | `specs/F001-grounded-confirmed-brief/ux-ui.md` Gate Record @ `c4cd127cb372` |
| F001 | `TEST DESIGN READY` | `PASS` | `specs/F001-grounded-confirmed-brief/test-design.md` Gate Record @ `dc6978dfefc8` |
| F001 | `DONE` | `PASS` | PR #2 merge `1253ca2`; `specs/F001-grounded-confirmed-brief/review.md` |
| F002 | `SPEC READY` | `PASS` | `specs/F002-confirmed-unit-blueprint/spec.md` Gate Record @ `108178994342` |
| F002 | `UI READY` | `PASS` | `specs/F002-confirmed-unit-blueprint/ux-ui.md` Gate Record @ `a8cfd23189ac` |
| F002 | `TEST DESIGN READY` | `PASS` | `specs/F002-confirmed-unit-blueprint/test-design.md` Gate Record @ `9c997cfa2b6f` |
| F002 | `DONE` | `PASS` | PR [#4](https://github.com/MaoyuanYang/LessonCanvas/pull/4) merged `8f90bb6`, 2026-08-28; DONE evidence manifest in `specs/ROADMAP.md` Handoff |
| F003 | `SPEC READY` | `PASS` | `specs/F003-recoverable-unit-lesson-plans/spec.md` Gate Record @ `193e90d10b68` |
| F003 | `UI READY` | `PASS` | `specs/F003-recoverable-unit-lesson-plans/ux-ui.md` UI READY Record @ `ux-ui-f003-r1` / `43f93abc6ed3` |
| F003 | `TEST DESIGN READY` | `PASS` | `specs/F003-recoverable-unit-lesson-plans/test-design.md` Record @ `test-design-f003-r2` / `880a6a4a418c` |
| F004 | `SPEC READY` | `PASS` | `specs/F004-editable-lesson-slide-decks/spec.md` Gate Record @ `b913da61ec40` |
| F004 | `UI READY` | `PASS` | `specs/F004-editable-lesson-slide-decks/ux-ui.md` UI READY Record @ `ux-ui-f004-r1` / `05e5748c9a4d` |
| F004 | `TEST DESIGN READY` | `PASS` | `specs/F004-editable-lesson-slide-decks/test-design.md` Record @ `test-design-f004-r1` / `4afef155b09f` |
| F004 | `DONE` | `PASS` | PR #9 merge `123523a`; DONE evidence manifest in `specs/F004-editable-lesson-slide-decks/spec.md` Gate Record |
| F005 | `SPEC READY` | `PASS` | `specs/F005-lesson-exercises-and-answers/spec.md` Gate Record @ `41b391751a33` |
| F005 | `UI READY` | `PASS` | `specs/F005-lesson-exercises-and-answers/ux-ui.md` UI READY Record @ `ux-ui-f005-r1` / `78923f6468b7` |
| F005 | `TEST DESIGN READY` | `PASS` | `specs/F005-lesson-exercises-and-answers/test-design.md` Record @ `test-design-f005-r1` / `29b9ad5c42d2` |
| F005 | `DONE` | `PASS` | PR #11 merge `5804e86`; DONE evidence manifest in `specs/F005-lesson-exercises-and-answers/spec.md` Gate Record |
| F006 | `SPEC READY` | `PASS` | `specs/F006-layered-run-evidence/spec.md` Gate Record @ `b43922d2cc17` |
| F006 | `UI READY` | `PASS` | `specs/F006-layered-run-evidence/ux-ui.md` UI READY Record @ `ux-ui-f006-r1` / `4bff46959bb0` |
| F006 | `TEST DESIGN READY` | `PASS` | `specs/F006-layered-run-evidence/test-design.md` Record @ `test-design-f006-r1` / `e2e261591bd8` |
| F006 | `DONE` | `PASS` | PR #13 merge `21bef27`; DONE evidence manifest in `specs/F006-layered-run-evidence/spec.md` Gate Record |
| F007 | `SPEC READY` | `PASS` | `specs/F007-versioned-targeted-regeneration/spec.md` Gate Record @ `fb351456a2ee` |
| F007 | `UI READY` | `PASS` | `specs/F007-versioned-targeted-regeneration/ux-ui.md` UI READY Record @ `ux-ui-f007-r1` / `97597ad3c608` |
| F007 | `TEST DESIGN READY` | `PASS` | `specs/F007-versioned-targeted-regeneration/test-design.md` Record @ `test-design-f007-r1` / `69c9d0532f7a` |
| F007 | `DONE` | `PASS` | PR #15 merge `2b36d73`; DONE evidence manifest in `specs/F007-versioned-targeted-regeneration/spec.md` Gate Record |
| F008 | `SPEC READY` | `PASS` | `specs/F008-alignment-review-and-delivery/spec.md` Gate Record @ `dc301bba1a83` |
| F008 | `UI READY` | `PASS` | `specs/F008-alignment-review-and-delivery/ux-ui.md` UI READY Record @ `ux-ui-f008-r1` / `6bca800ac896` |
| F008 | `TEST DESIGN READY` | `PASS` | `specs/F008-alignment-review-and-delivery/test-design.md` Record @ `test-design-f008-r1` / `6d7979391f92` |
| F008 | `DONE` | `PASS` | PR #17 merge `1982ac9`; DONE evidence manifest in `specs/F008-alignment-review-and-delivery/spec.md` Gate Record |
| F009 | `SPEC READY` | `PASS` | `specs/F009-technical-portfolio-evaluation/spec.md` Gate Record @ `15803bdc1837` |
| F009 | `UI READY` | `PASS` | `specs/F009-technical-portfolio-evaluation/ux-ui.md` UI READY Record @ `ux-ui-f009-r1` / `d3860c7a8c05` |
| F009 | `TEST DESIGN READY` | `PASS` | `specs/F009-technical-portfolio-evaluation/test-design.md` Record @ `test-design-f009-r1` / `5a7fc2df6b13` |
| F009 | `DONE` | `PASS` | PR #19 merge `6eed93f`; DONE evidence manifest in `specs/F009-technical-portfolio-evaluation/spec.md` Gate Record |
| F010 | `SPEC READY` | `PASS` | `specs/F010-teacher-product-validation/spec.md` Gate Record @ `66a3c94329a9` (decision log D1–D9; ROADMAP projection @ `6c7128eccd4b`) |
| F010 | `UI READY` | `PASS` | `specs/F010-teacher-product-validation/ux-ui.md` UI READY Record @ `ux-ui-f010-r1` / `35fe2b9b1417` |
| F010 | `TEST DESIGN READY` | `PASS` | `specs/F010-teacher-product-validation/test-design.md` Record @ `test-design-f010-r1` / `eaa31cd897d6` |
| F010 | `DONE` | `PASS` | PR #21 merge `683172b`; DONE evidence manifest in `specs/F010-teacher-product-validation/spec.md` Gate Record |

## Blockers and Conflicts

| ID | Affected Activity / Work Item | Type | Evidence | Owner | Unblock / Resolution Condition |
| --- | --- | --- | --- | --- | --- |
| `B-002` | F007 (`A-007`) | `RESOLVED 2026-08-31` | Owner answered interactively: Issue creation authorized (Issue #14 bound); D1 = field-level conservative matrix; D2 = teacher-triggered per family. Spec finalized with D1..D7 resolved. | `YMY / Project Owner` | Resolved |
| `B-001` | F002 | `NON_BLOCKING residual from F001` | Authenticated Playwright E2E RESOLVED 2026-08-28: Clerk device verification disabled by owner; full teacher-journey spec passes against live DeepSeek after live-model JSON-contract fixes (PR [#5](https://github.com/MaoyuanYang/LessonCanvas/pull/5) merged `f6d3b4a`, authorized merge by `YMY / Project Owner`; main re-verified 80 backend tests + ruff). Remaining: keyboard manual pass pending; Postgres LangGraph checkpointer investigation deferred to F012 | `YMY / Project Owner` | Keyboard manual pass at next UI touch; checkpointer at F012 |

## Handoffs

| From | To | Work Item | Resume From | Required Inputs | Authority Transfer | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `feature-dev F001 session` | `feature-dev F002 session` | `F002` | `WORK_ITEM_BINDING` | F001 delivery records, F002 DRAFT Spec, Issue #3 | `N/A` (remote authority continuous) | `ACCEPTED` |

## Recently Completed

| Activity ID | Work Item | Member | Outcome | Final Work Status | Final Status Authority | Delivery Evidence | Completed At |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A-010` | `F010 Teacher Product Validation` | `ZCode feature-dev session` | Teacher product validation delivered end to end (fixed rubric-r1, version-bound assignments with staleness, deterministic zero-model outcomes, owner-mediated evidence import with private original documents, honest not-complete, live separate status on all shared surfaces; SF-1/SF-2 review fixes; real-teacher reviews deferred by owner per D9 with follow-up import pending) | `DONE` | Issue #20 (auto-closed by merge) | PR #21 merge `683172b` | `2026-09-01` |
| `A-009` | `F009 Technical Portfolio Evaluation` | `ZCode feature-dev session` | Technical portfolio evaluation end to end (governed synthetic dataset, deterministic blocking/diagnostic criteria engine, idempotent scripted harness with eval-gated fault injection, owner API + report, evidence-panel region; F006 L-1 narration token capture; truncated-response reclassification fix; six live DeepSeek passes with one honest per-pass failure + real-worker recovery demonstration) | `DONE` | Issue #18 (auto-closed by merge) | PR #19 merge `6eed93f` | `2026-09-01` |
| `A-008` | `F008 Alignment Review and Delivery` | `ZCode feature-dev session` | Alignment review and delivery end to end (deterministic coverage/findings, reasoned overrides with audit, draft/validated labelled ZIP export, printable report; SF-1 retry defect fixed with regression test) | `DONE` | Issue #16 (auto-closed by merge) | PR #17 merge `1982ac9` | `2026-09-01` |
| `A-007` | `F007 Versioned Targeted Regeneration` | `ZCode feature-dev session` | Versioned targeted regeneration delivered end to end (impact matrix, scoped runs with scope-once idempotency, retained provenance with zero re-billing, coverage gates, 版本对比 view; three delivery-found defects fixed with tests) | `DONE` | Issue #14 (closed) | PR #15 merge `2b36d73` | `2026-09-01` |
| `A-006` | `F006 Layered Run Evidence` | `ZCode feature-dev session` | Layered run evidence delivered end to end (five-kind inventory/summary/events, estimated-cost telemetry, explanation narration, SSE keepalive fix for the F003 residual, B-001 closed) | `DONE` | Issue #12 (closed) | PR #13 merge `21bef27` | `2026-08-31` |
| `A-005` | `F005 Lesson Exercises and Answers` | `ZCode feature-dev session` | Third artifact vertical slice delivered end to end (paired DOCX exercises/answers, difficulty-bound runs, deterministic pairing validation) | `DONE` | Issue #10 (closed) | PR #11 merge `5804e86` | `2026-08-31` |
| `A-004` | `F004 Editable Lesson Slide Decks` | `ZCode feature-dev session` | Second artifact vertical slice delivered end to end (PPTX decks, prerequisite gate, shared artifact-run components) | `DONE` | Issue #8 (closed) | PR #9 merge `123523a` | `2026-08-30` |
| `A-001/A-002` | `F002 Confirmed Unit Blueprint` | `opencode feature-dev session` | Second teacher-confirmation gate delivered end to end | `DONE` | Issue #3 (closed) | PR #4 merge `8f90bb6` | `2026-08-28` |
| `N/A (pre-STAGE)` | `F001 Grounded Confirmed Brief` | `feature-dev session` | Confirmed brief vertical slice delivered end to end | `DONE` | Issue #1 (closed) | PR #2 merge `1253ca2` | `2026-08-24` |

## Authority and Update Rules

1. `STAGE.md` owns the current project phase, active-member view, coordination blockers, handoffs, and resume points.
2. Before Feature work is bound, `specs/ROADMAP.md` owns its initial `DRAFT/NEXT/BLOCKED` status. After binding, a remote tracker owns Work Status and its `STAGE.md` row is a projection. Temporary authorization, tool, authentication, or availability failure never transfers that authority: preserve status and stop. Use `STAGE_LOCAL:<Activity ID>` only when no remote is bound or after an explicit durable migration unbinds it.
3. `specs/ROADMAP.md` always owns Feature ordering and dependencies and mirrors Work Status after binding. A Feature Spec owns correctness. Gate artifacts own Gate decisions and evidence. `AGENTS.md` owns durable rules. PRs or Delivery Records own delivered changes.
4. Serialize Stage writes through the repository's existing lock or one designated canonical writer. When neither exists, use an optimistic guard: retain the revision and SHA-256 read, compare both immediately before writing, and abort/reconcile if either changed. After two consecutive aborts on unexpected change, record `CONFLICT` and stop the affected update; when neither serialization nor hash comparison is available, stop before writing. Allocate the next `A-xxx` ID under the same guard. A divergent worktree copy is not live project state until the canonical Stage writer reconciles it.
5. Read the latest file and every applicable status authority immediately before updating. Preserve unrelated member rows and user changes; never replace the whole file to fit this template. Record the prior revision/hash as `Parent Snapshot`, then reread after writing and stop on a duplicate ID or unexpected result.
6. Each member or agent changes only its activity and directly affected blocker or handoff rows; a designated writer may apply that scoped change. Change project-level fields only when authoritative evidence supports the transition.
7. Two members may reference the same work item only when explicit collaboration and responsibility boundaries are recorded. Otherwise add a `CONFLICT` and stop the affected transition.
8. Transfer Stage-local authority atomically under the write guard: create or confirm the receiver row, preserve Work Status, change authority to `STAGE_LOCAL:<receiver Activity ID>`, mark the sender as transferred, and accept the handoff in the same update. The sender row remains active until transfer succeeds.
9. Update on assignment, meaningful Skill-stage transition, block, resume, handoff, and completion. Do not log commands, chat history, debugging detail, or every micro-task.
10. When a remote authority disagrees with this file, reconcile from the remote source. If binding, freshness, revision, identity, or authority is uncertain, record `CONFLICT` and stop the affected transition, handoff, or completion; unrelated read-only investigation may continue.
11. Move an activity to `Recently Completed` only after its Work Status is terminal or its authority was transferred. Preserve final status and authority in that row; Git plus the tracker or Delivery Record retains history after the 20-entry window.
12. Follow the applicable Documentation Language for prose and preserve the exact ASCII status tokens above. Never record secrets, credentials, personal data beyond the chosen member identity, or sensitive operational output.

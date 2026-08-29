# Project Stage

## Project Snapshot

| Field | Value |
| --- | --- |
| Snapshot Revision | `STAGE-16` |
| Parent Snapshot | `STAGE-15` @ `c4edcd267d5a` |
| Last Reconciled At | `2026-08-30T00:59:28+08:00` |
| Reconciled By | `ZCode feature-dev session (YMY / Project Owner driving)` |
| Repository Ref | `main @ b727734` |
| Write Coordination | `SINGLE_WRITER:ZCode feature-dev session` |
| Lifecycle Path | `GREENFIELD` |
| Project Phase | `DELIVERY` |
| Overall State | `ACTIVE` |
| Current Milestone | F004 Editable Lesson Slide Decks selected for refinement after F003 delivery |
| Tracking Mode | `REMOTE` |

## Lifecycle Progress

| Area / Milestone | State | Authoritative Evidence | Next Condition |
| --- | --- | --- | --- |
| Macro design and Feature Map | `COMPLETE` | `specs/ROADMAP.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` | N/A |
| F001 Grounded Confirmed Brief | `COMPLETE` | Issue #1 (closed), PR #2 merge `1253ca2`, `specs/F001-grounded-confirmed-brief/` | N/A |
| F002 planning workflow delivered | `COMPLETE` | Issue #3 (closed), PR #4 merge `8f90bb6`, `specs/F002-confirmed-unit-blueprint/` | N/A |
| F003 Recoverable Unit Lesson Plans | `DONE` | Issue #6 (closed), PR #7 merge `ad81c82`, `specs/F003-recoverable-unit-lesson-plans/` | F004/F005 refinement |
| F004+ remaining Feature map | `IN_PROGRESS` | `specs/ROADMAP.md` Feature Map + Issue #8 | F004 gates (`SPEC READY` next), then delivery |

## Active Work

| Activity ID | Work Item | Member | Type | Skill | Skill Stage | Activity State | Work Status | Branch / Worktree | Status Authority | Next Checkpoint | Updated At |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A-004` | `F004 Editable Lesson Slide Decks` | `ZCode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `REVIEW` | `ACTIVE` | `REVIEW` | `feature/F004-editable-lesson-slide-decks` | `https://github.com/MaoyuanYang/LessonCanvas/issues/8` | Delivery decision on M-1 residual (two env-blocked deck E2E journeys) | `2026-08-30T00:59:28+08:00` |
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

## Blockers and Conflicts

| ID | Affected Activity / Work Item | Type | Evidence | Owner | Unblock / Resolution Condition |
| --- | --- | --- | --- | --- | --- |
| `B-001` | F002 | `NON_BLOCKING residual from F001` | Authenticated Playwright E2E RESOLVED 2026-08-28: Clerk device verification disabled by owner; full teacher-journey spec passes against live DeepSeek after live-model JSON-contract fixes (PR [#5](https://github.com/MaoyuanYang/LessonCanvas/pull/5) merged `f6d3b4a`, authorized merge by `YMY / Project Owner`; main re-verified 80 backend tests + ruff). Remaining: keyboard manual pass pending; Postgres LangGraph checkpointer investigation deferred to F012 | `YMY / Project Owner` | Keyboard manual pass at next UI touch; checkpointer at F012 |

## Handoffs

| From | To | Work Item | Resume From | Required Inputs | Authority Transfer | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `feature-dev F001 session` | `feature-dev F002 session` | `F002` | `WORK_ITEM_BINDING` | F001 delivery records, F002 DRAFT Spec, Issue #3 | `N/A` (remote authority continuous) | `ACCEPTED` |

## Recently Completed

| Activity ID | Work Item | Member | Outcome | Final Work Status | Final Status Authority | Delivery Evidence | Completed At |
| --- | --- | --- | --- | --- | --- | --- | --- |
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

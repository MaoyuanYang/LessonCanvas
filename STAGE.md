# Project Stage

## Project Snapshot

| Field | Value |
| --- | --- |
| Snapshot Revision | `STAGE-1` |
| Parent Snapshot | `INITIAL` |
| Last Reconciled At | `2026-08-28T16:03:34+08:00` |
| Reconciled By | `opencode feature-dev session (YMY / Project Owner driving)` |
| Repository Ref | `main @ 8bf078e` |
| Write Coordination | `SINGLE_WRITER:opencode feature-dev session` |
| Lifecycle Path | `GREENFIELD` |
| Project Phase | `DELIVERY` |
| Overall State | `ACTIVE` |
| Current Milestone | F002 Confirmed Unit Blueprint delivered as the second teacher authority gate |
| Tracking Mode | `REMOTE` |

## Lifecycle Progress

| Area / Milestone | State | Authoritative Evidence | Next Condition |
| --- | --- | --- | --- |
| Macro design and Feature Map | `COMPLETE` | `specs/ROADMAP.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` | N/A |
| F001 Grounded Confirmed Brief | `COMPLETE` | Issue #1 (closed), PR #2 merge `1253ca2`, `specs/F001-grounded-confirmed-brief/` | N/A |
| F002 Confirmed Unit Blueprint | `ACTIVE` | Issue #3 (writable work-status authority) | `SPEC READY` Gate decision |
| F003+ remaining Feature map | `NOT_STARTED` | `specs/ROADMAP.md` Feature Map | F002 DONE |

## Active Work

| Activity ID | Work Item | Member | Type | Skill | Skill Stage | Activity State | Work Status | Branch / Worktree | Status Authority | Next Checkpoint | Updated At |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A-001` | `F002 Confirmed Unit Blueprint` | `opencode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `DELIVERY` | `ACTIVE` | `REVIEW` | `feature/F002-confirmed-unit-blueprint` | `https://github.com/MaoyuanYang/LessonCanvas/issues/3` | Delivery decision (commit/push/PR authorization) | `2026-08-28T16:03:34+08:00` |

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
| F002 | `DONE` | `NOT_READY` | Delivery pending PR authorization; review recorded in `specs/F002-confirmed-unit-blueprint/review.md` |

## Blockers and Conflicts

| ID | Affected Activity / Work Item | Type | Evidence | Owner | Unblock / Resolution Condition |
| --- | --- | --- | --- | --- | --- |
| `B-001` | F002 | `NON_BLOCKING residual from F001` | Authenticated Playwright E2E pending Clerk device-verification disable; Postgres LangGraph checkpointer investigation deferred to F012 | `YMY / Project Owner` | Revisit at F012 or when Clerk configuration changes |

## Handoffs

| From | To | Work Item | Resume From | Required Inputs | Authority Transfer | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `feature-dev F001 session` | `feature-dev F002 session` | `F002` | `WORK_ITEM_BINDING` | F001 delivery records, F002 DRAFT Spec, Issue #3 | `N/A` (remote authority continuous) | `ACCEPTED` |

## Recently Completed

| Activity ID | Work Item | Member | Outcome | Final Work Status | Final Status Authority | Delivery Evidence | Completed At |
| --- | --- | --- | --- | --- | --- | --- | --- |
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

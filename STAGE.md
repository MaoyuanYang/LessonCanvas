# Project Stage

## Project Snapshot

| Field | Value |
| --- | --- |
| Snapshot Revision | `STAGE-83` |
| Parent Snapshot | `STAGE-82` @ `9fff33a2ea92` (pre-write hash guard; PR #27 merged `66a0b6c`, main re-verified) |
| Last Reconciled At | `2026-09-03T01:03:40+08:00` |
| Reconciled By | `ZCode feature-dev session (YMY / Project Owner driving)` |
| Repository Ref | `main @ 66a0b6c` (PR #27 merge; F013 delivered) |
| Write Coordination | `SINGLE_WRITER:ZCode feature-dev session` |
| Lifecycle Path | `GREENFIELD` |
| Project Phase | `COMPLETE` |
| Overall State | `ACTIVE` |
| Current Milestone | F013 Teacher Memory DONE (PR #27 merge `66a0b6c`; backend 515+4skip + ruff, web 108 + tsc + lint 0 errors on main; TS-026 live DeepSeek evidence recorded; Issue #26 closed). Phase-1 Feature Map complete: F001–F013 all DONE. Follow-up candidate: public cloud/internet exposure deployment Feature (F012 D1 residual). Prior: F012 DONE (deployed LAN stack healthy; ADR-0006 delivered) |
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
| `A-013` | `F013 Teacher Memory` | `ZCode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `COMPLETE` | `DONE` | `DONE` | `N/A` | `https://github.com/MaoyuanYang/LessonCanvas/issues/26` | N/A - terminal (PR #27 merge `66a0b6c`; DONE record in spec Gate Record) | `2026-09-03T01:03:40+08:00` |
| `A-010` | `F010 Teacher Product Validation` | `ZCode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `COMPLETE` | `DONE` | `DONE` | `N/A` | `https://github.com/MaoyuanYang/LessonCanvas/issues/20` | N/A - terminal (PR #21 merge `683172b`) | `2026-09-01T20:25:15+08:00` |
| `A-012` | `F012 Deployed Portfolio Proof` | `ZCode feature-dev session (YMY / Project Owner driving)` | `AGENT` | `feature-dev` | `COMPLETE` | `DONE` | `DONE` | `N/A` | `https://github.com/MaoyuanYang/LessonCanvas/issues/24` | N/A - terminal (PR #25 merge `c6c7b53`; DONE record in spec Gate Record) | `2026-09-02T23:30:00+08:00` |
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
| F011 | `SPEC READY` | `PASS` | `specs/F011-public-multi-account-guardrails/spec.md` Gate Record @ `d27deee5bfc8` (decision log D1–D11: D2 relaxed limits, D3 no-operator-role + disclosure, D4(b) content-free retained ledger, D6 fast-fail included; ROADMAP projection @ `e758364d566d`) |
| F011 | `UI READY` | `PASS` | `specs/F011-public-multi-account-guardrails/ux-ui.md` UI READY Record @ `ux-ui-f011-r1` / `ab827a69abd6` (owner-ratified 2026-09-01) |
| F011 | `TEST DESIGN READY` | `PASS` | `specs/F011-public-multi-account-guardrails/test-design.md` Record @ `test-design-f011-r1` / `d4ceb6eb0d30`, TS-001..TS-019 (approved 2026-09-01); Plan `plan-f011-r1` @ `850c40e8e41a` valid; `Roadmap Status: READY` then `IN_PROGRESS` recorded 2026-09-01 |
| F011 | `DONE` | `PASS` | PR #23 merge `42fd778`; DONE evidence manifest in `specs/F011-public-multi-account-guardrails/spec.md` Gate Record |
| F012 | `SPEC READY` | `PASS` | revalidated @ `5edfc9352c1e` 2026-09-02 with ADR-0006 (D2/D9 revised, D11/D12 added; prior `8c033df6a4e6` STALE) |
| F012 | `UI READY` | `PASS` | revalidated @ `ux-ui-f012-r2` / `8ddb95ac7315` 2026-09-02 (sign-in flow removed; prior r1 STALE) |
| F012 | `TEST DESIGN READY` | `PASS` | revalidated @ `test-design-f012-r2` / `ff71c903386f` 2026-09-02 (TS-016 added; TS-005/012/015 revised; Plan `plan-f012-r2`; prior r1 STALE) |
| F012 | `DONE` | `PASS` | PR #25 merge `c6c7b53` (commit `dd04e72`); main re-verified backend 477+4skip + ruff, web 97 + tsc + lint 0 errors; deployed LAN stack healthy; DONE evidence manifest in `specs/F012-deployed-portfolio-proof/spec.md` Gate Record |
| F013 | `SPEC READY` | `PASS` | `specs/F013-teacher-memory/spec.md` Gate Record @ `75ee61c2cf0b` (decision log D1–D8; approved 2026-09-02) |
| F013 | `UI READY` | `PASS` | `specs/F013-teacher-memory/ux-ui.md` UI READY Record @ `ux-ui-f013-r1` / `8b39aeebb9a9` (owner-ratified 2026-09-02) |
| F013 | `TEST DESIGN READY` | `PASS` | `specs/F013-teacher-memory/test-design.md` Record @ `test-design-f013-r1` / `c033f186772a`, TS-001..TS-027 (risk-based scope; Plan `plan-f013-r1` @ `427356ca088e` approved together 2026-09-02); `Roadmap Status: READY` recorded 2026-09-02 |
| F013 | `DONE` | `PASS` | PR #27 merge `66a0b6c` (commit `8ddae59`); main re-verified backend 515+4skip + ruff, web 108 + tsc + lint 0 errors; TS-026 live evidence in `specs/F013-teacher-memory/live-evidence.json`; DONE evidence manifest in `specs/F013-teacher-memory/spec.md` Gate Record |

## Blockers and Conflicts

| ID | Affected Activity / Work Item | Type | Evidence | Owner | Unblock / Resolution Condition |
| --- | --- | --- | --- | --- | --- |
| `B-003` | F012 (`A-012`) T8 deployed verification | `RESOLVED 2026-09-02` | Docker socket requires membership (user `ymy` not in `docker` group; passwordless sudo unavailable); `infra/deploy.env` needs real DB/MinIO passwords + DeepSeek key. [UPDATED 2026-09-02, ADR-0006] The Clerk LAN-origin prerequisite is removed. Code T1–T7 complete and green (backend 474+1skip, web 90). | `YMY / Project Owner` | Resolved: owner provided sudo (docker group added; `sg docker` used), DeepSeek key + random infra passwords in untracked `infra/deploy.env`; deploy chain and full T8/T9 executed |
| `B-002` | F007 (`A-007`) | `RESOLVED 2026-08-31` | Owner answered interactively: Issue creation authorized (Issue #14 bound); D1 = field-level conservative matrix; D2 = teacher-triggered per family. Spec finalized with D1..D7 resolved. | `YMY / Project Owner` | Resolved |
| `B-001` | F002 | `NON_BLOCKING residual from F001` | Authenticated Playwright E2E RESOLVED 2026-08-28: Clerk device verification disabled by owner; full teacher-journey spec passes against live DeepSeek after live-model JSON-contract fixes (PR [#5](https://github.com/MaoyuanYang/LessonCanvas/pull/5) merged `f6d3b4a`, authorized merge by `YMY / Project Owner`; main re-verified 80 backend tests + ruff). Remaining: keyboard manual pass pending; Postgres LangGraph checkpointer investigation deferred to F012 | `YMY / Project Owner` | Keyboard manual pass at next UI touch; checkpointer at F012 |

## Handoffs

| From | To | Work Item | Resume From | Required Inputs | Authority Transfer | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `feature-dev F001 session` | `feature-dev F002 session` | `F002` | `WORK_ITEM_BINDING` | F001 delivery records, F002 DRAFT Spec, Issue #3 | `N/A` (remote authority continuous) | `ACCEPTED` |

## Recently Completed

| Activity ID | Work Item | Member | Outcome | Final Work Status | Final Status Authority | Delivery Evidence | Completed At |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A-013` | `F013 Teacher Memory` | `ZCode feature-dev session` | Teacher memory delivered end to end (governed proposal pipeline with identity idempotency + best-effort failure + content-hash dedupe; confirmed records with caps and race-safe admission; snapshot-once subordinate injection across discovery/planning/generation with `memory.applied` traces; deterministic language conflict rule; U6 budget priority with disclosed skips; per-project overrides; account + workspace + evidence surfaces; F009 revision-list pinning joining the comparability signature; F011 deletion sweep extension; adversarial inertness proven; TS-026 live DeepSeek quality evidence incl. a real transient failure and live dedupe; review IF-1..IF-5 dispositioned) | `DONE` | Issue #26 (auto-closed by merge) | PR #27 merge `66a0b6c` | `2026-09-03` |
| `A-012` | `F012 Deployed Portfolio Proof` | `ZCode feature-dev session` | Deployed portfolio proof delivered end to end (local full-stack containers + LAN entry with deploy/smoke/teardown chain, synthetic sample read-only journey + idempotent seeding, live DeepSeek recovery journey TS-029, deletion completeness all-zero + retained ledger, SSE single-process + D10 recheck, teardown/redeploy, a11y/420px spot; ADR-0006 removed Clerk for the MVP — guest workspace tokens, subject rename, deterministic E2E; B-001 checkpointer deadlock found+fixed via entrypoint pre-setup; review IF-1..IF-11 all dispositioned) | `DONE` | Issue #24 (closed) | PR #25 merge `c6c7b53` | `2026-09-02` |
| `A-011` | `F011 Public Multi-Account Guardrails` | `ZCode feature-dev session` | Public multi-account guardrails delivered end to end (PostgreSQL-authoritative nested rate windows, admission + SSE/upload caps, upload hardening with bomb guards, race-safe quotas and workspace resolution, deletion completeness incl. checkpoints with metadata-only residual repair, worker fast-fail F006 M-2, download audits + usage/audit surfaces + D4(b) retained ledger, governed adversarial corpus + 71-path sweep + 5-workspace journey; latent F001 content_type defect fixed; dependency audits clean) | `DONE` | Issue #22 (auto-closed by merge) | PR #23 merge `42fd778` | `2026-09-02` |
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

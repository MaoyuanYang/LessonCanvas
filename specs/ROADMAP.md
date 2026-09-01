# Feature Roadmap

## Product Milestone

Phase 1 produces a publicly inspectable, multi-account LessonCanvas workflow in which a senior-high English teacher confirms grounded unit intent, generates every lesson's editable teaching package, reviews alignment and evidence, recovers or revises versioned work, and sees technical and teacher-product validation reported separately.

## Status Contract

| Status | Meaning |
| --- | --- |
| `DRAFT` | Feature is mapped at macro level and remains intentionally shallow. |
| `NEXT` | The sole Feature selected for refinement by `feature-dev`. |
| `READY` | `SPEC READY`, `UI READY` or an explicit skip, `TEST DESIGN READY`, and current Plan and Tasks are all valid; `coding-start` never sets it. |
| `IN_PROGRESS` | Implementation is active. |
| `REVIEW` | Implementation and evidence are under review. |
| `DONE` | Delivery and documentation sync are complete. |
| `BLOCKED` | A named blocker prevents progress. |

## Feature Map

| ID | Name | Goal | Business Value | Priority | Dependencies | Status | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `F001` | Grounded Confirmed Brief | Confirm a source-grounded teaching brief inside a private teacher project | First real Agent/HITL outcome and ownership proof | `P0` | None | `DONE` | Managed sign-in, private project, allowed sources via MCP, streamed Agent questions, structured brief, and first confirmation gate |
| `F002` | Confirmed Unit Blueprint | Confirm a complete every-lesson unit design | Makes expensive generation governable by teacher intent | `P0` | `F001` | `DONE` | Source-linked unit blueprint, structured revision, and second confirmation gate |
| `F003` | Recoverable Unit Lesson Plans | Generate DOCX lesson plans for every lesson with durable recovery | First useful Office artifact and proof of long-running Agent execution | `P0` | `F002` | `DONE` | Version-bound asynchronous run, all-lesson plans, trace capture, progress, idempotency, checkpoints, and authorized downloads; delivered via PR [#7](https://github.com/MaoyuanYang/LessonCanvas/pull/7) |
| `F004` | Editable Lesson Slide Decks | Generate editable PPTX decks for every lesson | Adds the presentation deliverable and a distinct rendering boundary | `P0` | `F003` | `DONE` | Evidence-linked slide decks with scoped progress, file validation, and recoverable delivery; delivered via PR [#9](https://github.com/MaoyuanYang/LessonCanvas/pull/9) |
| `F005` | Lesson Exercises and Answers | Generate DOCX exercise and answer sets for every lesson | Completes assessment material and exposes correctness risk | `P0` | `F003` | `DONE` | Paired, version-bound exercises and answers with validation, recovery, and authorized download; delivered via PR [#11](https://github.com/MaoyuanYang/LessonCanvas/pull/11) |
| `F006` | Layered Run Evidence | Explain each run to teachers and technical reviewers | Turns hidden telemetry into credible portfolio evidence | `P0` | `F003`, `F004`, `F005` | `DONE` | Teacher-readable explanation with owner-authorized sources, specialist steps, tools, cost, latency, retries, and currently available validation details |
| `F007` | Versioned Targeted Regeneration | Rebuild only affected work after confirmed intent changes | Preserves valid work and demonstrates safe concurrency and cost control | `P0` | `F003`, `F004`, `F005` | `DONE` | Impact preview, immutable revisions, stale conflict handling, supersession, selective regeneration, and version comparison |
| `F008` | Alignment Review and Delivery | Review objective alignment and deliver a selected unit version | Directly resolves the validated teacher problem | `P0` | `F006`, `F007` | `REVIEW` | Cross-artifact findings, severe-issue handling, draft vs validated status, selected-version package and printable report |
| `F009` | Technical Portfolio Evaluation | Produce reproducible Agent, artifact, concurrency, and recovery evidence | Makes technical claims falsifiable | `P0` | `F008` | `DRAFT` | Fixed representative units, trace-bound metrics, fault injection, duplicate/concurrency checks, and technical results |
| `F010` | Teacher Product Validation | Record independent teacher-quality pass, fail, or not-complete status | Prevents technical completion from becoming a false usability claim | `P1` | `F009` | `DRAFT` | External teacher rubric for representative complete units with separate product-validation status |
| `F011` | Public Multi-Account Guardrails | Verify the complete system's privacy, abuse, cost, and deletion controls | Makes public use bounded and defensible | `P0` | `F009` | `DRAFT` | System-wide isolation, quotas, rate/concurrency limits, injection defense, authorized objects, operator audit, and deletion |
| `F012` | Deployed Portfolio Proof | Make the protected workflow independently inspectable in the cloud | Converts repository claims into observable release evidence | `P0` | `F009`, `F011` | `DRAFT` | Public entry, synthetic demo data, complete runtime deployment, accessibility, recovery, and honest validation status |
| `F013` | Teacher Memory | Personalize future work with teacher-confirmed workspace memory | Faster repeat preparation and governed-memory portfolio evidence | `P1` | `F001` | `DRAFT` | Agent-proposed, teacher-confirmed memory records; management UI; subordinate context application; untrusted-input handling |

Only `DRAFT/NEXT/READY/IN_PROGRESS/REVIEW/DONE/BLOCKED` may appear in this Roadmap. No Feature becomes `READY` during `coding-start`.

## Dependency View

```text
F001 -> F002
F002 -> F003
F003 -> F004
F003 -> F005
F003 + F004 + F005 -> F006
F003 + F004 + F005 -> F007
F006 + F007 -> F008
F008 -> F009
F009 -> F010
F009 -> F011
F009 + F011 -> F012
F001 -> F013
```

## Handoff

### Current: F008 NEXT

- Feature: `F008 Alignment Review and Delivery`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-09-01 (start instruction after F007 DONE; dependencies F006 and F007 both DONE).
- Status: Issue #16 bound 2026-09-01; Gates `SPEC READY` @ `dc301bba1a83`, `UI READY` @ `ux-ui-f008-r1` / `6bca800ac896`, `TEST DESIGN READY` @ `test-design-f008-r1` / `6d7979391f92` all PASS (D1–D4 owner-selected interactively; D5–D8 evidence-resolved). Plan `plan.md` (T0–T7) executed on `feature/F008-alignment-review-and-delivery`: backend module + routers + migration `f008c3e7a9b1` + 17 alignment tests; web 对齐与交付 tab + override dialogs + delivery region + print report route + family-panel links. Verification: backend suite exit-0 incl. alignment tests + ruff clean; web 57/57 + eslint/tsc/build clean; E2E fault-stack TS-016/TS-017 green (M-1/M-2/L-1 residuals recorded in test-design evidence snapshot); self review found+fixed SF-1 failed-export retry with regression test. `Roadmap Status: REVIEW` 2026-09-01; PR [#17](https://github.com/MaoyuanYang/LessonCanvas/pull/17) opened 2026-09-01 (commit/push/PR/Issue update authorized by `YMY / Project Owner`); merge pending authorization.

### Previous: F007 DONE
- Work item: [GitHub Issue #14](https://github.com/MaoyuanYang/LessonCanvas/issues/14) — bound 2026-08-31; auto-closed on delivery.
- Gates: `SPEC READY: PASS` (`fb351456a2ee`), `UI READY: PASS` (`ux-ui-f007-r1` / `97597ad3c608`), `TEST DESIGN READY: PASS` (`test-design-f007-r1` / `69c9d0532f7a`), approved by `YMY / Project Owner` on 2026-08-31 (D1 field-level conservative matrix and D2 teacher-triggered per-family regeneration selected interactively). `DONE: PASS` recorded 2026-09-01 after PR [#15](https://github.com/MaoyuanYang/LessonCanvas/pull/15) merged as `2b36d73` (full delivery flow authorized by `YMY / Project Owner`).
- DONE evidence manifest (working tree @ gate time): spec `ae06a143e088`, ux-ui `92e90e6e7cdf`, test-design `402f001db60f`, plan `c35bfd12e495`, review `251e53f96b31`, ROADMAP pre-DONE `636d8f141a87`; verification: backend full suite green incl. 11 regeneration tests + ruff clean, web 51/51 + eslint/tsc/build clean, E2E fault TS-014/TS-016 + live TS-015 (real DeepSeek + real Worker) green; main re-verified (backend exit-0 + ruff + web 51/51).
- Refinement resolved: D1 field-level conservative impact matrix (citations non-intent, uncertainty widens visibly); D2 teacher-triggered per-family regeneration with generalized plan coverage; D3 checkpoint supersession inherited; D4 version-seeded revision drafts; D5 retained artifacts under original provenance, zero re-billing; D6 structured comparison with embedded transition impact; D7 stale-base conflicts.
- Delivery-found defects fixed with tests before merge: M-1 retained plans never cover plan-affected lessons; M-2 comparison embeds its transition impact; M-3 pair-aware current-run rule (settled old runs never mask the new pair's start surface).
- Next actionable: F008 Alignment Review and Delivery refinement (F006 + F007 complete its dependencies).

### Previous: F006 DONE

- Feature: `F007 Versioned Targeted Regeneration`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-08-31 (start instruction after F006 DONE; dependencies F003/F004/F005 all DONE; F006 DONE completes the other half of the F008 dependency).
- Gates: `SPEC READY` PASS (`fb351456a2ee`), `UI READY` PASS (`ux-ui-f007-r1` / `97597ad3c608`), `TEST DESIGN READY` PASS (`test-design-f007-r1` / `69c9d0532f7a`), approved by `YMY / Project Owner` on 2026-08-31 (D1 field-level conservative matrix and D2 teacher-triggered per-family regeneration selected interactively; D3–D7 evidence-resolved). Plan `specs/F007-versioned-targeted-regeneration/plan.md` (T0–T6) valid; `Roadmap Status: READY` recorded 2026-08-31. Implementation complete on `feature/F007-versioned-targeted-regeneration` (T0–T6): backend full suite green incl. 11 regeneration tests + ruff; web 51/51 + eslint/tsc/build clean; E2E TS-014/TS-016 fault stack + TS-015 live stack green; three delivery-found defects fixed with tests (review.md M-1..M-3); docs synced. `Roadmap Status: REVIEW` 2026-08-31; delivery pending authorization.
- Residuals in scope by routing: F004 M-2 fast-fail hardening stays with F011; F007 owns versioned revision/impact/supersession/selective-regeneration semantics.

### Previous: F006 DONE

- Feature: `F006 Layered Run Evidence`
- Work item: [GitHub Issue #12](https://github.com/MaoyuanYang/LessonCanvas/issues/12) — bound 2026-08-31; auto-closed on delivery.
- Gates: `SPEC READY: PASS` (`b43922d2cc17`), `UI READY: PASS` (`ux-ui-f006-r1` / `4bff46959bb0`), `TEST DESIGN READY: PASS` (`test-design-f006-r1` / `e2e261591bd8`), approved by `YMY / Project Owner` on 2026-08-31 (D2 estimated-USD cost and D3 five-kind coverage selected interactively). `DONE: PASS` recorded 2026-08-31 after PR [#13](https://github.com/MaoyuanYang/LessonCanvas/pull/13) merged as `21bef27` (full delivery flow authorized by `YMY / Project Owner`).
- DONE evidence manifest (working tree @ gate time): spec `a9b445a541cf`, ux-ui `0028c5b3b77c`, test-design `46b7a8c90802`, plan `c487fc9b7b19`, review `f245463363a2`, ROADMAP pre-DONE `2497c71650ed`; verification: backend full suite green incl. 20 evidence tests + ruff clean, web 47/47 + eslint/tsc/build clean, E2E fault TS-020a/020/TS-022 (B-001 keyboard pass) + live TS-021 (real DeepSeek + real Worker); main re-verified (backend exit-0 + ruff + web 47/47).
- Residuals handled by F006: F003 SSE early-drop root-caused and FIXED (comment keepalives on generation/deck/exercise/narration streams + regression test + live probe verification); F004 M-2 StaleDataError REPRODUCED with self-heal evidence, fast-fail hardening routed to F011; STAGE B-001 keyboard pass executed and closed; F002 findings-embedding deferral not needed by this read model (revisit at F008).
- Delivery-recorded deviations (owner-visible in review.md): M-1 environment re-run class, M-3 interfaces-over-Zod convention follow, L-1 narration stream token capture deferred to F009, L-2 multi-DB probe hygiene note.
- Next actionable: F007 refinement (F006 completes half of the F008 dependency; F007 supplies the rest).

### Previous: F005 DONE

- Feature: `F006 Layered Run Evidence`
- Work item: [GitHub Issue #12](https://github.com/MaoyuanYang/LessonCanvas/issues/12) — bound 2026-08-31; authorized by `YMY / Project Owner`.
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-08-31 (F007 deferred as the parallel-eligible alternative; dependencies F003/F004/F005 all DONE).
- Gates: `SPEC READY` PASS (`b43922d2cc17`), `UI READY` PASS (`ux-ui-f006-r1` / `4bff46959bb0`), `TEST DESIGN READY` PASS (`test-design-f006-r1` / `e2e261591bd8`), approved by `YMY / Project Owner` on 2026-08-31. Plan `specs/F006-layered-run-evidence/plan.md` (T0-T7) valid; `Roadmap Status: READY` recorded 2026-08-31. Implementation complete on `feature/F006-layered-run-evidence` (T0–T7): all suites green (backend exit-0 incl. 20 evidence tests, web 47 passed, lint/typecheck/build clean), E2E TS-020a/020/022/021 green across fault and live stacks, TS-023 root-caused and fixed (SSE keepalive + regression), TS-024 reproduced with self-heal evidence routed to F011, review and docs sync recorded. `Roadmap Status: REVIEW` 2026-08-31; delivery pending commit/push/PR authorization.
- Residuals routed here by prior features: F003 SSE early-drop root cause; F004 M-2 StaleDataError run-teardown semantics (shared with F011); F002 findings-embedding deferral only if cross-version finding queries become needed; STAGE B-001 keyboard manual pass at this UI touch.

### Previous: F005 DONE

- Feature: `F005 Lesson Exercises and Answers`
- Work item: [GitHub Issue #10](https://github.com/MaoyuanYang/LessonCanvas/issues/10) — bound 2026-08-31; closed on delivery.
- Gates: `SPEC READY: PASS` (`41b391751a33`), `UI READY: PASS` (`ux-ui-f005-r1` / `78923f6468b7`), `TEST DESIGN READY: PASS` (`test-design-f005-r1` / `29b9ad5c42d2`), approved by `YMY / Project Owner` on 2026-08-31. `DONE: PASS` recorded 2026-08-31 after PR [#11](https://github.com/MaoyuanYang/LessonCanvas/pull/11) merged as `5804e86` (authorized commit/push/PR/merge by `YMY / Project Owner`).
- DONE evidence manifest (working tree @ gate time): spec `807f4c857bf8`, ux-ui `98e79e83c0cd`, test-design `b9f922a0c5cb`, plan `d36cc2307cd8`, review `446769289540`, ROADMAP pre-DONE `3d795c14b6db`; verification: 150 backend tests, 39 web tests, ruff/eslint/tsc/build clean, exercise E2E 7/7 journeys green (TS-024/025/026 fault stack on the F003 eager profile, TS-028 small-cap, TS-027/029/030 live stack with real DeepSeek + real Worker), TS-031 Word 16.0 COM smoke over all 12 pair files; main re-verified (150 passed + ruff clean + 39 web passed).
- Refinement resolved: D1 blueprint-objective-driven six-category catalog with renderer-owned continuous numbering; D2 pair-as-checkpoint inherited; D3 complete-lesson-plan prerequisite (no deck requirement) + own cap; D4/D5/D6 contracts inherited (assembler extended to blueprint objectives + tier); D7 deterministic structural + pairing validation with one controlled Word smoke; D8 python-docx behind MCP-compatible definitions; D9 structured difficulty tier selected at start, recorded once, immutable per run, tier switch via the supersession path. UI decisions D-EXGEN/D-EXDIFF/D-EXPROG/D-EXNARR/D-EXART/D-EXRECN (shared artifact-run surfaces consumed unchanged as the recorded third consumer).
- Live-model defect fixed during delivery: multi-line writing-task reference answers broke the pairing validator's first-line-anchored numbered-entry regex (false `missing answers`); fixed with a DOTALL leading-number anchor + regression test; all captured live drafts replay green.
- Residuals (owner-visible in review.md): M-1 intermittent Clerk dev-instance session hang on TS-025 (F004 M-1 class; re-run passed; substitute coverage green). M-2 fault stack ran on the F003 eager profile (real-Worker retries insert 2x180s Celery delays beyond journey budgets — the F004 M-1 trap). M-3 orphan/missing-number pairing negatives covered by validator-level fixtures since the renderer owns numbering.
- Next actionable: F006/F007 refinement (F005 completes their dependencies).

### Previous: F004 DONE

- Feature: `F004 Editable Lesson Slide Decks`
- Work item: [GitHub Issue #8](https://github.com/MaoyuanYang/LessonCanvas/issues/8) — bound 2026-08-29; closed on delivery.
- Gates: `SPEC READY: PASS` (`b913da61ec40`), `UI READY: PASS` (`ux-ui-f004-r1` / `05e5748c9a4d`), `TEST DESIGN READY: PASS` (`test-design-f004-r1` / `4afef155b09f`), approved by `YMY / Project Owner` on 2026-08-29. `DONE: PASS` recorded 2026-08-30 after PR [#9](https://github.com/MaoyuanYang/LessonCanvas/pull/9) merged as `123523a` (authorized merge by `YMY / Project Owner`).
- DONE evidence manifest (working tree @ gate time): spec `b0ecf7c28df0`, ux-ui `475e56ba6e18`, test-design `2e2a704263d4`, plan `9647ab81974e`, review `137184659551`; verification: 124 backend tests, 30 web tests, ruff/eslint/tsc/build clean, deck E2E 5 journeys green (TS-024/TS-025 fault stack; TS-030/TS-027/TS-029 live stack with real DeepSeek + real Worker), TS-031 PowerPoint COM smoke passed; main re-verified (124 passed).
- Refinement resolved: D1 fixed deck skeleton with bounded stage slides (renderer-owned structural titles); D2 per-deck checkpoint inherited; D3 complete-lesson-plan prerequisite + own deck-run cap; D4/D5/D6 contracts inherited; D7 deterministic structural validation + controlled Office smoke; D8 python-pptx behind MCP-compatible definitions; D9 download + structure summary, no browser preview. UI decisions D-DECKGEN/D-DECKPROG/D-DECKNARR/D-DECKART/D-DECKRECN/D-DECKDS (Design System promotion of artifact progress list + outcome banners).
- Residual (owner-accepted M-1): deck E2E TS-026 (partial failure + scoped resume) and TS-028 (cap exhaustion) environment-blocked by intermittent Clerk dev-instance session failure (F003's unchanged journeys showed the same hang); automated substitute coverage green; resume condition: re-run under stable auth and append evidence to the Test Design Execution Evidence Snapshot.

### Previous: F003 DONE

- Feature: `F003 Recoverable Unit Lesson Plans`
- Work item: [GitHub Issue #6](https://github.com/MaoyuanYang/LessonCanvas/issues/6) — bound 2026-08-29; closed on delivery.
- Gates: `SPEC READY: PASS` (`193e90d10b68`), `UI READY: PASS` (`ux-ui-f003-r1` / `43f93abc6ed3`), `TEST DESIGN READY: PASS` (`test-design-f003-r2` / `880a6a4a418c`), approved by `YMY / Project Owner` on 2026-08-29. `DONE: PASS` recorded 2026-08-29 after PR [#7](https://github.com/MaoyuanYang/LessonCanvas/pull/7) merged as `ad81c82` (authorized merge by `YMY / Project Owner`).
- DONE evidence manifest (working tree @ gate time): spec `ea5efb32e94e`, ux-ui `7b2630aad7ee`, test-design `e72245eb84e4`, plan `afc78ad33896`, review `a23c67784a9d`; verification: 102 backend tests, 22 web tests, ruff/eslint/tsc clean, public E2E 3/3, authenticated primary journey 1/1 (live stack), six designed journeys TS-024..029 green across live and fault stacks; main re-verified (102 passed).
- Refinement resolved: D1 standard lesson-plan structure; D2 per-lesson checkpoints; D3 per-run call cap only; D4 authoritative SSE event log with Last-Event-ID replay (resolves API.md open item); D5 failure taxonomy; D6 three-specialist split; D7 structural validation; D8 python-docx + three new tables. UI decisions D-GEN/D-PROG/D-NARR/D-ART/D-RECN.
- Residual (non-blocking): SSE early-drop root cause deferred to F006 (mitigated by 3s snapshot polling + auto-reconnect); human-teacher keyboard review recommended as follow-up to the scripted TS-024 pass; Clerk dev-instance rate limits handled in E2E via @clerk/testing token.

### Previous: F002 DONE

- Feature: `F002 Confirmed Unit Blueprint`
- Work item: [GitHub Issue #3](https://github.com/MaoyuanYang/LessonCanvas/issues/3) — writable work-status authority bound 2026-08-28; closed on delivery.
- Gates: `SPEC READY: PASS` (`108178994342`), `UI READY: PASS` (`a8cfd23189ac`), `TEST DESIGN READY: PASS` (`9c997cfa2b6f`), approved by `YMY / Project Owner` on 2026-08-28. `DONE: PASS` with `Roadmap Status: DONE` recorded 2026-08-28 after PR [#4](https://github.com/MaoyuanYang/LessonCanvas/pull/4) merged as `8f90bb6` (authorized merge by `YMY / Project Owner`).
- DONE evidence manifest (merged working tree @ `8f90bb6`): spec `841e5020239d`, ux-ui `26f5938e9f30`, test-design `67e1b50fa36f`, plan `75b2f6e6bbb3`, review `35b8ee303938`, ROADMAP pre-DONE `cce584bc5215`, AGENTS `b03a2200602b`; verification: 73 backend tests, 16 web tests, ruff/eslint/tsc/build clean, public E2E 3/3; merge re-verified on main (73 passed).
- Refinement resolved: D1 four hard completeness checks; D2 lesson granularity; D3 blocking/waivable conflict tiers; D4 brief-diff + stale supersession; D5/D5a/D5b interview-style planning 6x3; D6 sources + standards MCP grounding wired; D7 no per-run cap with workspace quota; D8 read-only small screen. UI decisions D-NAV/D-CONVO/D-FIND.
- Residual (non-blocking, tracked for later Features): authenticated E2E blueprint journey RESOLVED 2026-08-28 after Clerk device-verification disable and live-model JSON-contract fixes (PR [#5](https://github.com/MaoyuanYang/LessonCanvas/pull/5) merged `f6d3b4a`; full journey green against live DeepSeek, main re-verified); keyboard manual pass still pending (STAGE B-001); findings-embedding deferral (review L-2) revisited by F006/F007 if cross-version finding queries are needed.

### Previous: F001 DONE

- Feature: `F001 Grounded Confirmed Brief`
- Work item: [GitHub Issue #1](https://github.com/MaoyuanYang/LessonCanvas/issues/1) (closed 2026-08-28 after delivery).
- Gates: `SPEC READY: PASS` (`d7ae5094c490`), `UI READY: PASS` (`c4cd127cb372`), `TEST DESIGN READY: PASS` (`dc6978dfefc8`), all approved by `YMY / Project Owner` on 2026-08-24.
- Plan and Tasks: `specs/F001-grounded-confirmed-brief/plan.md` @ `0092f169df34` (`plan-f001-r1`, 13 interleaved tasks T0–T12).
- Refinement resolved: providers (Clerk, DeepSeek, local MinIO), source formats, standards-snapshot MCP tool, UUIDv7, stop semantics, brief completeness, questioning cap, small-screen boundary, deletion evidence.
- Implementation: T0–T12 complete; `DONE` 2026-08-24. Delivery PR [#2](https://github.com/MaoyuanYang/LessonCanvas/pull/2) merged as `1253ca2` (authorized and merged by `YMY / Project Owner`).
- Residual (non-blocking, tracked for later Features): authenticated E2E unblocked 2026-08-28 (device verification disabled; journey passes with live model; PR [#5](https://github.com/MaoyuanYang/LessonCanvas/pull/5) merged `f6d3b4a`); Postgres LangGraph checkpointer investigation deferred to F012.

## Sequencing Notes

- Identity, persistence, storage, Agent runtime, and UI foundations are implementation work inside the first owning Vertical Slice; they are not separate Features.
- `F004` and `F005` may be refined in parallel after `F003`, but neither bypasses the versioned run and recovery contract established there.
- `F010` does not block an honest technical portfolio release. `F012` must display product validation as passed, failed, or not complete.
- Security, ownership, accessibility, and untrusted-input behavior are obligations in every Feature. `F011` verifies the completed system rather than introducing these concerns late.
- Token streaming lands with `F001` (interview), `F003` (generation narration), and `F006` (explanation); MCP consumption lands with `F001` (official sources) and `F003` (tool definitions).
- `F013` may be refined after `F001`; `F003`–`F005` can adopt confirmed memory as optional context after `F013` without a hard dependency.

## Roadmap Risks

- `F001` crosses identity, source, Agent, structured-state, streaming, MCP, and UI boundaries. Keep its outcome to one confirmed brief and defer unit planning and artifacts.
- `F003` is the largest early risk because it introduces full-unit long-running execution. It may be refined only into sub-outcomes that still deliver teacher-visible all-lesson value, not infrastructure-only tasks.
- Full trace retention increases deletion and operator-access risk across `F006` and `F011`; public portfolio samples remain synthetic-only.
- Exact providers, official sources, formats, evaluation topics, and rubric details remain Feature-level questions with documented resolution points.
- Product validation has one stable external teacher, so conclusions remain bounded to that evidence and cannot be generalized without new research.

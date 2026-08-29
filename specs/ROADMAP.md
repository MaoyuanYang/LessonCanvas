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
| `F004` | Editable Lesson Slide Decks | Generate editable PPTX decks for every lesson | Adds the presentation deliverable and a distinct rendering boundary | `P0` | `F003` | `REVIEW` | Evidence-linked slide decks with scoped progress, file validation, and recoverable delivery; selected 2026-08-29 by `YMY / Project Owner`; SPEC/UI/TEST DESIGN Gates PASS; implementation complete with review residual M-1 (two env-blocked deck E2E journeys, automated substitute coverage green) awaiting delivery decision |
| `F005` | Lesson Exercises and Answers | Generate DOCX exercise and answer sets for every lesson | Completes assessment material and exposes correctness risk | `P0` | `F003` | `DRAFT` | Paired, version-bound exercises and answers with validation, recovery, and authorized download |
| `F006` | Layered Run Evidence | Explain each run to teachers and technical reviewers | Turns hidden telemetry into credible portfolio evidence | `P0` | `F003`, `F004`, `F005` | `DRAFT` | Teacher-readable explanation with owner-authorized sources, specialist steps, tools, cost, latency, retries, and currently available validation details |
| `F007` | Versioned Targeted Regeneration | Rebuild only affected work after confirmed intent changes | Preserves valid work and demonstrates safe concurrency and cost control | `P0` | `F003`, `F004`, `F005` | `DRAFT` | Impact preview, immutable revisions, stale conflict handling, supersession, selective regeneration, and version comparison |
| `F008` | Alignment Review and Delivery | Review objective alignment and deliver a selected unit version | Directly resolves the validated teacher problem | `P0` | `F006`, `F007` | `DRAFT` | Cross-artifact findings, severe-issue handling, draft vs validated status, selected-version package and printable report |
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

### Current: F003 DONE

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

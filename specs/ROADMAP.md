# Feature Roadmap

## Product Milestone

Phase 1 produces a publicly inspectable, multi-account LessonCanvas workflow in which a senior-high English teacher confirms grounded unit intent, generates every lesson's editable teaching package, reviews alignment and evidence, recovers or revises versioned work, and sees technical and teacher-product validation reported separately.

## Phase 2 Milestone

Phase 2 closes the gap between documented and actual grounding capability and deepens Agent specialization under the existing governance: source context recalled by semantic similarity with chunk-level traceable citations (F014), specialists that call whitelisted tools themselves inside a bounded traced loop (F015), and a real specialist division of labor with per-stage trace and model-assisted quality review (F016). Phase-1 close-out state is recorded in `specs/PHASE1-retrospective.md` (2026-09-03).

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
| `F008` | Alignment Review and Delivery | Review objective alignment and deliver a selected unit version | Directly resolves the validated teacher problem | `P0` | `F006`, `F007` | `DONE` | Cross-artifact findings, severe-issue handling, draft vs validated status, selected-version package and printable report |
| `F009` | Technical Portfolio Evaluation | Produce reproducible Agent, artifact, concurrency, and recovery evidence | Makes technical claims falsifiable | `P0` | `F008` | `DONE` | Fixed representative units, trace-bound metrics, fault injection, duplicate/concurrency checks, and technical results |
| `F010` | Teacher Product Validation | Record independent teacher-quality pass, fail, or not-complete status | Prevents technical completion from becoming a false usability claim | `P1` | `F009` | `DONE` | External teacher rubric for representative complete units with separate product-validation status |
| `F011` | Public Multi-Account Guardrails | Verify the complete system's privacy, abuse, cost, and deletion controls | Makes public use bounded and defensible | `P0` | `F009` | `DONE` | System-wide isolation, quotas, rate/concurrency limits, injection defense, authorized objects, operator audit, and deletion |
| `F012` | Deployed Portfolio Proof | Make the protected workflow independently inspectable in the cloud | Converts repository claims into observable release evidence | `P0` | `F009`, `F011` | `DONE` | Public entry, synthetic demo data, complete runtime deployment, accessibility, recovery, and honest validation status |
| `F013` | Teacher Memory | Personalize future work with teacher-confirmed workspace memory | Faster repeat preparation and governed-memory portfolio evidence | `P1` | `F001` | `DONE` | Agent-proposed, teacher-confirmed memory records; management UI; subordinate context application; untrusted-input handling |
| `F014` | Semantic Source Retrieval | Recall the most relevant source chunks by semantic similarity and cite them traceably | Makes the documented pgvector grounding real and improves grounding quality and traceability as corpora grow | `P0` | None | `REVIEW` | Implemented on `feature/F014-semantic-source-retrieval` (T0–T8): adapter + migrations + backfill + retrieval + four call sites + chunk citations + guardrails/evaluation + web surfaces; 547 backend + 113 web + E2E TS-025 green, review `review-f014-r1` no Critical; delivery and TS-026 live re-baseline pending owner authorization |
| `F015` | Governed Model Tool Calling | Let workflow specialists invoke whitelisted tools in a bounded traced loop | Turns MCP-compatible tool definitions into real governed agentic tool use | `P1` | None | `DRAFT` | Adapter `tools`/`tool_calls` support, bounded tool loop in discovery/planning, per-round trace, whitelist refusal policy, F009 fault scenarios and signature; drafted 2026-09-03 |
| `F016` | Specialist Role Expansion | Add source-analysis, activity-design, and quality-review specialists to the workflows | Real specialist division of labor with per-stage trace and model-assisted review | `P1` | `F014` | `DRAFT` | Structured source analysis, designer→writer split for lesson plans, reviewer with one bounded revise round, cap/quota/cost updates, F009 stage-set signature; drafted 2026-09-03 |

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
F014 -> F016
```

## Handoff

### Current: F014 NEXT — spec refined, awaiting SPEC READY approval

- Feature: `F014 Semantic Source Retrieval`
- Selection: `NEXT` from Phase-2 planning confirmed by `YMY / Project Owner` on 2026-09-03 at `feature-dev` start.
- Direction: capability audit on 2026-09-03 (owner session) compared delivered behavior against project claims and found three gaps — the documented pgvector semantic recall is unimplemented (grounding is full-corpus truncation), tool definitions are not model-callable (all tool calls are issued by orchestration code), and the source-analysis / activity-design / quality-review specialist roles do not exist. Phase 2 makes those claims true under the existing governance. F014 addresses the first gap.
- Work item: [GitHub Issue #28](https://github.com/MaoyuanYang/LessonCanvas/issues/28) — bound 2026-09-03 (authorized); work-status authority.
- Spec refinement complete 2026-09-03: decision log D1–D9 resolved interactively (D1 local in-process embedding fastembed + bge-small-zh-v1.5 512-dim; D2 deploy-time idempotent batch backfill; D3 exclude-with-disclosure; D4 proceed with explicit ungrounded state; D5 full live re-baseline at delivery; D6 embedding classified under upload processing, no new quota; D9 all three generation families retrieve — generation payloads inject no source text today, so this is a new capability, not a truncation swap; D7 k=6/budget 2000 chars and D8 standards-stays-deterministic recorded as maintainer judgment). Baseline re-verified on `main` during refinement.
- L3 decision recorded: ADR-0007 `Accepted` 2026-09-03 (local in-process embedding model behind a thin adapter; hosted embedding APIs excluded in Phase 2).
- Phase-1 close-out is recorded in `specs/PHASE1-retrospective.md` (2026-09-03); its owner-decision residuals (F010 real-teacher evidence import, public cloud exposure deployment Feature, DTO convention) remain open and separate from this wave.
- Next: owner approval of `SPEC READY` for the refined Spec, then UI refinement (UI impact: YES — chunk-level citation chips, retrieval disclosure, ungrounded state) toward `UI READY`.
- Gates (all 2026-09-03, approved by `YMY / Project Owner` interactively): `SPEC READY: PASS` (spec @ `21794b907af1`; decision log D1–D9: local in-process fastembed + bge-small-zh-v1.5 512-dim, deploy-time idempotent backfill, exclude-with-disclosure, proceed-with-explicit-ungrounded, full live re-baseline at delivery, embedding under upload processing with no new quota, maintainer-judgment D7 k=6/budget 2000 chars + D8 standards stays deterministic, D9 all three generation families retrieve). `UI READY: PASS` (`ux-ui-f014-r1` / `f913f17b7f41`; U1 expandable citation badges with server-delivered excerpts + sources chunk view, U2 per-lesson 无强相关来源语料 notice, U3 shared citation-chip variant, U4 evidence 命中/排除/预算 summary chips, U5 未嵌入 disclosure; no new public endpoints). `TEST DESIGN READY: PASS` (`test-design-f014-r1` / `605e7c1989bb`, TS-001..TS-027, deterministic/live separation, risk-based exclusions recorded) + Plan `plan-f014-r1` @ `d70025a354b9` (T0–T10) approved together; `Roadmap Status: READY` recorded 2026-09-03.
- Next: branch `feature/F014-semantic-source-retrieval`, then `CODING_TESTING` (T0–T10); commit/push/PR and the TS-026 live re-baseline each require separate owner authorization at their time.
- Implementation COMPLETE 2026-09-03 (plan `plan-f014-r1`, T0–T8): new `adapters/embedding.py` (fake + fastembed, ADR-0007), migrations `f014c1e3f5a7` + `f014d5f7b9c2` (vector/HNSW/hashes/embedding status; artifact citations), parse-time embedding with explicit failure states, idempotent deploy-time backfill wired as deploy step 4/5 with weights baked into the image, retrieval service (top-k, budget trim, exclusion disclosure, honest none-state), planning corpus swap + per-item citation retrievals, per-lesson retrieval in all three generation families, server-injected chunk citations everywhere (payload citations stripped), F009 `retrieval_mode` signature, deletion/quota verification, shared citation chip + ungrounded notices + sources chunk view + evidence retrieval rows. Verification: backend 547 passed + 4 skipped + ruff clean (+32 F014 tests); web 113/113 + tsc + lint 0 errors; E2E TS-025 green (`E2E_RETRIEVAL=1`, deterministic stack, keyboard + 420px). Review `review-f014-r1` (SF-1..SF-3, M-1/M-2 residuals owner-visible): no Critical/unfixed-High. Docs synced (README/DATABASE/ARCHITECTURE/API/UX/DESIGN_SYSTEM/TESTING/ADR-0007). `Roadmap Status: REVIEW` recorded 2026-09-03.
- Next: owner-authorized delivery (commit/push/PR; deployed-stack verification incl. the backfill step; TS-026 full live re-baseline per D5), then DONE. T9/T10 delivery actions each require separate explicit authorization.

### Previous: F013 DONE

- Feature: `F013 Teacher Memory`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-09-02 (start instruction after F012 DONE; dependency `F001` DONE).
- Work item: [GitHub Issue #26](https://github.com/MaoyuanYang/LessonCanvas/issues/26) — bound 2026-09-02 (authorized); work-status authority.
- Governing decision: ADR-0005 (workspace-scoped, teacher-confirmed, subordinate context; deleted with the workspace; untrusted input at re-injection; no cross-user or training use).
- Known integration anchors from delivered code: F009 `memory_state_json` pinning (`empty (F013 not implemented)` today) and the `C-MEM-1` criterion must become memory-revision-bound; deletion-completeness sweep (`identity_workspace/deletion.py`) must cover the new memory tables; proposal triggers sit at brief/blueprint confirmation and run completion.
- Next: `SPEC_REFINEMENT` toward `SPEC READY`; resolve DRAFT open questions (preference categories, applicability scope, applied-context display, F009 memory pinning, re-proposal policy) with the owner during refinement.
- Gates (all 2026-09-02, approved by `YMY / Project Owner` interactively): `SPEC READY: PASS` (`75ee61c2cf0b`; decision log D1–D8: fixed four categories, workspace-default applicability with per-project adjust, all three proposal triggers with identity idempotency, content-hash rejection dedupe, deterministic language_mode conflict rule, F009 constructed-empty revision-list pinning, account-section + in-workspace proposal cards + evidence applied-context region, caps 20/300/2500). `UI READY: PASS` (`ux-ui-f013-r1` / `8b39aeebb9a9`; U1–U6 incl. injection budget priority language > exercise > pacing > assessment, most-recent-first within category, whole records, disclosed truncation). `TEST DESIGN READY: PASS` (`test-design-f013-r1` / `c033f186772a`, TS-001..TS-027, recommended risk-based scope with recorded exclusions) + Plan `plan-f013-r1` @ `427356ca088e` (T0–T10, new `teacher_memory` module, one migration, Celery proposal task, four payload injection points) approved together; `Roadmap Status: READY` recorded 2026-09-02.
- Next: branch `feature/F013-teacher-memory`, then `CODING_TESTING` (T0–T10).
- Implementation COMPLETE on `feature/F013-teacher-memory` (T0–T10, plan `plan-f013-r1`): new `teacher_memory` module (records/proposals/passes/overrides + proposal pipeline + effective-set assembly), migration `f013b1d2e3f4`, Celery task `generate_memory_proposals`, brief/blueprint/run-settle triggers, `memory_context` injection into discovery/planning/generation payloads with snapshot-once `memory.applied` trace events, F009 structured revision-list pinning joining the comparability signature, F011 deletion-sweep registration, `MEMORY_LIMIT` error class; web adds `/account` 教师记忆 section, shared proposal region + badge across five host panels, evidence 教师记忆（本项目） region, and the E2E journey. Verification: backend 504 passed + 4 skipped + ruff clean; web 108/108 + tsc clean + eslint 0 errors (3 pre-existing warnings); memory E2E 3/3 behind `E2E_MEM_FAULT=1`. Review `review-f013-r1`: IF-1..IF-5 + M-1 dispositioned, no Critical/unfixed-High; residual TS-026 live proposal-quality pass pending owner authorization. Documentation synced (API/DATABASE/ARCHITECTURE/TESTING/AGENTS module-consumer note). `Roadmap Status: REVIEW` recorded 2026-09-02; delivery pending authorization (commit/push/PR).
- Delivery & DONE: full flow authorized 2026-09-03; TS-026 live DeepSeek proposal-quality evidence executed first (owner-authorized; `specs/F013-teacher-memory/live-evidence.json` — quality proposals with derived values, one real transient-provider best-effort failure, live dedupe honest-empty, journeys purged by account deletion). PR [#27](https://github.com/MaoyuanYang/LessonCanvas/pull/27) merged as `66a0b6c` (commit `8ddae59`; Issue #26 auto-closed); main re-verified (backend 515 passed + 4 skipped + ruff clean; web 108/108 + tsc clean + eslint 0 errors). `DONE: PASS` + `Roadmap Status: DONE` recorded 2026-09-03; evidence manifest in `specs/F013-teacher-memory/spec.md` Gate Record.
- Next actionable: none remaining in the Phase-1 Feature Map (F001–F013 all DONE); follow-up candidates recorded earlier: public cloud/region/internet exposure deployment Feature (F012 D1 residual); Phase-1 close-out review recorded in `specs/PHASE1-retrospective.md` (2026-09-03).

### Previous: F012 NEXT

- Feature: `F012 Deployed Portfolio Proof`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-09-02 (start instruction after F011 DONE; dependencies `F009` DONE and `F011` DONE; F013 P1 unclaimed).
- Owner direction 2026-09-02: local-first full-stack deployment (complete real deployment verified on the local environment first); public exposure / cloud provider selection refined during Spec clarification.
- Work item: [GitHub Issue #24](https://github.com/MaoyuanYang/LessonCanvas/issues/24) — bound 2026-09-02 (authorized); work-status authority.
- Gates: `SPEC READY: PASS` (`8c033df6a4e6`) approved by `YMY / Project Owner` on 2026-09-02 (interactive decisions D1 local full-stack containerization as DONE boundary, D2 LAN access, D3 synthetic sample + self-service bounded generation, D4 checkpointer inclusion; D5-D10 evidence-resolved). `UI READY: PASS` (`ux-ui-f012-r1` / `36d3aa65cfaa`, owner-approved 2026-09-02). `TEST DESIGN READY: PASS` (`test-design-f012-r1` / `36b64b867e42`, TS-001..TS-015, risk-based scope) + Plan `plan-f012-r1` (`c266fd767156`, T0-T11) approved together 2026-09-02; `Roadmap Status: READY` then `IN_PROGRESS` recorded 2026-09-02; branch `feature/F012-deployed-portfolio-proof`.
- Carry-in obligations from F011/F010 records: verify the F011 D10 provider constraint set against the selected deployment topology; re-check the single-process SSE registry assumption (F011 M-2) for the deployed topology; investigate the Postgres LangGraph checkpointer deferred from F001 (B-001 residual); display product validation as passed/failed/not-complete (F010 D9).
- Design Change (L3) 2026-09-02: ADR-0006 removes Clerk — Phase 1 has no login/logout; identity is application-issued anonymous workspace tokens (`POST /auth/guest-token`, per-browser subject; `clerk_user_id` columns renamed `subject`). F012 Gates revalidated (SPEC/UI/TEST DESIGN r2) after D2/D9 revision + D11/D12. E2E becomes fully deterministic (F011 M-1 pattern obsolete).
- Implementation COMPLETE on `feature/F012-deployed-portfolio-proof` (plan `plan-f012-r2`: T0-T11 incl. ADR-0006 identity-removal slices T4b/T4c/T6b). Deployed verification executed 2026-09-02 on the owner machine (LAN 192.168.9.101): deploy chain/migrate/smoke PASS, seed idempotent, live DeepSeek recovery journey TS-029 PASS, deletion completeness all-zero with retained ledger, SSE single-process verified, F011 D10 constraints re-verified, teardown+redeploy+re-seed PASS, accessibility/420px spot PASS. Defects found+fixed in review `review-f012-r3` (IF-8 checkpointer setup deadlock in multi-process topology — entrypoint pre-setup; IF-9 tabs nav 420px overflow; IF-10 image build fixes; IF-11 seed exit). Suites: backend 477+4skip + ruff clean; web 97 + tsc + lint 0 errors; deployed E2E 5/5. Evidence: `specs/F012-deployed-portfolio-proof/deployment-evidence.md`. Awaiting delivery authorization (commit/push/PR).
- Delivery & DONE: full flow authorized 2026-09-02; PR [#25](https://github.com/MaoyuanYang/LessonCanvas/pull/25) merged as `c6c7b53`; main re-verified (backend 477+4skip + ruff; web 97 + tsc + lint 0 errors; deployed LAN stack healthy). `DONE: PASS` + `Roadmap Status: DONE` recorded 2026-09-02; evidence manifest in `specs/F012-deployed-portfolio-proof/spec.md` Gate Record.
- Residuals routed forward: public cloud/region/internet exposure = follow-up deployment Feature (Spec D1); F011 M-1 pattern obsolete (E2E deterministic under ADR-0006); checkpointer B-001 CLOSED (IF-8 fix verified).
- Next actionable: F013 Teacher Memory (P1, unclaimed).

### Previous: F011 DONE

- Feature: `F011 Public Multi-Account Guardrails`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-09-01 (start instruction after F010 DONE; dependency `F009` DONE; F012 waits on F011, F013 P1 unclaimed).
- Work item: [GitHub Issue #22](https://github.com/MaoyuanYang/LessonCanvas/issues/22) — bound 2026-09-01 (authorized); work-status authority; auto-closed on delivery.
- Gates: `SPEC READY: PASS` (`d27deee5bfc8`) approved by `YMY / Project Owner` on 2026-09-01 (interactive question-form confirmation of D2 relaxed limit set — API 240/min general + 120/min expensive writes, 2 concurrent generation runs, 6 SSE streams, 200 MB/day uploads — D3 no-operator-role + account-page disclosure, D4(b) content-free retained security ledger after account deletion, D6 inclusion of the F006 M-2 worker fast-fail; D1/D5/D7–D11 evidence-resolved and confirmed with Spec approval). `UI READY: PASS` (`ux-ui-f011-r1` / `875da011e55e`, owner-ratified 2026-09-01). `TEST DESIGN READY: PASS` (`test-design-f011-r1`, final @ `66c431920e95` incl. execution snapshot, TS-001..TS-019) approved 2026-09-01. Plan `plan-f011-r1` @ `850c40e8e41a` (T0–T12) valid.
- Delivery: implementation T0–T12 complete on `feature/F011-public-multi-account-guardrails`; review recorded (`review.md` @ `216c63239c6e`: IF-1 content_type latent-F001 defect, IF-2 workspace-resolution race, IF-3 unrepairable deletion orphan — all fixed with tests; no unfixed Critical/High; residuals M-1 env-gated E2E, M-2 single-process SSE registry, L-1..L-3 owner-visible). Full delivery flow authorized 2026-09-01: PR [#23](https://github.com/MaoyuanYang/LessonCanvas/pull/23) merged as `42fd778`; `DONE: PASS` + `Roadmap Status: DONE` recorded after main re-verification (backend 454 passed, 1 env-gated skip + ruff clean; web 83/83 + tsc clean). DONE evidence manifest in `specs/F011-public-multi-account-guardrails/spec.md` Gate Record. Security evidence: uv audit 0; pnpm audit 0 via workspace overrides; tracked-tree credential scan clean.
- Next actionable: F012 Deployed Portfolio Proof (P0; F011 DONE completes its dependency; must verify the D10 provider constraint set against selected cloud providers, re-check the SSE single-process assumption for the deployed topology, and display the honest product-validation status) and F013 Teacher Memory (P1).
- Next: bind Issue, then `SPEC_REFINEMENT` toward `SPEC READY`.

### Previous: F010 DONE

- Feature: `F010 Teacher Product Validation`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-09-01 (start instruction after F009 DONE; dependency `F009` DONE).
- Work item: [GitHub Issue #20](https://github.com/MaoyuanYang/LessonCanvas/issues/20) — bound 2026-09-01 (authorized); work-status authority; auto-closed on delivery.
- Gates: `SPEC READY: PASS` (`66a3c94329a9`, D1–D9: five-dimension rubric with 4.0 mean threshold and separate blocking severe-error classes; all three dataset units; controlled structured-evidence import with no new identity surface; publication boundary; staleness rule; status vocabulary/precedence; surface integration; idempotency; real-reviews-before-delivery with honest fallback — approved interactively 2026-09-01). `UI READY: PASS` (`ux-ui-f010-r1` / `35fe2b9b1417`). `TEST DESIGN READY: PASS` (`test-design-f010-r1` / `eaa31cd897d6`, TS-001..TS-015). Plan T0–T6 @ `76fced0843e7` valid; all approved 2026-09-01.
- Delivery: implementation T0–T5 complete on `feature/F010-teacher-product-validation`; review recorded (`review.md`: SF-1 client pre-validation added per approved UX/UI; SF-2 evidence-document orphan-privacy defect fixed with flush-before-store + best-effort cleanup; no Critical findings); TS-013 E2E environment-gated with green substitute coverage and recorded resume condition; TS-014 real-teacher reviews deferred by `YMY / Project Owner` on 2026-09-01 per the D9 honest-fallback branch (runtime truthfully 未评估 until assignments exist; follow-up import appends to the Test Design snapshot). Full delivery flow authorized 2026-09-01: PR [#21](https://github.com/MaoyuanYang/LessonCanvas/pull/21) merged as `683172b`; `DONE: PASS` + `Roadmap Status: DONE` recorded after main re-verification (backend 269 passed + ruff clean + web 74/74 + tsc clean). DONE evidence manifest in `specs/F010-teacher-product-validation/spec.md` Gate Record.
- Next actionable: F011 Public Multi-Account Guardrails (P0; F009 DONE completes its dependency) and F012 Deployed Portfolio Proof (waits on F011; must display the honest product-validation status); F013 Teacher Memory (P1) may also be refined.
- Next: bind Issue, then `SPEC_REFINEMENT` toward `SPEC READY`.

### Previous: F009 DONE

- Feature: `F009 Technical Portfolio Evaluation`
- Selection: `DRAFT -> NEXT` confirmed by `YMY / Project Owner` on 2026-09-01 (start instruction after F008 DONE; dependency `F008` DONE; execution plan approved interactively).
- Direction decisions confirmed by `YMY / Project Owner` on 2026-09-01: self-authored synthetic representative units (licensed, versioned, checksummed in-repo); live-model evidence runs 2-3 passes per unit with per-pass criterion judgment and no cross-pass normalization; technical-evaluation surfaces integrate into the layered evidence experience (summary region + dedicated report view, no new top-level tab).
- Work item: [GitHub Issue #18](https://github.com/MaoyuanYang/LessonCanvas/issues/18) — bound 2026-09-01 (authorized); work-status authority.
- Gates: `SPEC READY: PASS` (`15803bdc1837`) approved by `YMY / Project Owner` on 2026-09-01 (D1 synthetic dataset, D2 blocking/diagnostic split, D3 two live passes per unit without normalization, D6 unit topics selected interactively; D4/D5/D7–D11 evidence-resolved and confirmed with Spec approval). `UI READY: PASS` (`ux-ui-f009-r1` / `d3860c7a8c05`, D-EVALREGION..D-EVALSMALL composing evidence-panel region + print report). `TEST DESIGN READY: PASS` (`test-design-f009-r1` / `5a7fc2df6b13`, TS-001..TS-018 with deterministic/live separation) approved (incl. UI READY confirmation) 2026-09-01. Plan `specs/F009-technical-portfolio-evaluation/plan.md` @ `d12d93ad3b76` (T0–T8) valid; `Roadmap Status: READY` recorded 2026-09-01, then `IN_PROGRESS` at implementation start the same day on `feature/F009-technical-portfolio-evaluation`. Implementation T0–T7 complete on the deterministic stack (backend 221 passed incl. 24 F009 tests + ruff clean; web 63/63 + eslint/tsc/build clean; TS-016 browser journey environment-blocked with substitute coverage); review recorded (SF-1..SF-5; SF-1/SF-2/SF-3 fixed with tests). `Roadmap Status: REVIEW` 2026-09-01. T8 live evidence executed the same day under owner authorization (real DeepSeek): six live passes — cultural-heritage p1/p2 pass, natural-disasters p1/p2 pass, travelling-around p1 pass, travelling-around p2 fail (C-ART-1 slide-deck lesson 3 not downloadable; honest per-pass failure kept explicit) — plus the real-worker stop/restart recovery demonstration (same-run resume, byte-identical preserved checksum, model_calls 2→4). Evidence: `specs/F009-technical-portfolio-evaluation/live-evidence.json`, `worker-recovery-evidence.json`, `live-evidence-summary.txt`. Commit/push/PR authorized 2026-09-01: delivery PR [#19](https://github.com/MaoyuanYang/LessonCanvas/pull/19) merged as `6eed93f` (full delivery flow authorized by `YMY / Project Owner`); `DONE: PASS` + `Roadmap Status: DONE` recorded 2026-09-01 after main re-verification (backend 221 passed + ruff clean; web 63/63 + tsc clean). DONE evidence manifest in `specs/F009-technical-portfolio-evaluation/spec.md` Gate Record.
- Next actionable: F010 Teacher Product Validation (P1) and F011 Public Multi-Account Guardrails (P0) — F009 DONE completes their shared dependency; F012 additionally waits on F011.
- Next: bind Issue, then `SPEC_REFINEMENT` toward `SPEC READY`.

### Previous: F008 DONE

- Feature: `F008 Alignment Review and Delivery`
- Work item: [GitHub Issue #16](https://github.com/MaoyuanYang/LessonCanvas/issues/16) — bound 2026-09-01 (authorized); auto-closed on delivery.
- Gates: `SPEC READY: PASS` (`dc301bba1a83`), `UI READY: PASS` (`ux-ui-f008-r1` / `6bca800ac896`), `TEST DESIGN READY: PASS` (`test-design-f008-r1` / `6d7979391f92`), approved by `YMY / Project Owner` on 2026-09-01 (D1 deterministic-only judgment, D2 missing-not-overridable/disputed-overridable, D3 all-three-families validated package, D4 ZIP + web printable report selected interactively; D5–D8 evidence-resolved). `DONE: PASS` recorded 2026-09-01 after PR [#17](https://github.com/MaoyuanYang/LessonCanvas/pull/17) merged as `1982ac9` (full delivery flow authorized by `YMY / Project Owner`).
- DONE evidence manifest (working tree @ gate time): spec `865244341a9e`, ux-ui `817e9fcfa4a3`, test-design `d9feba15621d`, plan `cd47f7a23a05`, review `f1212fbc6698`, ROADMAP pre-DONE `ad8c1ea0f128`; verification: backend 197 passed (incl. 17 alignment tests) + ruff clean, web 57/57 + eslint/tsc/build clean, E2E fault-stack TS-016/TS-017 green; main re-verified (backend exit-0 + ruff + web 57/57).
- Refinement resolved: D1 deterministic structural judgment (objective→lesson→family coverage incl. F007 retention; zero model calls); D2 gap-class never overridable, disputed conflict-class owner-overridable with required audited reason and withdrawal; D3 validated = every lesson complete+validated across plans/decks/exercises; D4 ZIP of byte-identical artifacts + print-styled web report; D5 derived findings with version-bound overrides; D6 status pair with product validation not-evaluated until F010; D7 synchronous read-side computation; D8 idempotent export per (pair, label, manifest digest) with failed-retry-in-place.
- Review-fixed defect: SF-1 failed export with unchanged manifest could never retry (identity collision) — retried in place with regression test.
- Residuals (owner-visible in test-design snapshot): M-1 scripted-override browser journey environment-blocked (substitute coverage green; resume by re-run under stable environment); M-2 pre-existing `next dev` intermittent client exception (E2E used production build); L-1 print paper output relies on browser engine.
- Next actionable: F009 Technical Portfolio Evaluation (F008 DONE completes its dependency).

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
- `F014` lands first in Phase 2: retrieval quality and chunk-level citations are what make `F016`'s grounded review meaningful, and it converts the existing README/docs pgvector claim into implemented behavior.
- `F016` may additionally consume `F015` tool calling when available (designer/reviewer using standards search); that dependency is soft and must not delay `F016` refinement after `F014`.
- Phase-2 stages multiply per-lesson model calls; per-run caps (F003 contract), quota classification (F011), and evidence-panel cost visibility must change together with the stage set, never after it.
- F009 comparability: retrieval mode (F014), tool mode (F015), and the specialist stage set (F016) each join the pass-comparability signature so mixed-configuration evaluation passes cannot compare silently.

## Roadmap Risks

- `F001` crosses identity, source, Agent, structured-state, streaming, MCP, and UI boundaries. Keep its outcome to one confirmed brief and defer unit planning and artifacts.
- `F003` is the largest early risk because it introduces full-unit long-running execution. It may be refined only into sub-outcomes that still deliver teacher-visible all-lesson value, not infrastructure-only tasks.
- Full trace retention increases deletion and operator-access risk across `F006` and `F011`; public portfolio samples remain synthetic-only.
- Exact providers, official sources, formats, evaluation topics, and rubric details remain Feature-level questions with documented resolution points.
- Product validation has one stable external teacher, so conclusions remain bounded to that evidence and cannot be generalized without new research.
- Embedding dependency (F014): local model weights affect image size and offline deployment; a hosted embedding API would supersede the Phase-1 single-hosted-model constraint and requires an L3 ADR.
- Provider function-calling reliability and variance may destabilize F015; the no-tool path must remain a deterministic fallback, and deterministic/live evaluation stay separate.
- F016 multiplies model cost per lesson; without cap, quota, and evidence updates landing together, it would silently break the cost-honesty contract.
- F009 live evidence was produced under the Phase-1 configuration; after F014/F015/F016 the comparability signature changes and existing live passes must not be presented as comparable with new ones.

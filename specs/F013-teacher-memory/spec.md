# F013: Teacher Memory

- Spec Status: `SPEC READY`
- Roadmap Status: `NEXT`
- Priority: `P1`
- Owner: `YMY / Project Owner` (driving `ZCode feature-dev` session, A-013)
- Work item: [GitHub Issue #26](https://github.com/MaoyuanYang/LessonCanvas/issues/26) — bound 2026-09-02 (authorized); work-status authority
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F001` (DONE; workspace authorization, confirmed briefs, evidence boundary); integration anchors in delivered code: F009 memory pinning placeholder, F011 deletion sweep, F006 evidence panel, ADR-0005 governing decision
- Last Updated: 2026-09-02 (implementation complete; Review recorded in `review.md`)

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-02
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-02 (question-form answers selecting D1 "固定四类", D2 "默认启用可调", D3 "三处全触发", D4 "内容哈希去重", D5 "确定性字段检测", D6 "构造为空+修订清单", D7 "账号分区+工作区提案卡", D8 "更松 (20/300/2500)"; explicit SPEC READY approval; Issue #26 creation separately authorized), scope: F013 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-009, Greenfield lifecycle with OBSERVED baseline inventory retained above, no unresolved conflicts, no Critical Open Question OPEN/DEFERRED — three NON-CRITICAL questions routed to UX/UI and Plan)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F013-teacher-memory/spec.md` @ (this file, final working-tree hash recorded in `STAGE.md` Gate Snapshot)
  - `specs/F001-grounded-confirmed-brief/spec.md` @ `88c8000aa885`
  - `specs/F009-technical-portfolio-evaluation/spec.md` @ `38bff6656785`
  - `specs/F011-public-multi-account-guardrails/spec.md` @ `e4425d0a2556`
  - `AGENTS.md` @ `ecde9412a7df`
  - `specs/ROADMAP.md` @ `f0c0469f4413`
  - `docs/ADR/0005` @ `1db4a620df31`
  - `docs/ADR/0006` @ `10182dad72b0`
  - `docs/API.md` @ `95c765ac5baa`
  - `docs/DATABASE.md` @ `b815be594c9e`
  - `docs/ARCHITECTURE.md` @ `59ed50d523e3`
  - `docs/TESTING.md` @ `64f6af3824c2`
  - `docs/UX.md` @ `bce8aecf872f`

## Baseline Evidence (Preflight Inventory, 2026-09-02)

All items are `OBSERVED` from code, tests, docs, and Specs at `main @ 505232e` unless labeled otherwise.

- ADR-0005 (`Accepted`) governs memory: workspace-scoped, Agent-proposed plus teacher-confirmed, subordinate context, untrusted at re-injection, deleted with workspace, never cross-user or training use.
- Identity is application-issued anonymous workspace tokens (ADR-0006): one subject string keys every workspace, ownership, quota, and audit decision; a workspace-scoped memory surface needs no new identity mechanism.
- F009 already pins a memory-state snapshot per evaluation pass: `TechnicalEvaluation.memory_state_json` holds the placeholder `{"memory_state": "empty (F013 not implemented)"}`, checked by blocking criterion `C-MEM-1` ("Memory pinning recorded") via `evaluate_memory_pinning()`; evaluation workspaces are created and driven entirely by the harness.
- Deletion completeness (F011) sweeps an explicit project/workspace table list (`identity_workspace/deletion.py`) with residual verification; a new memory table family must register there and in the truncation test fixture.
- Untrusted-content injection pattern exists: source corpus and metadata travel as labeled keys inside JSON-encoded user payloads (e.g. `corpus_excerpt`), system prompts mandate JSON-only output, and adversarial corpus tests prove injected instructions stay inert inside serialized payloads.
- Layered evidence (F006) renders per-run summaries and merged trace/run event streams; the panel is the natural surface for an applied-memory section.
- The web app has an account area (`/account`: usage, audit, deletion) and a ten-tab workspace view with inline zh-Hans copy; no memory surface exists anywhere yet.
- Proposal trigger points exist as synchronous service functions: `confirm_brief`, `confirm_blueprint`, and generation run settlement in the artifact graphs.

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | First preference categories | Fixed four-category enum: `language_mode` (Chinese/English/bilingual output tendency), `exercise_format` (exercise types, difficulty and pairing habits), `pacing_structure` (lesson rhythm, unit pacing, structural habits), `assessment_style` (assessment and homework style). Every record is category + short free text (length capped per D8) + evidence references. No free-form uncategorized records in Phase 1; new categories require a Spec change. | `YMY / Project Owner`, 2026-09-02 (interactive, "固定四类") |
| D2 | Default applicability scope | Workspace-wide default ON: confirmed records apply as subordinate context to new discovery/planning/generation work in every project of the workspace; each project can view the effective set and disable individual records for that project only (default enabled). No per-project opt-in gate. | `YMY / Project Owner`, 2026-09-02 (interactive, "默认启用可调") |
| D3 | Proposal generation triggers and cost boundary | All three trigger points: brief confirmation, blueprint confirmation, and generation run settlement each start one bounded proposal pass (one model call, at most 3 candidate proposals). A pass is skipped when its trigger evidence identity (workspace, trigger kind, brief/blueprint version or run id) already had a pass — retries and duplicate settle events never re-bill. Proposal generation is asynchronous and best-effort: failure never blocks or fails the confirmation/run flow. | `YMY / Project Owner`, 2026-09-02 (interactive, "三处全触发") |
| D4 | Re-proposal policy after rejection | Content-hash dedupe: a candidate whose (category, normalized-content hash) equals an already rejected proposal is never re-proposed; at most one pending proposal per category (a newer distinct candidate supersedes the pending one without rejection penalty); re-proposal happens only when new confirmed evidence produces different normalized content (evidence-driven, no time cooldown). | `YMY / Project Owner`, 2026-09-02 (interactive, "内容哈希去重") |
| D5 | Conflict with confirmed intent | Deterministic field-level detection only, where a category maps onto a structured confirmed field (Phase 1: `language_mode` vs the bound brief's language field): the conflicting record is not injected for that run, the confirmed version wins by construction, and the conflict is recorded in the run's applied-memory trace event and shown as a teacher-visible notice in the applied-context area. Non-structured content is subordinate by construction (labeled data payload, never an authoritative input). No new human interruption point is added. | `YMY / Project Owner`, 2026-09-02 (interactive, "确定性字段检测") |
| D6 | F009 comparability pinning | Evaluation workspaces remain empty by construction (the harness never confirms memory proposals); `memory_state_json` upgrades from the placeholder string to a structured snapshot binding the applied memory-set revision list (empty list for evaluations); the `C-MEM-1` criterion keeps requiring a recorded pinning snapshot; the pass-comparability signature includes the memory set so future memory-bearing comparisons cannot mix silently. | `YMY / Project Owner`, 2026-09-02 (interactive, "构造为空+修订清单") |
| D7 | Management and proposal UI layout | Memory management lives in the account area (new teacher-memory section in `/account`); proposals surface in-workspace as explicit proposal cards in the relevant panels (after brief/blueprint confirmation and after run settlement) with a navigation badge; applied context renders as a new section of the run evidence panel. | `YMY / Project Owner`, 2026-09-02 (interactive, "账号分区+工作区提案卡") |
| D8 | Quantitative caps | Confirmed records at most 20 per workspace; record content at most 300 characters; total injected memory context at most 2500 characters per run/pass; at most 1 pending proposal per category (4 total across the four categories); all caps validated server-side with explicit quota errors; proposal model passes run under the existing expensive-write rate limit and are audited with estimated cost. | `YMY / Project Owner`, 2026-09-02 (interactive, "更松 (20/300/2500)") |

## Goal

Let a teacher keep workspace-scoped, teacher-confirmed preference memory — proposed by the Agent from confirmed briefs, blueprints, and completed runs — that personalizes future preparation as visible, subordinate context without ever overriding confirmed intent.

## Business Value

Repeat unit preparation starts closer to the teacher's established style, and the project demonstrates governed Agent memory — bounded proposal, explicit confirmation, audited application, honest conflict handling, and complete deletion — which most Agent demos omit.

## User Story

As a senior-high English teacher, I want the system to propose remembering preferences I confirmed in earlier work and let me manage them, so that future units start from my style without me re-explaining it — and so that what is remembered never overrides what I have confirmed for the current unit.

## Scope

- Memory proposal passes triggered by brief confirmation, blueprint confirmation, and generation run settlement (D3), one bounded model call each, at most 3 candidates, deduplicated per D4.
- Teacher decision surfaces: confirm (with optional edit), reject, and retry-failed-generation for proposals; proposals stay visibly distinct from confirmed records and have no effect until confirmed.
- Confirmed-record management in the account area: view (with evidence references and applied-context counts), edit, delete; workspace-owner-only (D7).
- Subordinate application as labeled, capped context to discovery, planning, and artifact generation in all workspace projects by default, with per-project per-record disable overrides (D2).
- Deterministic `language_mode` conflict detection with confirmed-version-wins behavior and teacher-visible conflict notices (D5).
- Applied-memory trace events and an applied-context section in the layered evidence panel, including skipped-for-conflict records (D5, D7).
- Memory-set revision snapshot bound into F009 evaluation pinning (`memory_state_json`, `C-MEM-1`) (D6).
- Memory tables, per-project overrides, and proposals registered in F011 deletion-completeness sweeps and workspace cascade; audited memory actions with estimated pass cost (D8).
- Untrusted-input handling for memory content at re-injection, mirroring the source-corpus injection defenses and adversarial test patterns.

## Out of Scope

- Implicit auto-extraction without teacher confirmation (ADR-0005; revisit trigger unchanged).
- Cross-user memory, shared preference corpora, training use, or memory-based analytics beyond the owning workspace.
- Memory overriding, rewriting, or invalidating a confirmed brief/blueprint version; memory-driven regeneration triggers; any second workflow authority.
- Student data, learning profiles, or grade-linked personalization (rejected data classes unchanged).
- New preference categories beyond the four of D1 (requires a Spec change).
- Time-based re-proposal cooldowns, semantic similarity matching, or embedding-based memory retrieval.
- A memory import/export feature, and per-record history/versioning beyond the audit trail.
- Changes to identity, run/version contracts, quotas of other surfaces, or the deployed topology.

## Actors / Preconditions

- Actors: the workspace owner (teacher) — the only actor for every memory operation; the Agent — proposes bounded candidates from confirmed evidence; the F009 harness — an automated consumer that pins (empty) memory state.
- Preconditions: F001–F012 behavior present at `main`; the workspace exists (subject token per ADR-0006); proposals exist only after at least one trigger event (a confirmed brief/blueprint version or a settled generation run).

## Main Flow

1. A trigger event occurs (brief confirmed, blueprint confirmed, or generation run settled); an asynchronous proposal pass runs one bounded model call over that confirmed evidence and produces at most 3 category-labeled candidates with evidence references (D1, D3).
2. Candidates are validated (category enum, length cap) and deduplicated against confirmed records, pending proposals, and rejected proposals; survivors become pending proposals, at most one per category, superseding an older pending proposal of the same category when distinct (D4, D8).
3. The teacher sees proposal cards in the relevant workspace panel (and a navigation badge); confirming — optionally after editing the text — persists a confirmed workspace-scoped record; rejecting records the rejection for permanent identical-form dedupe (D4, D7).
4. Later discovery/planning/generation work in any workspace project assembles the effective memory set (active records minus project-disabled, minus deterministic conflicts, capped at the injection budget) and injects it as a labeled data payload; the applied set, skipped conflicts, and injection size are recorded in a `memory.applied` trace event and shown in the evidence panel's applied-context section (D2, D5, D7, D8).
5. The teacher manages records any time in the account area: edit, disable per project, or delete; deletion hard-deletes the record and stops every future application immediately.

## Alternative Flows

- Proposal pass fails (provider/transient): the pass is visibly `failed` with a retry action in the proposal surface; the triggering confirmation/run flow is unaffected; retry is idempotent per trigger evidence identity and never re-bills a completed pass (D3).
- Proposal pass yields no surviving candidates: the surface honestly shows "no new proposals" (empty result), not a fabricated proposal.
- Invalid model output (unknown category, over-length content, malformed JSON): invalid candidates are dropped as untrusted output; the pass completes with the valid subset (possibly none).
- Confirmed-record cap reached on confirm: explicit `MEMORY_LIMIT` quota error with a management link; the proposal stays pending (teacher may delete a record first, then confirm).
- `language_mode` conflict at application time: the conflicting record is skipped for that run, the confirmed version's field wins, and the conflict appears in the applied-context section and record management (D5).
- Per-project disable: the record stops applying in that project's future runs only; other projects are unaffected; already-recorded applied contexts remain as history (D2).
- Record deleted while a run is in flight: the run keeps its already-assembled snapshot (it is historical trace data inside the project boundary); no new run applies the record (deletion rule below).
- Workspace/project deletion: memory tables and overrides are swept with the existing F011 cascades and completeness verification (Scope; D8 audit).

## Business Rules / Invariants

- Only teacher-confirmed records persist as memory; proposals are drafts with no effect on any run; rejected and superseded proposals are not memory (ADR-0005; D4).
- Memory is subordinate context: it never overrides, rewrites, or invalidates a confirmed brief/blueprint version; on conflict the confirmed version wins and the conflict surfaces (ADR-0005; D5).
- Memory is workspace-scoped, never shared across users, never used for training, and deleted with the project or account (ADR-0005).
- Memory content is untrusted input at re-injection: labeled data payload inside the JSON user message, length-capped, never phrased as instructions, covered by injection defenses and adversarial tests (AGENTS; D8).
- Applied memory context is recorded in the run trace so its influence is inspectable (ADR-0005; D5).
- Record deletion hard-deletes the record, its per-project overrides, and pending proposals referencing it; no new run applies it. Immutable historical run traces (including the applied-memory payload already injected, per ADR-0003 complete-trace ownership) remain inside the owning project and are removed with project deletion — never republished or reused.
- Every memory action (pass execution, confirm, reject, edit, delete, override change) writes an audit event in the owning workspace; proposal passes record estimated model cost; audit records never contain memory text content.
- Rejected proposals are never re-proposed in identical (category, normalized-content) form; superseded proposals carry no dedupe penalty (D4).
- Memory never becomes a Source of Truth: prompts, model responses, and memory text cannot grant tools, change system policy, or bypass authorization.

## State Transitions

- Proposal: `pending -> confirmed | rejected | superseded | deleted-with-record`; invalid transition (e.g. deciding a superseded proposal) is rejected with an explicit stale error.
- Proposal pass (per trigger evidence identity): `scheduled -> running -> completed | failed`; `failed -> running` only via the explicit retry action; a completed pass never re-runs for the same identity.
- Confirmed record: `active -> edited (still active) | deleted` (hard delete; no soft states).
- Per-record project applicability: `enabled (default) <-> disabled`.

## Data Changes

- New workspace-scoped tables owned by the Teacher Memory module: confirmed records (category enum, capped content, evidence references to brief/blueprint version or generation run, normalized content hash), pending/rejected/superseded proposals (same shape plus decision timestamps), and project-scoped applicability overrides. Exact columns and indexes are Implementation Plan territory; the Spec fixes the semantics above.
- `TechnicalEvaluation.memory_state_json` upgrades from the placeholder string to a structured revision-list snapshot (D6); existing rows render as the legacy empty state.
- F011 deletion sweep registration for all new tables (project cascade removes that project's overrides; workspace cascade removes all memory rows); completeness-verification table lists extended.
- No changes to brief/blueprint/run tables; memory only reads confirmed evidence and writes its own tables plus trace events.

## API Behavior

- Workspace memory management (owner-authorized): list records and proposals with statuses, evidence references, and pass states; confirm a proposal (optional edited text); reject a proposal; retry a failed pass; edit a record; delete a record.
- Project memory view: effective record set for the project (applied list, disabled list, known conflicts) and per-record enable/disable override.
- Existing confirmation and run surfaces are unchanged externally except for the asynchronous side effect of scheduled proposal passes.
- Applied context is exposed through the existing run evidence surfaces (summary section plus trace events), not a new parallel authority.
- Error semantics: explicit `MEMORY_LIMIT` quota error on cap violation; stale-state errors on deciding superseded proposals or editing deleted records; standard authorization semantics (workspace owner only); pass failures surface as retryable states, never as confirmation-flow failures.

## Error Cases

- Provider failure during a proposal pass: visible failed state with bounded retry (idempotent per trigger identity); no impact on the confirmed version or settled run that triggered it.
- Malicious memory content (injection attempt inside confirmed text): inert at re-injection — stays a labeled data value inside the payload, cannot alter system prompts, tool availability, authorization, or output schemas; proven by adversarial tests.
- Concurrent confirmations of the same proposal: first decision wins; later attempts get an explicit stale/proposal-already-decided error.
- Concurrent record creation racing the cap: unique (workspace, category, content-hash) record identity plus a workspace-count check; losers receive `MEMORY_LIMIT`, never a duplicate record.
- Cap-exceeding edit: rejected server-side with the same quota error; the previous content stays intact.

## Idempotency / Concurrency / Transaction / Consistency

- One proposal pass per trigger evidence identity; retries and duplicate settle events reuse the pass, never re-billing a completed one (D3; AGENTS retry rule).
- Proposal decision, record edit, record delete, and override changes are idempotent by resource state with explicit stale errors on concurrent conflicting operations.
- Record identity uniqueness (workspace, category, normalized content hash) prevents duplicate confirmed records; the pending-slot rule (one per category) is enforced transactionally on insert/supersede.
- Effective-set assembly happens at run/pass start inside the owning transaction and is snapshotted into the trace event; later memory changes never mutate an in-flight run's applied context (stale output never overwrites newer memory state and vice versa).
- Strong consistency for owner checks and cap enforcement follows the existing PostgreSQL patterns.

## Security / Privacy / Authorization

- Every memory operation requires the workspace owner (subject token); no cross-workspace read, proposal, or application path exists; the sample/demo workspace's memory state follows the same isolation.
- Memory text, proposal text, and evidence references never enter audit logs, generic infrastructure logs, evaluation corpora, or training data; they live only in the owning workspace's memory tables and its projects' run traces (ADR-0003 boundary).
- Memory content is screened by the same untrusted-input rules as sources at re-injection; deterministic validation on category and length before persistence.
- Deletion: record deletion and workspace/project deletion remove governed memory copies per the invariants; completeness verified by the extended F011 sweep.

## Non-functional

- Cost: proposal passes are bounded (one call per trigger identity, at most 3 candidates) and audited with estimated cost; injection adds at most 2500 characters per run payload (D3, D8).
- Performance: effective-set assembly is a bounded workspace query at run start; no retrieval infrastructure added.
- Observability: `memory.applied` trace events, pass audit events, and the evidence-panel section make memory influence inspectable end to end.

## Acceptance Criteria

- `AC-001` Given a confirmed brief version, confirmed blueprint version, or settled generation run, when the proposal pass completes, then at most 3 validated, deduplicated pending proposals appear in the workspace proposal surface with category labels and evidence references — or an honest empty result — and the triggering flow is never blocked or failed by the pass.
- `AC-002` Given a confirmed memory record, when later discovery, planning, or generation work starts in a workspace project, then the run visibly applies it as subordinate context: the injected payload, applied record list, and injection size are recorded in a `memory.applied` trace event and rendered in the evidence panel's applied-context section.
- `AC-003` Given a confirmed `language_mode` record conflicting with the bound brief's language field, when a run starts, then the record is not injected, the confirmed version's field wins, and the conflict is recorded in the trace event and shown to the teacher in the applied-context section.
- `AC-004` Given a deleted memory record or a deleted workspace, when deletion completes, then no new run applies that memory, per-project overrides and pending proposals are removed, and the F011 completeness verification reports zero governed memory rows (immutable historical in-project traces excepted, removed with the project).
- `AC-005` Given an unconfirmed proposal or a rejected proposal, when any run executes, then it has no effect on the run; and a candidate identical in (category, normalized content) to a rejected proposal is never re-proposed, while a genuinely different candidate from new evidence may be.
- `AC-006` Given memory content containing injection instructions, when it is re-injected into any run, then it remains inert serialized data: it cannot grant tools, change policy or system prompts, alter output schemas, or cross workspace boundaries — proven by adversarial tests mirroring the source-injection corpus.
- `AC-007` Given a record disabled for one project, when runs start in that project versus other workspace projects, then the record is excluded only in the disabled project's applied context, and the disable/enable action is audited.
- `AC-008` Given an F009 evaluation pass, when it is created, then its `memory_state_json` binds the applied memory-set revision snapshot (empty by construction for harness workspaces), `C-MEM-1` requires that snapshot, and pass comparability includes the memory set.
- `AC-009` Given the caps of D8, when a teacher confirms beyond 20 records, edits beyond 300 characters, or a run's effective set exceeds 2500 injected characters, then the server rejects with explicit quota/limit errors, the surface shows the honest state, and the truncation/priority rule (deterministic order, never silent) governs what applies.

## Open Questions

- [ ] `NON-CRITICAL` Exact proposal-card placement and badge behavior per panel — resolved in the UX/UI artifact (D7 direction fixed). Owner: UX/UI refinement. Status: `OPEN`.
- [ ] `NON-CRITICAL` Injection priority order when the effective set exceeds the 2500-character budget (e.g., oldest-first, most-recently-confirmed-first, or category priority) — reversible implementation choice to be fixed in the UX/UI/Test Design artifacts together with its visible truncation disclosure. Owner: UX/UI refinement. Status: `OPEN`.
- [ ] `NON-CRITICAL` Whether proposal passes reuse the worker's existing model-call accounting surface or a dedicated audit cost field — Implementation Plan choice, observable contract fixed (audited estimated cost). Status: `OPEN`.

All Critical questions from the DRAFT Spec are resolved in the Decision Log (D1–D8); none remain `OPEN` or `DEFERRED`.

## Deliberately Deferred Detail

- DTO shapes, table columns, indexes, and migration layout (Implementation Plan).
- Component decomposition and pixel-level UI (UX/UI artifact and Design System reuse).
- Complete Test Design (separate artifact).
- Any second deterministic conflict-mapped category beyond `language_mode` (future Spec change; D5 mechanism is extensible).

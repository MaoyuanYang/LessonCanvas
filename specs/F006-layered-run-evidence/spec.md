# F006: Layered Run Evidence

- Spec Status: `SPEC READY`
- Roadmap Status: `REVIEW`
- Priority: `P0`
- Owner: Implementation assignee unassigned until Coding starts
- Work item: [GitHub Issue #12](https://github.com/MaoyuanYang/LessonCanvas/issues/12)
- Decision Authority: `YMY / Project Owner`
- Dependencies: `F003`, `F004`, `F005` (all DONE) for the complete artifact-family run, trace-capture, and recovery contracts that this Feature makes inspectable
- Last Updated: 2026-08-31

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-08-31
- Decision Authority: `YMY / Project Owner` — approved via interactive session (cost-evidence and run-coverage decisions D2/D3 selected interactively 2026-08-31; D1/D4–D9 confirmed with Spec approval), scope: F006 Spec at the revision below
- Checklist: 11/11 YES (Goal/Scope, Flows, Rules/States, Data/API, Errors/Security, Idempotency/Concurrency, Dependencies/Migration/Non-functional, unique ACs AC-001..AC-015, Greenfield N/A for AS-IS row, no unresolved conflicts, no Critical Open Question)
- Input manifest (working-tree SHA-256 prefixes):
  - `specs/F006-layered-run-evidence/spec.md` @ `b43922d2cc17`
  - `specs/F003-recoverable-unit-lesson-plans/spec.md` @ `77cac3f8a2c1`
  - `specs/F004-editable-lesson-slide-decks/spec.md` @ `9011ff986157`
  - `specs/F005-lesson-exercises-and-answers/spec.md` @ `807f4c857bf8`
  - `AGENTS.md` @ `b03a2200602b`
  - `specs/ROADMAP.md` @ `9b129ae5d524`
  - `docs/API.md` @ `4754312ca25d`
  - `docs/DATABASE.md` @ `d52f92251bcf`
  - `docs/ARCHITECTURE.md` @ `a3118a75d52b`
  - `docs/PRODUCT.md` @ `2ec972e941fc`
  - `docs/adr/0002-stateful-agent-and-async-execution.md` @ `5145b0ff319f`
  - `docs/adr/0003-user-owned-complete-run-traces.md` @ `d0e2fcd0c587`
  - `docs/adr/0004-mcp-tool-and-source-protocol.md` @ `7b4a56764d3f`

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Evidence layering contract | Two disclosure layers over one owner-authorized API. Layer 1 (teacher summary, default): plain-language "what happened and what can I do" — run kind, bound intent versions, authoritative status, lesson/artifact scope with per-lesson outcomes, failure and recovery pointers, model-call usage vs cap, aggregate estimated cost and model latency, available evidence categories, explicit telemetry-gap notices. Layer 2 (technical expansion, owner-initiated): the run's complete technical event stream — specialist model calls (prompt payload and parsed response), tool calls with outcomes, failures, retries, and checkpoint events — cursor-paginated, expandable row by row. Raw prompt/response text is never the default view but is owner-expandable and copyable within D6 safety rules. | `YMY / Project Owner`, 2026-08-31 (confirmed with Spec approval; follows UX.md "reveal technical depth progressively" and the DRAFT out-of-scope "no default raw-prompt view") |
| D2 | Cost evidence | The model adapter's already-returned token usage is persisted per trace event (prompt and completion tokens). Estimated USD cost is computed at write time from a settings-owned price table (per-token prices, defaulting to the selected provider's published prices at implementation time) and stored on the event. Every cost figure is labeled an estimate (估算) in the UI and is never presented as provider-billed truth. Events recorded before this Feature have no token/cost data and display an explicit 未记录 (not recorded) marker. | `YMY / Project Owner`, 2026-08-31 (interactive selection: estimated USD cost) |
| D3 | Run coverage | The evidence view covers all five run kinds: discovery, planning, lesson-plan generation, slide-deck generation, exercise generation. Discovery and planning runs aggregate their interview rounds (teacher questions/answers and agent narration) plus their specialist/tool trace events; generation runs aggregate their per-lesson artifact outcomes, run events, and trace events. One shared layered structure; no run kind is left unexplained. | `YMY / Project Owner`, 2026-08-31 (interactive selection: all five run kinds) |
| D4 | API shape and legacy endpoint | Owner-authorized read APIs under `/projects/{id}/evidence`: a run inventory for the project, a layered summary per run, and a cursor-paginated technical-event list per run (event payloads included; the UI owns progressive rendering). Explanation narration uses the established SSE pattern. The pre-existing metadata-only `GET /projects/{id}/trace` endpoint (never consumed by the Web application, never documented as a project contract in `docs/API.md`) is removed and replaced by the layered evidence API. | Engineering; confirmed with Spec approval |
| D5 | Read-only guarantee | Every evidence interaction is a safe read. The only work the evidence view may trigger is explanation narration (D8), which records its own trace event and quota usage and changes no run, artifact, version, or validation state. Retry, resume, supersession, confirmation, and finding-resolution actions stay in their owning surfaces; the evidence view links to recovery paths but never performs them. | Inherited from DRAFT Out of Scope; confirmed with Spec approval |
| D6 | Safe display and copy | Prompts, source-derived text, model outputs, filenames, and metadata are untrusted text: rendered inert (escaped, no HTML/script interpretation), never persisted outside server-side workspace storage (no browser localStorage/sessionStorage), copyable to clipboard for the owner only, and never leaked through error messages. React's default text rendering satisfies inertness; no markdown/HTML rendering of trace content. | Engineering; confirmed with Spec approval |
| D7 | Pagination and progressive loading | Technical events use stable cursor pagination (cursor = event id, bounded page size, settings-configurable default and maximum). The summary loads first; event pages load on demand with explicit loading state. Run inventory is cursor-paginated per `docs/API.md`. | Engineering; confirmed with Spec approval |
| D8 | Explanation narration | The owner may request a streamed, teacher-readable explanation of one run's findings (status, failures and reasons, validation outcomes, telemetry summary). It reuses the established narration pattern (SSE with stop, complete text recorded in the workspace trace) and reserves against the workspace-level quota counters rather than any per-run cap, because evidence narration may target already-settled runs. | Engineering; confirmed with Spec approval |
| D9 | Telemetry model-config evidence and operator access | From this Feature onward, each trace event records the model adapter kind and model identifier alongside tokens/latency/cost; legacy events display the gap explicitly. No operator access path is added in Phase 1: the evidence view is owner-only, and any future operator troubleshooting access remains governed by ADR-0003's disclosed/audited rule and is owned by F011. | Engineering; confirmed with Spec approval |

## Goal

Let a teacher understand why any recorded run produced its current outcome, and let an authorized portfolio reviewer inspect that run's complete technical evidence, through layered progressive disclosure that keeps the default teacher experience a teaching tool rather than a developer console.

## Business Value

Layered evidence turns already-captured telemetry (sources, specialist steps, prompts and outputs, tool calls, model configuration, cost, latency, failures, retries, checkpoints, and current-stage validation outcomes) into credible, inspectable portfolio evidence without re-architecting the run lifecycle or weakening privacy boundaries.

## User Story

As a teacher or authorized reviewer, I want to move from a plain-language run explanation into detailed technical evidence for exactly the run and version I am looking at, so that I can understand the result at the depth relevant to me and trust what produced it.

## Scope

- Present a teacher-readable summary for every recorded run of the project's five run kinds (D3): what was requested, which confirmed versions it bound to, what happened, what failed and why, what recovered, and what it cost in estimated terms.
- Let the workspace owner expand the technical evidence of their runs: specialist model calls with prompt payloads and parsed responses, tool calls with outcomes, model configuration, token usage, estimated cost, latency, failures, retries, and checkpoint events.
- Stream an owner-requested teacher-readable explanation of a run's findings over SSE, recording the complete explanation in the workspace trace (D8).
- Bind every displayed detail to the authoritative project, immutable intent version, run, and (for generation runs) lesson/artifact scope.
- Disclose missing or incomplete telemetry explicitly without hiding or inferring the authoritative run outcome.
- Treat all displayed trace content as untrusted input with inert display and owner-only copy (D6).
- Resolve the residuals routed to this Feature by prior deliveries: the F003 SSE early-drop root cause investigation, the F004 M-2 StaleDataError run-teardown semantics investigation, and the STAGE B-001 keyboard manual pass over the touched UI.

## Out of Scope

- Cross-user analytics, a shared trace corpus, or use of teacher content for training.
- A default raw-prompt view; raw text is owner-initiated expansion only (D1).
- A general infrastructure observability console, operator role access, or unrestricted operator visibility into teacher workspaces (F011 owns system-wide operator verification).
- Changing business state, retrying work, or resolving findings from the evidence view (D5).
- Answer-correctness, language-quality, and cross-artifact alignment evaluation (F008/F009 own evaluation; this Feature only surfaces the validation evidence that exists at this stage).
- Re-publishing private traces as portfolio samples; synthetic samples belong to F009.
- Redesigning the run lifecycle, event log, or trace capture established by F001–F005.

## Actors / Preconditions

- Actor: the authenticated workspace owner (teacher). Portfolio reviewers access only via the owner's authorized workspace in Phase 1; there is no separate reviewer role.
- Preconditions: a project exists with at least one recorded run of any kind; the requester is the recorded workspace owner. Runs with incomplete or legacy telemetry remain inspectable with explicit gaps.

## Main Flow

1. The owner opens the evidence view from the unit workspace and sees the project's run inventory (kind, status, bound versions, recency, estimated cost) — or an explicit empty state when no run exists yet.
2. The owner selects a run and first receives the teacher-readable summary: bound versions, authoritative status, lesson/artifact scope, failures with reasons and recovery pointers, model-call usage vs cap, aggregate estimated cost and latency, and any telemetry-gap notices.
3. The owner expands technical evidence: the run's complete event stream loads page by page; each row discloses event kind, lesson scope where applicable, latency, tokens, estimated cost, and model configuration, and expands to full prompt/response text on demand.
4. Optionally the owner requests a streamed explanation of the run's findings and may stop the stream; the complete explanation is recorded in the trace.
5. The owner returns to the teaching task without losing version or decision context; nothing about the run changed.

## Alternative Flows

- No run recorded yet: empty state explains why the area is empty and names the first workflow action that produces a run.
- Run active (queued/generating/validating): summary shows live status and progress scope; technical evidence shows events recorded so far; no projection of final outcome.
- Missing telemetry segment (legacy events without tokens/cost/model config, or a narration gap): the gap is explicit at the row and summary level; authoritative status stays sourced from run tables, never inferred from trace completeness.
- Partial-failure or capped run: summary names failed scope with reasons and links the recovery path that lives in the owning generation panel; the evidence view itself offers no retry action (D5).
- Superseded run: clearly marked with the newer version identified; its evidence remains inspectable as history and never appears current.
- Evidence narration provider failure or stream drop: an explicit error class is shown; the run's recorded evidence is unaffected; retrying narration is a new owner action, not an automatic loop.
- Another teacher or unauthenticated request: authorization-denied class response without disclosing that the resource exists.
- Large trace: pagination proceeds by stable cursor; explicit loading state between pages; no unbounded fetch.

## Business Rules / Invariants

- The evidence view is a derived projection: PostgreSQL run/artifact/event/trace tables remain the only truth; evidence reads never mutate business state (D5).
- Every evidence response is authorized by recorded workspace ownership; no cross-workspace content or existence disclosure.
- Complete traces belong to the teacher workspace, follow source/artifact authorization and deletion, and are never reused across users or for training (ADR-0003).
- Teacher-readable state remains authoritative even when a low-level trace element is unavailable; the gap is explicit (D9).
- Technical details may explain a teacher decision but cannot replace confirmation, override, or validation rules.
- Raw prompt, source-derived, and output content is untrusted input: inert display, no execution, no policy or authorization effect (D6).
- Estimated cost figures are derived from a settings price table and are always labeled estimates; absence of token data is shown as not recorded, never as zero cost (D2).
- The removed legacy trace endpoint must not leave a second, weaker authorization path to trace metadata (D4).

## State Transitions

No new business states. Evidence-related UI states: `no run`, `inventory loading`, `summary loading`, `events loading (page)`, `available summary`, `expanded detail`, `missing telemetry (explicit)`, `narration streaming`, `narration failed`, `stale/superseded evidence (marked)`, `permission denied`, `large-trace paging`. All are presentation states over authoritative run status.

## Data Changes

- `trace_events` gains nullable evidence columns — prompt tokens, completion tokens, and model identifier — populated for events recorded from this Feature onward; the existing `cost_usd` column carries the write-time estimate from the price table; legacy rows keep null values and display as not recorded.
- The `TraceEvent` ORM declaration is aligned with the already-applied migration that freed `run_id` from the `discovery_runs` foreign key (no further database change for that alignment).
- Explanation narration records a trace event against the narrated run following the existing `model.narration` pattern.
- No new table, service, cache, or queue; deletion cascades already covering runs/events/traces are verified by test rather than redesigned.
- Exact column names, indexes, and migration strategy are finalized by the Implementation Plan.

## API Behavior

- `GET /projects/{id}/evidence` — cursor-paginated inventory of the project's runs across all five kinds with summary metrics (kind, status, bound versions where applicable, artifact counts, model-call usage, aggregate estimated cost, recency).
- `GET /projects/{id}/evidence/{run_id}` — layered teacher summary for one run (Layer 1): authoritative status, bound versions, scope outcomes, failure reasons and recovery pointers, aggregate metrics, evidence-category availability, and explicit telemetry-gap notices.
- `GET /projects/{id}/evidence/{run_id}/events` — cursor-paginated technical event list (Layer 2) with full payloads; optional event-type filter; bounded page size.
- `POST /projects/{id}/evidence/{run_id}/narrate` — start an owner-authorized explanation stream for the run's current findings; workspace-quota guarded; idempotent per active narration (one active narration per run per workspace).
- `GET /projects/{id}/evidence/{run_id}/narrate/stream` — SSE token stream with stop semantics matching the established narration pattern; the complete text is recorded in the workspace trace.
- Removed: `GET /projects/{id}/trace` (metadata-only legacy endpoint with no consumer; D4).
- Error semantics follow the project taxonomy; authorization failures do not confirm existence; no prompt, storage path, or provider secret ever appears in an error.

## Error Cases

- Unauthenticated or non-owner request: authorization-denied class without resource-existence disclosure.
- Unknown run id inside an owned project: not-found class without cross-workspace probing.
- Narration quota exhausted: explicit quota class naming the boundary and recovery (wait or reduce usage); the recorded evidence stays fully readable.
- Narration provider failure or client disconnect mid-stream: explicit provider class with retry as an owner action; run evidence unaffected.
- Malformed pagination cursor: input-validation error; no data returned.
- Backend aggregation errors: unexpected-system class with correlation reference; no partial trace content leak.

## Idempotency / Concurrency / Transactions

- All evidence reads are safe, read-only queries; concurrent run activity may append events between pages, and cursor pagination returns each event exactly once per traversal.
- Narration start is idempotent per run while a narration is active; stop and disconnect never mutate run state.
- Evidence reads never take locks that block Worker writes; snapshot consistency is per-query, and the summary always re-reads authoritative run status.

## Security / Privacy / Authorization

- Every evidence request is authorized by recorded workspace ownership at the boundary; run-scoped queries are additionally constrained to runs belonging to the owned project.
- Trace payloads, prompts, source-derived text, filenames, and metadata are untrusted input (D6); display and copy cannot grant tools, change policy, or bypass authorization.
- No trace content enters browser-persistent storage, generic infrastructure logs, cross-user evaluation sets, or model-training data.
- Deletion of a project or account removes all evidence surfaces together with their backing runs, events, traces, and binaries; no copy survives outside documented boundaries.
- No operator access path is introduced; future operator access is disclosed and audited per ADR-0003 and verified by F011 (D9).

## Non-functional

- No new infrastructure product, cache, queue, or second database; evidence aggregation queries existing indexed tables.
- Page sizes, price-table values, and quota keys are settings, not code.
- Trace retention follows ADR-0003 (complete traces retained workspace-scoped); storage cost is an accepted trade-off already recorded there.
- Accessibility: WCAG 2.2 AA for the evidence flow — keyboard-reachable disclosures, pagination, and copy; text semantics for relationships; no color-only or motion-dependent meaning (honors the DRAFT RECOMMENDED relationship-focused, text-semantic first visualization).

## UI Impact

- UI involved: `YES`
- Affected screens: unit workspace evidence view (run inventory + run summary + technical expansion + explanation narration), reached from the workspace navigation as a contextual view; per-panel recovery links remain in their owning panels.
- Primary flow: open evidence view → inspect run inventory → read one run's teacher summary → expand technical evidence pages → optionally stream an explanation → return to task.
- Detailed UX/UI refinement follows `SPEC READY` in `ux-ui.md`.

## Acceptance Criteria

- AC-001: Given an owner with any recorded run of the five kinds, when they open that run's evidence, then a teacher-readable summary appears first — kind, bound intent versions where applicable, authoritative status, scope outcomes, failure reasons with recovery pointers, model-call usage vs cap, aggregate estimated cost and latency — without requiring technical expansion.
- AC-002: Given an owner expands a run's technical evidence, then specialist model calls (prompt payload and parsed response), tool calls with outcomes, checkpoint events, failures, and retries are listed version/run-bound with per-event latency, token usage, estimated cost, and model configuration where recorded.
- AC-003: Given a run whose recorded events exceed one page, when the owner pages through, then a stable cursor returns consecutive pages with no gaps or duplicates under concurrent appends, with an explicit loading state between pages.
- AC-004: Given events recorded before this Feature (no token/cost/model data), when displayed, then each gap is explicit (未记录) at row and summary level while authoritative run and artifact status remains sourced from run tables.
- AC-005: Given events recorded from this Feature onward, when cost is displayed, then it derives from the settings price table and is labeled an estimate, never provider-billed truth; absent token data is shown as not recorded rather than zero.
- AC-006: Given an unauthenticated user or another teacher requests private run evidence, when handled, then no trace content and no resource-existence information is disclosed.
- AC-007: Given any evidence-view interaction (open, page, expand, copy), when completed, then no run, artifact, version, quota, or validation business state changed.
- AC-008: Given project or account deletion completes, when evidence surfaces are requested afterward, then they are gone together with their backing runs, events, traces, and binaries.
- AC-009: Given an owner requests an explanation of a run, when it streams, then teacher-readable findings narration arrives over SSE with stop available, and the complete explanation is recorded in the workspace trace; narration reserves workspace quota, not any run cap.
- AC-010: Given prompts, source-derived text, model outputs, filenames, or metadata rendered or copied in the evidence view, when handled, then they behave as inert untrusted text — no HTML/script execution, no browser-persistent storage, no leak through error messages.
- AC-011: Given discovery and planning runs, when inspected, then their interview rounds (questions, answers, narration) and specialist/tool events appear in the same layered structure as generation runs.
- AC-012: Given a superseded run's evidence, when viewed, then it is marked superseded with the newer version identified and never presented as current.
- AC-013: Given the evidence view operated by keyboard and screen reader, then inventory, summary, disclosures, pagination, and copy are reachable and announced with text semantics; relationship and status meaning never depends on color or animation (evidenced by the executed B-001 keyboard manual pass).
- AC-014: Given the legacy `GET /projects/{id}/trace` endpoint, when this Feature ships, then it no longer exists, the layered evidence API replaces it, and no Web consumer breaks.
- AC-015: Given a small-screen session, when the evidence view is opened, then the canonical reduced experience keeps run-status summary information visible and defers deep trace exploration behind a clear desktop-required message consistent with `docs/UX.md`.

## Open Questions

All DRAFT open questions are resolved by D1–D9 above. Non-blocking residuals:

- [DEFERRED, owner-approved] Exact price-table values are configuration set in the Implementation Plan; estimates are labeled regardless of table accuracy.
- [DEFERRED, owner-approved] Teacher-facing wording for evidence categories and telemetry gaps is a UX-copy choice owned by the UX/UI refinement.
- [DEFERRED, revisit with evidence] Operator troubleshooting access remains unimplemented in Phase 1; F011 owns its disclosed/audited design.
- [DEFERRED, revisit at F008] Cross-version finding queries (F002 review L-2 findings-embedding deferral) are not needed by this Feature's read model.

## Risks and Assumptions

- [CONFIRMED] Every run retains a complete user-owned trace despite privacy and storage cost (ADR-0003); this Feature adds no new retention obligation.
- [CONFIRMED] Teacher-readable evidence precedes technical detail through progressive disclosure (D1).
- [CONFIRMED] Estimated cost is derived, not billed; labeling is mandatory (D2).
- [ASSUMED] Token usage and model identifiers available from the current thin adapter are sufficient cost/configuration evidence in Phase 1; a provider that stops returning usage would surface as an explicit not-recorded gap, not a failure.
- [ASSUMED] Cursor pagination over the existing trace table serves complete-unit traces within interactive latency; F009's fault/metric workloads will validate at scale.
- [RECOMMENDED→CONFIRMED] The first trace visualization stays relationship-focused and text-semantic (no graph animation); revisit only with reviewer and accessibility evidence.

## Deliberately Deferred Detail

- DTO shapes, exact response schemas, and error code strings (Implementation Plan + API doc sync)
- Column names, indexes, and migration steps (Implementation Plan)
- Components, packages, and internal functions (Implementation Plan)
- Pixel-level UI and complete Test Design (`ux-ui.md`, `test-design.md`)

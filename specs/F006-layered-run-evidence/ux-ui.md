# Feature UX/UI: F006 Layered Run Evidence

## Metadata

- Spec/Issue: `specs/F006-layered-run-evidence/spec.md` / [GitHub Issue #12](https://github.com/MaoyuanYang/LessonCanvas/issues/12)
- Validated Spec revision: `SPEC READY` PASS, content hash `b43922d2cc17`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md` (Inspect Technical Evidence flow, Run evidence view screen), `docs/UI.md` (Context/evidence region, detail views, trace-density lists), `docs/DESIGN_SYSTEM.md` (Disclosure/evidence panel, List/table trace density mode, Status marker), `docs/FRONTEND.md` (no browser persistence of trace content, SSE consumption, safe not-found) at base `main @ 5804e86`
- UX/UI artifact revision/change-log ID: `ux-ui-f006-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: shared artifact-run surfaces (`ArtifactProgressList`, `RunOutcomeBanners`, status label maps), shared conversation region (F002 D-CONVO), workspace shell tab navigation, desktop gate, shared `Alert`/`Button`/`EmptyState`/`SkeletonRows`/`StatusBadge` foundations

### UI-level decisions (2026-08-31, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-EVIDTAB | Evidence view placement | Eighth project-context view `运行证据` in the existing workspace shell, after `练习与答案`. Always reachable once a project exists (no prerequisite gate — the view itself explains emptiness); no new top-level navigation. This is the UX.md "Run evidence view" screen: contextual within the unit workspace. |
| D-EVIDINV | Run inventory surface | First screen of the view: a labelled list of the project's runs across all five kinds (需求访谈 / 蓝图规划 / 教案生成 / 课件生成 / 练习生成) with authoritative status in teacher language, bound intent versions where applicable, recency, model-call usage vs cap, aggregate estimated cost (labeled 估算), and one entry action per run. Bounded list in Phase 1; cursor pagination is implemented in the API and surfaces as 加载更多 only when exceeded. |
| D-EVIDSUM | Teacher summary surface (Layer 1) | For the selected run: bound versions, authoritative status (generation runs reuse the shared `RUN_STATUS_LABELS`; discovery/planning get a sibling label map: initializing=初始化中, questioning=提问中, draft_ready=草稿就绪, provider_failed=模型服务失败), scope outcomes (generation runs reuse the shared per-lesson artifact progress list in read-only mode without download actions — downloads stay in their owning panels), failure reasons with recovery pointers rendered as navigation links to the owning view, model-call usage vs cap, aggregate estimated cost and model latency, and explicit telemetry-gap notices (Alert, info/warning tone) when segments are 未记录. |
| D-EVIDTECH | Technical expansion surface (Layer 2) | Below the summary, one collapsed-by-default disclosure region `技术证据`. Inside: a table-like list of the run's evidence events in stable order — columns: 阶段/类型 (teacher-labelled kind, e.g. 模型调用·起草教案, 工具·渲染文档, 工具·结构校验, 面试轮次, 运行状态), 课程 scope where applicable, time, latency, token usage (输入/输出), estimated cost (估算), model identifier; `未记录` markers where legacy events lack data. Each row expands (native disclosure semantics, `aria-expanded`) to the full inert prompt/response text (pre-wrap, escaped by default React text rendering) with one 复制 copy-to-clipboard action per payload block. An optional event-kind filter (select) and 加载更多 cursor paging with explicit loading state complete the surface. No graph visualization; relationships are text-semantic (run → lesson → event ordering) per the Spec's confirmed RECOMMENDED. |
| D-EVIDNARR | Explanation narration | The shared conversation region (F002 D-CONVO) becomes the sixth consumer for run-explanation narration: one 讲解本任务 button on the summary (desktop only), stream with stop control, complete text recorded server-side in the trace (Spec D8). Narration failures show the named provider class with retry as an owner action; quota exhaustion names the workspace boundary. |
| D-EVIDSMALL | Small-screen boundary | Below 1024px the view keeps the run inventory and each run's teacher summary (status, bound versions, failure reasons, cost estimate) readable; the technical evidence expansion and explanation narration are replaced by the existing desktop-required notice naming the deferred task (UX.md defers trace exploration on small screens). |
| D-EVIDA11Y | B-001 keyboard manual pass | Because this Feature touches shared workspace UI, the pending STAGE B-001 manual keyboard pass is executed over this view plus the core flows (per its recorded condition "at next UI touch") and its evidence is recorded in the Test Design execution snapshot. |

Design System promotion decision: the disclosure-based evidence row and the teacher-labelled event-kind vocabulary are recorded as Feature-local compositions over the existing Disclosure/evidence panel and List contracts; promotion to shared variants is deferred until a second consumer exists (F008 findings views are the likely trigger). No new tokens.

These are interface refinements within Spec behavior (D1–D9); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner); the same surface serves an authorized portfolio reviewer operating within the owner's workspace in Phase 1
- Goal: understand why any recorded run produced its current outcome — first in teaching language, then in as much technical depth as needed — without leaving the unit workspace or changing anything
- Entry point: workspace shell -> `运行证据` context view (always reachable)
- Preconditions: valid Clerk session; an owned project (any run state, including none)

```text
Workspace -> 运行证据 view
  -> Inventory: all runs of the five kinds with teacher status, bound versions, recency, cost estimate
       (empty state: explains no run exists yet + names the first workflow action that creates one)
  -> Select one run -> Teacher summary (Layer 1):
       bound versions · authoritative status · per-lesson/scope outcomes · failure reasons + recovery links
       · model-call usage vs cap · aggregate estimated cost/latency · telemetry-gap notices
  -> Expand 技术证据 (Layer 2, collapsed by default):
       event rows page by page via stable cursor (加载更多, explicit loading)
       -> row expands to full inert prompt/response text + 复制
       -> optional event-kind filter
  -> Optional: 讲解本任务 -> streamed explanation (stoppable) -> complete text recorded in trace
  -> Return to any teaching view; nothing changed
Live-run path: summary reflects current status and events recorded so far; no final-outcome projection
Recovery-pointer path: failure rows link to the owning view (教案生成/课件生成/练习生成) which owns resume
Error paths:
  -> unauthenticated: sign-in redirect
  -> non-owner/unknown: safe not-found -> own project list
  -> narration quota exhausted: named quota boundary + recovery (wait/reduce); evidence stays readable
  -> narration provider failure: named class; retry is an owner action, no auto loop
  -> malformed cursor/filter: input-validation message; list unchanged
```

- Success exit: the owner returns to a teaching view with unchanged run state and full version context preserved (tab navigation keeps workspace context)
- Cancel/back behavior: free navigation; nothing cancels; expanded disclosures are transient UI state only
- Permission denied/recovery: safe not-found without existence disclosure, one action back to the project list

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Workspace shell (extended) | Add `运行证据` context view; always-available state (no prerequisite gating) | Project existence only | Switch view | Hosts evidence surfaces | Navigation item |
| Run inventory (D-EVIDINV) | List all five run kinds with teacher status, bound versions, recency, usage, estimated cost; empty state | `GET /projects/{id}/evidence` | Select a run | -> Run summary | Status marker, List, EmptyState, SkeletonRows |
| Run summary (D-EVIDSUM) | Layer 1 explanation: versions, authoritative status, scope outcomes, failures + recovery links, usage, aggregates, gap notices | `GET /projects/{id}/evidence/{run_id}` | Follow recovery links | -> Owning panels (read context preserved) | Shared artifact progress list (read-only), Alert, Status marker, version line |
| Technical expansion (D-EVIDTECH) | Layer 2 evidence events: labelled rows, lesson scope, latency/tokens/cost/model, per-row payload disclosure with copy, cursor paging, kind filter | `GET /projects/{id}/evidence/{run_id}/events` | Expand/collapse row; copy payload; filter; 加载更多 | None (read-only) | Disclosure/evidence panel contract, List trace density |
| Explanation narration (D-EVIDNARR) | Streamed teacher-readable explanation of the run's findings with stop | `POST .../narrate`, `GET .../narrate/stream` (SSE) | 讲解本任务; stop | None (recorded in trace) | Shared conversation region |
| Small-screen notice (D-EVIDSMALL) | Defer technical expansion/narration below 1024px while keeping summary readable | Viewport | Read summary | Desktop for depth | Desktop gate notice |

Component responsibility rule unchanged: networking/error normalization lives in the shared API layer; no component owns backend state transitions; SSE events update client projections only; the evidence view issues no state-changing requests except narration start.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Inventory | Empty (no run) | Project has zero runs | Empty state: why empty + first workflow action link | Go create a run (来源/需求访谈) | Inventory result | First run appears |
| Inventory | Loading | Entry/refresh | Skeleton preserving layout | Wait | Request in flight | Success or error |
| Inventory | Loaded | Runs exist | Run rows with kind/status/versions/cost | Select a run | Inventory result | Summary |
| Inventory | Error | Request failure | Named error class + retry | Retry/back | Error code | Recovery path |
| Summary | Loading | Run selected | Skeleton preserving layout | Wait | Request in flight | Success or error |
| Summary | Active run | Run queued/generating/validating/questioning | Live status; events recorded so far; no final projection | Leave freely; follow links | Summary + events | Updated status |
| Summary | Settled run | complete/partial/capped/superseded/terminal/draft_ready/provider_failed | Status in teacher language; outcomes; failure reasons; recovery pointers | Follow links; expand evidence | Summary | Owning views |
| Summary | Missing telemetry | Legacy events / narration gaps | Explicit gap notice (未记录) at summary level | Continue reading | Summary flags | None needed (explicit) |
| Summary | Superseded run | Run superseded | Superseded marker naming the newer version; never current impression | View history only | Summary | Newer version's run |
| Technical evidence | Collapsed (default) | Layer 2 entry point | One disclosure trigger `技术证据` | Expand | — | Event list |
| Technical evidence | Events loading | Expansion/page | Explicit loading indicator between pages | Wait | Cursor page in flight | Next page or end |
| Technical evidence | Loaded page | Page arrives | Labelled rows with metrics; 未记录 markers | Expand row; copy; filter; 加载更多 | Cursor page | Next page |
| Technical evidence | Expanded detail | Row expanded | Full inert prompt/response text + 复制 | Copy; collapse | Row payload (already fetched) | — |
| Technical evidence | End of trace | Cursor exhausted | 明确「已全部加载」 terminus; no infinite loader | — | Cursor end | — |
| Technical evidence | Malformed cursor/filter | Bad client state | Input-validation message; list unchanged | Correct filter; reload | Validation error | List restored |
| Narration | Streaming | 讲解本任务 active | Incremental explanation text with stop | Stop | SSE stream | Complete text recorded |
| Narration | Provider failure | Stream/model error | Named provider class | Retry (owner action) | Error code | No auto loop |
| Narration | Quota exhausted | Workspace quota reached | Named quota boundary + recovery | Wait/reduce usage | Quota error | Evidence still readable |
| Global | Permission denied | Non-owner/unknown | Safe not-found | Back to own projects | No disclosure | Project list |

Assessed states: Initial, Loaded, Submitting (`narrate` button loading + disabled), Disabled (narration desktop-only below 1024px; filter reset), Unauthorized, Forbidden-as-not-found, Offline (inventory/summary requests fail → named error with retry; recorded evidence is server-side and never lost), Partial Failure (run state, displayed not triggered), Superseded, Large-trace paging.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Event-kind filter | One of the served kind values | Unknown kind → input-validation error; list unchanged | Inline; focus preserved | Filter is read-only query state |
| 加载更多 paging | Cursor comes only from the served page | Malformed cursor → input-validation error; list unchanged | Button loading during fetch | Cursor is monotonic; no duplicate rows |
| Row disclosure / copy | — | — | Disclosure moves focus per shared pattern; copy confirms visually | Idempotent reads |
| 讲解本任务 | Desktop-only; disabled while streaming | Workspace-quota guard; idempotent per active narration per run | Button loading; focus to narration region | One active narration per run per workspace |
| Stop narration | Available while streaming | Server stop semantics (established pattern) | Immediate stop | Idempotent stop |

Client validation never replaces server constraints; the evidence view performs no governed business transitions.

## Frontend/Backend Contract

- Request/response: typed API client over the Spec's evidence endpoints (`/projects/{id}/evidence`, `/projects/{id}/evidence/{run_id}`, `/projects/{id}/evidence/{run_id}/events?after=&limit=&kind=`, `POST /projects/{id}/evidence/{run_id}/narrate`, `GET /projects/{id}/evidence/{run_id}/narrate/stream` SSE with `Last-Event-ID`); JSON for queries; SSE for narration. Exact DTO field names and the SSE event envelope are frozen schema-first (Zod) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: Clerk session token attached by the shared API client; 401 → sign-in redirect; 404 (ownership) → safe not-found; every evidence read is owner-authorized server-side.
- Pagination: stable cursor (event id) for technical events; bounded pages (settings default/max); inventory cursor-paginated with 加载更多 when exceeded.
- Optimistic update/rollback: `N/A - read-only projection; no local mutation of business state`.
- Version preconditions: none for reading evidence (any run, any settle state, including superseded history); bound versions are displayed from the served run record, never guessed client-side.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in with return path | Sign in | Return | Yes |
| 404 (ownership/not-found) | Safe not-found | Back to project list | None disclosed | Yes |
| VALIDATION (malformed cursor/filter) | Inline message; list unchanged | Correct and retry | List restored | Yes |
| QUOTA_EXCEEDED (narration) | Named workspace quota boundary + recovery | Wait / reduce usage | Evidence readable | Yes |
| PROVIDER_TRANSIENT / PROVIDER_UNAVAILABLE (narration) | Named provider class; retry is owner action | Retry narration | No auto loop | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes — no prompt, path, or provider secret ever shown |

Errors never collapse into one vague toast; mapping follows `docs/API.md` taxonomy and `docs/UX.md` state principles.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full evidence view: inventory, complete summary with scope outcomes and recovery links, technical expansion with payload disclosure and copy, narration stream | Full context nav; all disclosures/paging/copy keyboard operable | Dense event rows wrap long payload text (pre-wrap, no horizontal scroll) |
| Reduced <1024px | Run inventory and teacher summary preserved (status, bound versions, failure reasons, cost estimate) | Technical expansion and narration replaced by desktop-required notice naming the deferred task (D-EVIDSMALL) | Single reading sequence |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md rule that small screens preserve task status and failure/recovery information while deferring trace exploration.

## Accessibility

- Semantic structure/labels: the view reuses workspace landmarks; the inventory is a labelled list (run heading = kind + recency); the technical region is a labelled disclosure (`技术证据`, `aria-expanded`); event rows are list items with heading-level kind + scope text; payload text sits in labelled `pre-wrap` text blocks; cost is text labeled 估算, never color-only; 未记录 gaps are text markers plus a summary-level notice.
- Keyboard and focus order/recovery: inventory selection, disclosure, per-row expand/collapse, copy, filter, 加载更多, and narration start/stop are keyboard reachable in reading order; disclosure toggles keep focus on the trigger; narration start moves focus to the narration region; stop returns focus to its trigger; no focus movement for passive page loads. The D-EVIDA11Y manual keyboard pass (B-001) covers this view plus core flows and is recorded as evidence.
- Live announcements: narration text announced in throttled semantic batches (shared conversation region behavior); page loads and gap notices use polite status; no per-event announcement noise.
- Contrast/non-color cues: status uses shared text+marker pairs; superseded vs complete distinguished in language; token set >=4.5:1 body / >=3:1 components.
- Motion/reduced motion: no animation-dependent meaning; skeleton honors reduced-motion.
- Touch targets >=24px in reduced layout.
- Verification approach: automated accessibility checks in component/E2E tests plus the executed manual keyboard/screen-reader pass recorded in the Test Design execution snapshot.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, alerts, status markers, skeleton/empty, navigation item, list | F001–F005 foundations | Reuse | All variants exist | None |
| Per-lesson scope outcomes in summary | Shared `ArtifactProgressList` (F004 promotion) | Reuse (read-only consumer, no actions) | Identical semantics; actions stay in owning panels | None |
| Teacher status language | Shared `RUN_STATUS_LABELS` + new sibling label map for discovery/planning statuses | Compose (label map as a sibling, shared file) | Same status language rule across kinds | Usage noted at documentation sync |
| Conversation/narration region | F002 shared component (D-CONVO) | Reuse (sixth consumer, D-EVIDNARR) | Identical stop/trace semantics | None |
| Disclosure/evidence panel + trace-density list | DESIGN_SYSTEM contracts (Disclosure/evidence panel, List trace density mode) | Compose (Feature-local evidence row) | First concrete consumer of the recorded contracts; promotion deferred until F008 needs the same shape | Deferred-promotion note at documentation sync |
| Desktop gate | F003/F004 pattern | Reuse | Same deferred-task notice semantics | None |

No new tokens; no new visual language; no graph animation.

## UI Acceptance Links

- AC-001 teacher summary first: D-EVIDSUM surface (Layer 1 before any expansion)
- AC-002 technical expansion: D-EVIDTECH event list with metrics and payload disclosure
- AC-003 cursor paging: 加载更多 with explicit loading and no-gap/no-duplicate contract
- AC-004 missing telemetry: 未记录 row markers + summary-level gap notice (D-EVIDSUM)
- AC-005 estimated cost labeling: 估算 label on every cost figure; never zero-masking
- AC-006 no cross-user disclosure: permission-denied row in State Matrix; safe not-found
- AC-007 read-only interactions: component responsibility rule + forms table (no business mutations)
- AC-008 deletion: no surviving UI surface; backing data deleted (account/project flows own the action)
- AC-009 explanation narration: D-EVIDNARR (stream, stop, recorded, workspace quota)
- AC-010 safe display/copy: D-EVIDTECH inert payload blocks + copy; FRONTEND.md no-browser-persistence rule
- AC-011 discovery/planning coverage: D-EVIDINV five kinds + D-EVIDSUM sibling status labels + interview-round events
- AC-012 superseded marking: Summary superseded row (newer version named)
- AC-013 keyboard/screen-reader: Accessibility section + D-EVIDA11Y manual pass
- AC-014 legacy endpoint removal: no UI surface ever referenced it; API contract section lists only evidence endpoints
- AC-015 small-screen boundary: D-EVIDSMALL + Responsive table

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact SSE narration envelope and DTO field names for evidence endpoints | Non-critical | Implementation assignee | Frozen schema-first (Zod) in the first implementation task within Spec semantics; behavior fixed by Spec D4/D7/D8 | RESOLVED |
| UIQ-002 | Teacher-facing wording of event kinds and telemetry gaps | Non-critical | `YMY / Project Owner` | zh-Hans labels: 模型调用 / 工具调用 / 运行状态 / 面试轮次 / 讲解; gaps uniformly 未记录 with summary notice 部分早期记录未包含用量与成本数据; enum values fixed by trace event types | RESOLVED |
| UIQ-003 | Whether summary reuses shared artifact list with or without actions | Non-critical | Implementation assignee | Read-only reuse without download/resume actions (D-EVIDSUM); owning panels keep actions — evidence links, never performs | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, and the complete User Flow are explicit. | YES | User Goal and Flow incl. inventory-empty, live-run, recovery-pointer, narration, error, small-screen paths |
| UR-02 | Each affected Page, Screen, and Component has an explicit responsibility. | YES | Responsibilities table, 6 surfaces |
| UR-03 | The UI State Matrix covers applicable states. | YES | 18-row matrix + assessed-state paragraph covering empty/loading/active/settled/superseded/gap/paging/narration/permission/offline |
| UR-04 | Permission, validation, duplicate submit, cancel, back, and recovery are explicit. | YES | Forms table (filter/paging/disclosure/copy/narration), read-only rule, safe not-found |
| UR-05 | Frontend/Backend contract and error mapping are explicit. | YES | Contract section over the five Spec endpoints + 6-row error mapping |
| UR-06 | Responsive behavior is verifiable. | YES | 1024px table: inventory + summary preserved; expansion/narration deferred with notice |
| UR-07 | Accessibility behavior is verifiable. | YES | A11y section: disclosure semantics, focus rules, live-region batching, non-color cues, D-EVIDA11Y manual pass plan |
| UR-08 | Existing components and Design System checked with explicit reuse/extension decisions. | YES | Reuse table incl. first concrete Disclosure/evidence-panel consumption and deferred promotion note |
| UR-09 | UI Acceptance linked to `AC-*`. | YES | All 15 ACs mapped to surfaces |
| UR-10 | No Critical UI Open Question `OPEN`/`DEFERRED`. | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (see Spec Gate Record, spec @ `b43922d2cc17`) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 5804e86` + this artifact `ux-ui-f006-r1` @ `4bff46959bb0`
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `b43922d2cc17`
- Validated UX/UI revision: `ux-ui-f006-r1` @ `4bff46959bb0`
- Validated at: 2026-08-31
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-31
- Approval scope: F006 UX/UI refinement at `ux-ui-f006-r1`

# Feature UX/UI: F002 Confirmed Unit Blueprint

## Metadata

- Spec/Issue: `specs/F002-confirmed-unit-blueprint/spec.md` / [GitHub Issue #3](https://github.com/MaoyuanYang/LessonCanvas/issues/3)
- Validated Spec revision: `SPEC READY` PASS, content hash `108178994342` (base `8bf078e`)
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `8bf078e` plus working-tree edits listed in the UI READY Record
- UX/UI artifact revision/change-log ID: `ux-ui-f002-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: `docs/UX.md` (flows, states, a11y), `docs/UI.md` (patterns), `docs/DESIGN_SYSTEM.md` (tokens, components), F001 workspace implementation

### UI-level decisions (2026-08-28, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-NAV | Blueprint placement | Fourth project-context view `单元蓝图` in the existing workspace shell, after `教学简报`; unavailable state names the brief-confirmation requirement; no new top-level navigation |
| D-CONVO | Conversation region reuse | The F001 streaming conversation region becomes a shared component (second consumer: planning interview). Promotion into the shared frontend foundations is recorded at Documentation Sync per `docs/DESIGN_SYSTEM.md` governance |
| D-FIND | Findings presentation | A single findings region lists blocking and waivable findings with distinct status language (`阻断` vs `可决策`); waivable decisions collect a reason through a consequence modal; the reason is displayed with the finding afterwards |

These are interface refinements within Spec behavior (D5, D3, D8); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: review and confirm how confirmed unit intent is distributed across every lesson, resolving planning gaps and findings, producing an immutable blueprint version
- Entry point: workspace shell -> `单元蓝图` context view (enabled once a confirmed brief exists)
- Preconditions: valid Clerk session; confirmed brief version; planning quota available

```text
Workspace (brief confirmed) -> 单元蓝图 view
  -> Start planning (quota-checked, idempotent)
  -> Agent streams planning-gap questions (rounds <= 6, <= 3 questions each) -> Teacher answers
  -> Blueprint draft presented (unit objectives + every lesson, citations, findings)
  -> Structured correction (new draft revisions, base-revision guard)
  -> Resolve findings:
       blocking -> correct the draft
       waivable -> correct OR record decision + reason (modal)
  -> Completeness panel shows the four checks live
  -> Confirm (enabled when checks pass and findings resolved/decided) -> immutable version N
Stale path:
  -> new brief version confirmed elsewhere -> blueprint view shows stale banner
     + field-level brief diff + impact summary -> teacher starts a new planning run
Error paths:
  -> provider failure: named error + retry (state preserved)
  -> stale edit: conflict banner -> reload -> re-apply
  -> stop streaming: display stops; complete response stays in trace; explicit re-ask
  -> quota: quota alert before run creation
  -> permission denied / unknown project: safe not-found -> back to own project list
Cancel/back: leaving preserves run and draft state; return reconnects to authoritative state.
```

- Success exit: blueprint shows `confirmed` status marker with version label; the view states it is the authorized input for generation (F003 entry later)
- Cancel/back behavior: back never discards a draft or confirmed version; leaving during streaming lets the model call complete server-side; returning reconnects without a duplicate run
- Permission denied/recovery: safe not-found (no existence disclosure) with a single action back to the teacher's project list

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Workspace shell (extended) | Add `单元蓝图` context view with current phase and unavailable reason | Brief confirmation state | Switch context view | Hosts blueprint surfaces | Navigation item, Status marker |
| Blueprint panel — start/progress | Explain planning readiness; start planning; show run phase and streaming narration | `POST /planning/start`, `GET /planning`, `GET /planning/stream` (SSE) | Start, answer, stop narration, re-ask | Produces draft | Phase tracker, Button, shared conversation region (D-CONVO) |
| Blueprint panel — draft review | Present unit objectives and every lesson with citations; structured correction; live completeness checks | `GET /blueprint`, `PATCH /blueprint/draft` | Edit fields, save revision | New draft revision | Input, Status marker, Disclosure (evidence), citation marker |
| Findings region (D-FIND) | List blocking and waivable findings; record teacher decisions with reasons | Findings in `GET /blueprint`, `POST /blueprint/decisions` | Correct, record decision | Finding resolved/decided state | Alert, Modal (consequence), Input (reason) |
| Blueprint confirm | Summarize consequence; execute confirmation | `POST /blueprint/confirm` | Confirm | Immutable version | Modal (confirm consequence), Status marker |
| Stale view | Show stale banner, field-level brief diff, impact summary; route to new planning | Stale state in `GET /blueprint` | Start new planning | New run bound to new brief version | Alert (stale), diff list, Button |
| Safe not-found | Non-disclosing terminal for unauthorized/unknown resources | Route guard result | Return to project list | -> Project list | Empty state, Button |

Component responsibility rule: unchanged from F001; networking/error normalization lives in the shared API layer; no component owns backend state transitions.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Blueprint | Unavailable (no confirmed brief) | Brief not confirmed | Explanation naming the brief gate + link to brief view | Go to brief | Brief state | Confirm brief first |
| Blueprint | Loading | Entry/refresh | Skeleton rows preserving layout | Wait | Request in flight | Success or error |
| Blueprint | Generating/waiting for answer | Planning run active with questions | Question list with gap context; phase tracker | Answer, stop narration | SSE events | Submit answer |
| Blueprint | Streaming | Narration in flight | Incremental text, visible stop control | Stop display | SSE token events | Stop or wait |
| Blueprint | Stopped-display | Teacher pressed stop | Note: response completing in background; full text in trace | Continue, re-ask (quota note) | Run continues | Re-ask or proceed |
| Blueprint | Provider failure | Model outage/timeout | Named provider error (outage vs timeout vs rate) | Retry | provider/transient | Retry preserves state |
| Blueprint | Draft ready | Planning produced draft | Draft badge, revision label, citations, findings, live completeness checks | Edit, resolve findings, confirm when enabled | Draft revision | Confirm |
| Blueprint | Incomplete (failed checks) | A completeness check fails | Check list naming failed check and affected lessons/objectives | Correct draft | Requirement rule | Fix items |
| Findings | Blocking finding | Missing lesson/field, coverage gap, count mismatch | Severe alert; correction entry points | Correct draft | Finding state | Blocking cleared |
| Findings | Waivable pending | Source conflict, standards warning, period warning | Warning alert with evidence + two actions | Correct, or record decision + reason | Finding state | Decided or fixed |
| Findings | Waivable decided | Teacher recorded reason | Decision shown with reason and timestamp | Revisit decision (new correction) | Recorded decision | Supersede by correction |
| Blueprint | Confirm blocked | Checks failing or findings undecided | Confirm disabled + reason listing failing checks/findings | Complete items/decisions | Requirement rule | Enable confirm |
| Blueprint | Stale conflict | Save/confirm against old base | Conflict banner: newer revision exists | Reload, re-apply | stale-version/conflict | Reload |
| Blueprint | Stale (new brief version) | Brief re-confirmed | Stale banner + brief field diff + impact summary; confirmed version kept visible as history | Start new planning | Stale state + diff | New run |
| Blueprint | Confirmed | Confirmation success | Success label: confirmed version N; authorized input for generation; evidence link | View evidence; start correction (new draft) | Immutable version | F003 entry later |
| Global | Quota | Quota exhausted before start | Quota alert with wait/cleanup guidance | None expensive | quota/rate-limit | Wait or cleanup |
| Global | Offline / SSE disconnect | Network drop | Banner: connection lost; remote work may continue; reconnecting | Wait/auto-reconnect | Reconnect from authoritative state | Never duplicates run |
| Global | Permission denied | Non-owner or deleted resource | Safe not-found | Return to own projects | No disclosure | Project list |

Assessed states: Initial (no run yet), Loaded, Submitting (answer/save/confirm/decision buttons show loading and disable), Disabled (confirm blocked, start blocked with reason; nav item unavailable with reason), Unauthorized (redirect to sign-in), Forbidden-as-not-found (non-disclosure), Offline (SSE banner), Partial Failure (provider failure preserving completed rounds), Superseded (stale run after brief re-confirmation).

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Planning start | Enabled only with confirmed brief | Quota check; idempotent active-run return; requirement error without brief | Button loading | Server idempotent per project |
| Planning answer | Non-empty, <= 4000 chars | Revalidate; requirement/input error | Submit on button; Ctrl/Cmd+Enter optional | Client answer id -> server idempotency |
| Lesson field edit | Title/objectives/assessment intent required awareness; period count positive integer when present | Revalidate all rules on save; completeness checks server-side at confirm | Field-level errors + summary focus | Base revision check -> stale conflict |
| Add/remove lesson | Lesson count check preview (vs brief count) shown live | Enforced at confirm | Summary before save | Base revision check |
| Finding decision reason | Non-empty, <= 1000 chars | Revalidate; decision recorded with reason | Modal focus; reason associated with finding | One decision per finding state; re-decision via correction |
| Confirm blueprint | Enabled only when checks pass and findings resolved/decided | Atomic server check; names failing items; idempotent per base revision | Consequence modal (downstream authority statement) | Confirmation idempotent per base revision |
| Re-plan | Available after a completed run | New run after terminal state; quota check | Explicit button | Active run reused, not duplicated |
| Re-ask | Available after stop/completion | Quota check | Explicit button with quota note | Server rejects duplicate in-flight re-ask |

Client validation never replaces server constraints. The completeness panel is guidance; the server revalidates all four checks at confirmation.

## Frontend/Backend Contract

- Request/response: typed API client over the Spec API Behavior endpoints (`/planning/*`, `/blueprint*`); JSON for commands/queries; SSE for the planning stream. Exact DTO field names and SSE event envelopes are frozen schema-first via Zod in the first implementation task within Spec semantics; any deviation from Spec semantics is a Design Change.
- Authentication/authorization: Clerk session token attached by the shared API client; 401 -> sign-in redirect; 404 (ownership) -> safe not-found.
- Pagination: `N/A - bounded lists` (one active run, one current draft/version, quota-bounded lessons).
- Optimistic update/rollback: `N/A - authoritative server state governs drafts/versions; no optimistic mutation of governed state`.
- Version preconditions: draft mutation and confirmation carry the expected base revision.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in with return path | Sign in | Return to entry | Yes |
| 404 (ownership/not-found) | Safe not-found page | Back to project list | None disclosed | Yes |
| VALIDATION / REQUIREMENT (planning start without brief) | Explanation naming the brief gate + link | Go to brief | Confirm brief | Yes |
| VALIDATION / REQUIREMENT (confirm blocked) | Failed checks and affected lessons/objectives listed | Correct items | Complete checks | Yes |
| VALIDATION / REQUIREMENT (undecided findings) | Findings awaiting fix or decision listed | Resolve findings | Decide or fix | Yes |
| STALE_VERSION | Conflict banner: newer revision exists | Reload, re-apply | Reload current | Yes |
| QUOTA_EXCEEDED | Quota alert with concrete guidance | Wait or cleanup | Guidance actions | Yes |
| PROVIDER_TRANSIENT | Named provider error (outage/timeout/rate) | Retry | State preserved | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation ID | Retry/back | Report path later | Yes |

Errors never collapse into a single vague toast; mapping follows `docs/UX.md` state behavior and `docs/API.md` taxonomy. Stale-after-brief-change is a governed state view (banner + diff), not an error toast.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full blueprint: unit objectives, every lesson, citations, findings, and completeness panel with side-by-side evidence disclosure; current decision first | Full context nav; keyboard accelerators | Dense review layout; no horizontal scroll for core content |
| Reduced <1024px | Read-only status first: blueprint status (draft/confirmed/stale), lesson list with objectives summary, findings summary; conversational answering preserved | Simplified nav; editing/decision/confirm replaced by desktop-required message | Single reading sequence |
| Reduced <1024px, structured tasks | Attempting edit/decision/confirm/re-plan | Explicit desktop-required notice naming the task (Spec D8) | No degraded editing surfaces |

Breakpoint: 1024px (F001 D-BP). The boundary implements Spec D8 and `docs/UX.md` canonical reduced experience.

## Accessibility

- Semantic structure/labels: blueprint landmarks reuse the workspace shell; the lesson list uses a semantically associated structure (lesson heading + fields); completeness checks are a labelled status region; findings pair text labels (`阻断`/`可决策`) with visual treatment; the shared conversation region keeps its labelled stream semantics.
- Keyboard and focus order/recovery: all actions keyboard reachable; decision and confirm modals trap focus and return to the trigger; after save/decision/confirm, focus moves to the resulting status; after an error summary, focus moves to the first actionable problem; lesson add/remove is keyboard operable with logical order.
- Error association and live announcements: field errors associated with controls; phase changes (question round arrived, draft ready, finding decided, checks passed, confirmed, stale) announced via polite live region; completeness check transitions announced on change, not per keystroke; streamed text announced in throttled semantic batches.
- Contrast/non-color cues: existing token set (>=4.5:1 body, >=3:1 components); blocking vs waivable findings never distinguished by color alone (text labels + icons); stale state uses label + treatment.
- Motion/touch target considerations: streaming caret and phase transitions short and purposeful; reduced-motion preference honored; touch targets >=24px in reduced layout.
- Verification approach: automated checks plus manual keyboard/focus pass for start -> answer -> correct -> decide -> confirm and the stale path; results recorded in Test Design evidence.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, inputs, modals, alerts, status markers, disclosure, skeleton/empty, phase tracker, navigation item | F001 implementations of DESIGN_SYSTEM contracts | Reuse | All required variants exist | None |
| Streaming conversation region | F001 Feature-local pattern | Extend -> shared component (D-CONVO) | Second consumer (planning interview) triggers promotion per governance | Shared component + usage note added at Documentation Sync |
| Citation marker (source vs standards snapshot) | F001 evidence marker pattern | Reuse | Same semantics (source ref / snapshot version) | None |
| Findings list with two tiers + recorded decision | Alert + Modal + Input composition | Compose Feature-local; promote with F006 evidence | First findings surface; alignment findings arrive in F006 | Deferred with trigger |
| Stale view (banner + brief diff + impact summary) | Alert (stale) + list composition | Compose Feature-local; promote with F007 evidence | Version comparison deepens in F007 | Deferred with trigger |
| Completeness checks panel | Status marker + list composition | Compose Feature-local | Maps Spec D1 checks 1:1 | None |

No new tokens; no new visual language. All statuses use the shared stale/draft/confirmed/waiting status language from `docs/DESIGN_SYSTEM.md`.

## UI Acceptance Links

- AC-001 planning start/gate/quota: Blueprint start/progress surface, unavailable state, quota alert
- AC-002/AC-003 questioning and cap: shared conversation region, waiting/streaming states, unresolved-gap markers
- AC-004 draft grounding: Draft review surface, citations, lesson list
- AC-005 correction/stale edit: Lesson field edit + conflict banner
- AC-006 blocking findings: Findings region (blocking), confirm-blocked reason
- AC-007 waivable findings: Findings region (waivable) + decision modal with reason
- AC-008 confirmation: Confirm modal + confirmed status marker
- AC-009 stale after brief change: Stale view (banner + diff + impact summary)
- AC-010 standards citation: Citation marker distinguishing snapshot evidence
- AC-011 non-disclosure: Safe not-found surface
- AC-012 provider failure: Provider error mapping
- AC-013 streaming stop/re-ask/reconnect: Streaming states + offline banner
- AC-014 small screen: Reduced boundary behavior
- AC-015 trace: Evidence link to owner-scoped trace (F001 trace view)
- AC-016 authorization boundary: Confirmed-state wording; no generation entry exposed

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact SSE event envelope and DTO field names for planning/blueprint | Non-critical | Implementation assignee | Frozen schema-first in the first implementation task within Spec semantics; behavior already fixed | RESOLVED |
| UIQ-002 | Participating teacher validation of the blueprint flow | Non-critical (for this Gate) | `YMY / Project Owner` with teacher | Flow follows confirmed UX.md IA; teacher review scheduled during implementation demo; recorded as follow-up evidence | RESOLVED |
| UIQ-003 | Promotion of findings/stale/diff patterns to Design System | Non-critical | Design System owner | Deferred with triggers (F006/F007 evidence) recorded in the reuse table | RESOLVED (decision recorded: defer with trigger) |

No Critical UI Open Question is OPEN or DEFERRED.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, and the complete User Flow are explicit. | YES | User Goal and Flow section incl. stale path, error paths, cancel/back |
| UR-02 | Each affected Page, Screen, and Component has an explicit responsibility. | YES | Page/Screen/Component table, 7 surfaces |
| UR-03 | The UI State Matrix covers applicable Loading, Empty, Error, Success, and other states. | YES | 18-row matrix + assessed-state paragraph |
| UR-04 | Permission, validation, duplicate submit, cancel, back, and recovery behavior are explicit. | YES | Forms table (duplicate protection), permission rows, cancel/back in flow |
| UR-05 | The Frontend/Backend contract and error mapping are explicit. | YES | Contract section + 9-row error mapping |
| UR-06 | Responsive behavior is verifiable. | YES | 1024px breakpoint table implementing Spec D8 |
| UR-07 | Accessibility behavior is verifiable. | YES | A11y section with concrete focus/announcement/contrast behaviors + verification approach |
| UR-08 | Existing components and the Design System were checked, with an explicit reuse/extension decision. | YES | Reuse table; conversation-region promotion decision (D-CONVO) with governance trigger |
| UR-09 | UI Acceptance is in the Spec or explicitly linked to `AC-*`. | YES | UI Acceptance Links maps every AC with UI surface |
| UR-10 | No Critical UI Open Question is `OPEN` or `DEFERRED`. | YES | Open Questions table; none Critical unresolved |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (see Spec Gate Record) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` (base `8bf078e` + working-tree edits) + this artifact `ux-ui-f002-r1` @ `a8cfd23189ac`
- Evidence checklist result: ALL YES
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `108178994342`
- Validated UX/UI revision: `ux-ui-f002-r1` @ `a8cfd23189ac`
- Validated at: 2026-08-28
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-28
- Approval scope: F002 UX/UI refinement at `ux-ui-f002-r1`

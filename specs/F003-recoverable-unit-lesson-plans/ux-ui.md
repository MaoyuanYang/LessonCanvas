# Feature UX/UI: F003 Recoverable Unit Lesson Plans

## Metadata

- Spec/Issue: `specs/F003-recoverable-unit-lesson-plans/spec.md` / [GitHub Issue #6](https://github.com/MaoyuanYang/LessonCanvas/issues/6)
- Validated Spec revision: `SPEC READY` PASS, content hash `193e90d10b68`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `4ccc4ef`
- UX/UI artifact revision/change-log ID: `ux-ui-f003-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: `docs/UX.md` (IA already reserves generation as a workspace contextual view), F001/F002 workspace implementation, shared conversation region (F002 D-CONVO)

### UI-level decisions (2026-08-29, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-GEN | Generation placement | Fifth project-context view `教案生成` in the existing workspace shell, after `单元蓝图`; unavailable state names the blueprint-confirmation requirement; no new top-level navigation. The entry always shows the bound brief/blueprint version pair before start. |
| D-PROG | Progress surface | One phase tracker (queued → generating → validating → terminal states) plus a per-lesson progress list (index, title, per-lesson state) fed by SSE from the authoritative event log; the pollable snapshot is the fallback and the tie-breaker. Per-lesson rows never expose internal step names beyond the Spec's per-lesson states. |
| D-NARR | Narration reuse | The shared conversation region (F002 D-CONVO) becomes the third consumer for generation narration; narration has its own stop control; stopping narration never affects the run (AC-010). |
| D-ART | Artifact list | Per-lesson artifact rows inside `教案生成`: status marker, download action when complete and valid, per-lesson failure reason when failed, scoped resume action for eligible failures; superseded runs keep artifacts visible under a superseded banner without a download-as-current impression. |
| D-RECN | Reconnect behavior | SSE drop shows a reconnecting banner stating remote work continues; reconnect replays missed events via `Last-Event-ID`; leaving the view never cancels the run; returning reconnects to the authoritative snapshot without creating a replacement run. |

These are interface refinements within Spec behavior (D2, D4, D5); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: start all-lesson plan generation from the confirmed blueprint, leave or monitor safely, understand partial failures, resume eligible work, and download every completed editable lesson plan
- Entry point: workspace shell -> `教案生成` context view (enabled once a blueprint is confirmed)
- Preconditions: valid Clerk session; confirmed brief and blueprint versions; at least one lesson in the blueprint

```text
Workspace (blueprint confirmed) -> 教案生成 view
  -> Review bound versions (brief vX + blueprint vY) and language mode -> Start generation
       (idempotent: an existing same-version run is returned and shown)
  -> Acknowledged immediately: queued run snapshot -> teacher may leave safely
  -> Monitor (optional): phase tracker + per-lesson states + narration (stoppable)
  -> Outcomes:
       complete -> every lesson row offers authorized download
       partial_failure -> failed lessons show reasons + scoped resume action
       capped_failure -> cap usage shown; completed lessons downloadable; recovery guidance
       superseded -> banner names the newer confirmed version; run history preserved
       terminal_failure -> named final failure; completed lessons still downloadable
Resume path (eligible failures):
  -> scoped resume re-dispatches the SAME run -> only failed/incomplete lessons run
Reconnect path:
  -> SSE drop -> reconnecting banner -> replay from Last-Event-ID -> snapshot remains pollable
Error paths:
  -> teacher_blocked (no confirmed versions): explanation + link to 单元蓝图
  -> provider failure: named error class + bounded-retry status, state preserved
  -> unauthorized/unknown project: safe not-found -> back to own project list
Cancel/back: leaving preserves the run and all completed lessons; back never cancels; no run cancel action exists in F003.
```

- Success exit: run `complete`; every lesson row shows a valid artifact with download; the view names the bound versions the artifacts belong to
- Cancel/back behavior: free navigation away and back; return reconnects to authoritative state
- Permission denied/recovery: safe not-found (no existence disclosure) with one action back to the teacher's project list

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Workspace shell (extended) | Add `教案生成` context view with phase and unavailable reason | Blueprint confirmation state | Switch context view | Hosts generation surfaces | Navigation item, Status marker |
| Generation panel — start | Show bound brief/blueprint version pair, language mode, lesson count; start generation; explain idempotent duplicate handling | `GET /generation`, `POST /generation/start` | Start | Creates/returns run | Button, Status marker, version citation |
| Generation panel — progress | Phase tracker; per-lesson progress list; cap usage indicator; narration stream with stop | `GET /generation/events` (SSE), `GET /generation` snapshot | Stop narration; leave freely | Live run state | Phase tracker, per-lesson status markers, shared conversation region (D-NARR) |
| Artifact list (D-ART) | Per-lesson outcomes: complete/valid, failed with reason, pending; download; scoped resume for eligible failures | `GET /generation` snapshot, `GET /lesson-plans/{id}/download` | Download, resume | Authorized DOCX delivery / re-dispatch | Status marker, Button, disclosure (reason) |
| Outcome banners | complete / partial_failure / capped_failure / superseded / terminal_failure summaries with next actions | Run status in snapshot | Follow offered action | Recovery paths | Alert variants, Status marker |
| Reconnect banner (D-RECN) | Explain SSE drop and remote continuation; auto-reconnect with replay | SSE connection state | Wait / manual reconnect | Restored progress | Alert (offline), existing offline pattern |
| Safe not-found | Non-disclosing terminal for unauthorized/unknown resources | Route guard | Return to project list | -> Project list | Empty state, Button |

Component responsibility rule unchanged: networking/error normalization lives in the shared API layer; no component owns backend state transitions; SSE events update client projections only.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Generation | Unavailable (no confirmed blueprint) | Blueprint not confirmed | Explanation naming the blueprint gate + link | Go to blueprint view | Blueprint state | Confirm blueprint |
| Generation | Empty (no run yet) | Confirmed versions, no run | Start panel with bound versions and lesson count | Start generation | `POST start` | Run created/returned |
| Generation | Loading | Entry/refresh | Skeleton preserving layout | Wait | Request in flight | Success or error |
| Generation | Queued | Run created, work not started | Queued phase marker; safe-leave note | Leave freely | Snapshot/events | Generating |
| Generation | Generating | Active run | Phase tracker; per-lesson rows pending→drafting→rendering→validating→complete; narration stream | Stop narration; leave | SSE + snapshot | Validating → terminal states |
| Generation | Validating | All lessons processed | Validating phase marker | Wait | Snapshot/events | Complete or partial |
| Generation | Complete | Every lesson valid | Success banner naming bound versions; all rows downloadable | Download each | Snapshot | F004/F005 later |
| Generation | Partial failure | Some lessons failed after retries | Failed rows with reasons; preserved rows clearly valid; scoped resume action | Resume eligible; download completed | `POST resume` | Re-dispatch same run |
| Generation | Capped failure | Model-call cap reached | Cap usage banner; completed lessons downloadable; recovery guidance (new version → new run) | Download completed; follow guidance | Snapshot | Owner decision |
| Generation | Superseded | Newer version confirmed | Superseded banner naming newer version; history preserved without current impression | View newer version entry | Snapshot | Start new run on new version |
| Generation | Terminal failure | Non-retryable final failure | Named failure class; completed lessons preserved and downloadable | Download completed | Snapshot | Teacher decision |
| Generation | Teacher-blocked (start) | Missing required versions | Explanation + link to prerequisite view | Go fix prerequisite | Start error | Retry start after |
| Narration | Streaming / stopped | Narration in flight / stopped | Incremental text with stop control / stopped note (run continues) | Stop narration | SSE token events | Narrative only |
| Global | Offline / SSE drop | Network loss | Reconnecting banner: remote work continues | Wait / reconnect | `Last-Event-ID` replay | Never duplicates work |
| Global | Permission denied | Non-owner or deleted resource | Safe not-found | Return to own projects | No disclosure | Project list |
| Global | Provider failure named | Outage/timeout/rate during run | Named error class + bounded-retry status | Wait (auto) / resume when eligible | Provider error events | Checkpoint resume |
| Download | Authorized / denied | Download click | File stream / safe denial without existence disclosure | Open or back | Authorized endpoint | Retry / report |

Assessed states: Initial, Loaded, Submitting (start/resume buttons loading + disabled), Disabled (start blocked with reason; resume disabled for terminal/superseded/complete), Unauthorized, Forbidden-as-not-found, Offline, Partial Failure, Superseded, Capped, Teacher-blocked.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Start generation | Enabled only with confirmed versions; shows bound version pair before submit | Idempotent same-version run return; teacher-blocked error without prerequisites | Button loading; focus to run status on ack | Server idempotent per project + bound versions |
| Duplicate start click | Second click during submit disabled | Same-version duplicate returns existing run | Button disabled while submitting | No duplicate run possible |
| Resume | Enabled only for eligible failures (partial/capped with incomplete lessons) | Rejects terminal/superseded/complete with explicit state error | Confirmation modal naming affected lessons | Re-dispatches SAME run id |
| Download | Enabled only for valid artifacts | Workspace-authorized stream; denial is non-disclosing | Direct; focus preserved | Artifact id immutable; repeat safe |
| Stop narration | Always available during stream | Server stop semantics (F001 pattern); run unaffected | Immediate visual stop | Idempotent stop |

Client validation never replaces server constraints; every governed transition is revalidated server-side.

## Frontend/Backend Contract

- Request/response: typed API client over the Spec's five endpoints (`/generation/start`, `/generation`, `/generation/events` SSE with `Last-Event-ID`, `/generation/resume`, `/lesson-plans/{id}/download`); JSON for commands/queries; SSE for progress and narration. Exact DTO field names and the SSE event envelope are frozen schema-first (Zod) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: Clerk session token attached by the shared API client; 401 -> sign-in redirect; 404 (ownership) -> safe not-found; download denial non-disclosing.
- Pagination: `N/A - bounded lists` (one run per bound version pair; lessons bounded by blueprint).
- Optimistic update/rollback: `N/A - authoritative server state governs run/artifact status; SSE events append only`.
- Version preconditions: start binds the current confirmed versions server-side; UI displays the bound pair; no client-side version guessing.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in with return path | Sign in | Return | Yes |
| 404 (ownership/not-found, incl. download denial) | Safe not-found | Back to project list | None disclosed | Yes |
| VALIDATION / REQUIREMENT (start without confirmed versions) | Explanation naming prerequisite + link | Go to blueprint view | Confirm versions | Yes |
| STALE_VERSION / CONFLICT (resume on non-eligible run) | State explanation naming current run state | Refresh view | Follow actual state | Yes |
| QUOTA_EXCEEDED (per-run cap) | Cap banner with usage and recovery guidance | Download completed; new-version guidance | Owner decision | Yes |
| PROVIDER_TRANSIENT | Named provider error class + bounded-retry indicator | Wait / resume when eligible | Checkpoint resume | Yes |
| PARTIAL_EXECUTION | Partial-failure summary with per-lesson reasons | Scoped resume | Resume path | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

Errors never collapse into one vague toast; mapping follows `docs/API.md` taxonomy and `docs/UX.md` state principles.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full generation view: phase tracker, complete per-lesson list with statuses and actions, narration stream, outcome banners side-aware | Full context nav; keyboard accelerators | Dense progress layout; no horizontal scroll |
| Reduced <1024px | Read-only monitoring first: run status, phase, per-lesson status summary, outcome banner, and downloads preserved (UX.md responsive mandate) | Start generation and scoped resume replaced by desktop-required notice naming the task | Single reading sequence |
| Reduced <1024px, structured tasks | Attempting start/resume | Explicit desktop-required notice | No degraded action surfaces |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md rule that small screens preserve task status, recovery information, and downloads while deferring structured actions.

## Accessibility

- Semantic structure/labels: generation landmarks reuse the workspace shell; the per-lesson list is a labelled status list (lesson heading + state text); the phase tracker is a labelled progress region; cap usage is text, not color-only.
- Keyboard and focus order/recovery: start, resume (modal), download, and stop-narration are keyboard reachable; the resume modal traps focus and returns to the trigger; on outcome arrival (complete/partial/capped/superseded/terminal) focus moves to the outcome banner; per-lesson failure reasons reachable in order.
- Live announcements: phase changes, per-lesson completions, and terminal outcomes announced via polite live region in throttled semantic batches (never per SSE event); narration text announced in batches (shared conversation region behavior).
- Contrast/non-color cues: per-lesson states pair text labels with markers (never color alone); superseded vs complete distinguished in language and treatment; token set >=4.5:1 body / >=3:1 components.
- Motion/reduced motion: progress indication must not depend on animation; streaming caret honors reduced-motion.
- Touch targets >=24px in reduced layout.
- Verification approach: automated checks plus manual keyboard/focus pass for start → leave/return → partial failure → resume → download and the superseded path; recorded in Test Design evidence.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, inputs, modals, alerts, status markers, disclosure, skeleton/empty, phase tracker, navigation item | F001/F002 implementations of DESIGN_SYSTEM contracts | Reuse | All required variants exist | None |
| Shared conversation region | F002 shared component (D-CONVO) | Reuse (third consumer, D-NARR) | Narration has identical stop/trace semantics | None |
| Per-lesson progress list | Status marker + list composition | Compose Feature-local; promote with F004/F005 evidence | Decks/exercises will repeat per-lesson artifact patterns | Deferred with trigger |
| Outcome banners (partial/capped/superseded/terminal) | Alert variants + status marker composition | Compose Feature-local | First long-run outcome surfaces; F007 deepens supersession views | Deferred with trigger |
| Reconnect banner | F001 offline pattern | Reuse | Same semantics (remote continues, no duplicate) | None |

No new tokens; no new visual language; statuses use the shared draft/confirmed/waiting/stale/superseded status language from `docs/DESIGN_SYSTEM.md`.

## UI Acceptance Links

- AC-001 complete artifact set: artifact list + complete banner + download
- AC-002 idempotent start: duplicate-start behavior in Forms table
- AC-003 fast ack: start panel + queued state
- AC-004 progress visibility: phase tracker + per-lesson list (D-PROG)
- AC-005 transient failure resume: partial-failure rows + scoped resume
- AC-006 worker crash recovery: snapshot reconnect + resume path
- AC-007 cap: cap banner + usage + recovery guidance
- AC-008 supersession: superseded banner naming newer version
- AC-009 SSE replay: reconnect banner + Last-Event-ID (D-RECN)
- AC-010 narration stop: D-NARR stop control
- AC-011 partial visibility: per-lesson outcomes with reasons + resume
- AC-012 authorized download: download rows + non-disclosing denial
- AC-013 trace: evidence link on run outcomes (F006 deepens)
- AC-014 structural validation: valid-artifact status semantics
- AC-015 deletion: no F003 UI surface; deletion behavior owned by account/project flows
- AC-016 language mode: start panel names the bound language mode

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact SSE event envelope and DTO field names | Non-critical | Implementation assignee | Frozen schema-first (Zod) in the first implementation task within Spec semantics; behavior fixed by Spec D4 | RESOLVED |
| UIQ-002 | Cap default value display precision (calls used vs lessons affected) | Non-critical | Implementation assignee | Follows settings value chosen in Implementation Plan; UI renders authoritative usage numbers only | RESOLVED |
| UIQ-003 | Promotion of per-lesson progress/outcome patterns to Design System | Non-critical | Design System owner | Deferred with triggers (F004/F005 evidence) recorded in reuse table | RESOLVED (defer with trigger) |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, and the complete User Flow are explicit. | YES | User Goal and Flow incl. resume, reconnect, outcome, error paths, cancel/back |
| UR-02 | Each affected Page, Screen, and Component has an explicit responsibility. | YES | Responsibilities table, 7 surfaces |
| UR-03 | The UI State Matrix covers applicable states. | YES | 16-row matrix + assessed-state paragraph covering queued/generating/partial/capped/superseded/terminal/blocked/offline |
| UR-04 | Permission, validation, duplicate submit, cancel, back, and recovery are explicit. | YES | Forms table (duplicate protection), permission rows, safe-leave semantics |
| UR-05 | Frontend/Backend contract and error mapping are explicit. | YES | Contract section + 8-row error mapping over the five Spec endpoints |
| UR-06 | Responsive behavior is verifiable. | YES | 1024px table: monitoring + downloads preserved; start/resume desktop-required |
| UR-07 | Accessibility behavior is verifiable. | YES | A11y section with focus/live-region/contrast/reduced-motion behaviors + verification approach |
| UR-08 | Existing components and Design System checked with explicit reuse/extension decisions. | YES | Reuse table; conversation region third consumer; two deferred promotions with triggers |
| UR-09 | UI Acceptance linked to `AC-*`. | YES | All 16 ACs mapped to surfaces |
| UR-10 | No Critical UI Open Question `OPEN`/`DEFERRED`. | YES | All three UIQs resolved or deferred-with-trigger (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (see Spec Gate Record) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `4ccc4ef` + this artifact `ux-ui-f003-r1` @ `43f93abc6ed3`
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `193e90d10b68`
- Validated UX/UI revision: `ux-ui-f003-r1` @ `43f93abc6ed3`
- Validated at: 2026-08-29
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-29
- Approval scope: F003 UX/UI refinement at `ux-ui-f003-r1`

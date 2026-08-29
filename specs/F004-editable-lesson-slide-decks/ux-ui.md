# Feature UX/UI: F004 Editable Lesson Slide Decks

## Metadata

- Spec/Issue: `specs/F004-editable-lesson-slide-decks/spec.md` / [GitHub Issue #8](https://github.com/MaoyuanYang/LessonCanvas/issues/8)
- Validated Spec revision: `SPEC READY` PASS, content hash `b913da61ec40`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `b727734`
- UX/UI artifact revision/change-log ID: `ux-ui-f004-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: F003 generation surfaces (`specs/F003-recoverable-unit-lesson-plans/ux-ui.md` D-GEN/D-PROG/D-NARR/D-ART/D-RECN), shared conversation region (F002 D-CONVO), DESIGN_SYSTEM reuse table deferring per-lesson progress list and outcome banners with F004/F005 as promotion trigger

### UI-level decisions (2026-08-29, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-DECKGEN | Deck-generation placement | Sixth project-context view `课件生成` in the existing workspace shell, directly after `教案生成`; unavailable state names the prerequisite chain (blueprint confirmed AND lesson-plan run complete for the current versions, Spec D3); no new top-level navigation. The entry always shows the bound brief/blueprint version pair and language mode before start. |
| D-DECKPROG | Progress surface | Same pattern as F003 D-PROG: one phase tracker (queued → generating → validating → terminal states) plus a per-lesson deck progress list (index, lesson title, per-lesson state) fed by SSE from the authoritative event log; the pollable snapshot is the fallback and the tie-breaker. Per-lesson rows never expose internal step names beyond the Spec's per-lesson states. |
| D-DECKNARR | Narration reuse | The shared conversation region (F002 D-CONVO; third consumer in F003 D-NARR) becomes the fourth consumer for deck-generation narration; narration keeps its own stop control; stopping narration never affects the run (AC-010). |
| D-DECKART | Artifact list with structure summary | Per-lesson deck rows inside `课件生成`: status marker, structure summary (slide count + validation status, Spec D9), download action when complete and valid, per-lesson failure reason when failed, scoped resume action for eligible failures; superseded runs keep decks visible under a superseded banner without a download-as-current impression. No in-browser slide preview exists anywhere. |
| D-DECKRECN | Reconnect behavior | Same pattern as F003 D-RECN: SSE drop shows a reconnecting banner stating remote work continues; reconnect replays missed events via `Last-Event-ID`; leaving the view never cancels the run; returning reconnects to the authoritative snapshot without creating a replacement run. |
| D-DECKDS | Design System promotion | F004 is the recorded promotion trigger (F003 reuse table): promote the per-lesson artifact progress list and the run-outcome banner compositions from F003 feature-local code to documented shared variants in `docs/DESIGN_SYSTEM.md`. Implementation extracts shared components consumed by both `教案生成` and `课件生成` (behavior-preserving refactor of the F003 panel); F005 will consume the same variants. |

These are interface refinements within Spec behavior (D1, D3, D4, D9); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: start all-lesson deck generation from the completed lesson plans of the current confirmed version, leave or monitor safely, understand partial failures, resume eligible work, and download every completed editable PPTX deck
- Entry point: workspace shell -> `课件生成` context view (enabled once the lesson-plan run for the current confirmed versions is complete)
- Preconditions: valid Clerk session; confirmed brief and blueprint versions; a complete lesson-plan run bound to those versions (Spec D3)

```text
Workspace (lesson-plan run complete for current versions) -> 课件生成 view
  -> Review bound versions (brief vX + blueprint vY), language mode, lesson count -> Start deck generation
       (idempotent: an existing same-version deck run is returned and shown)
  -> Acknowledged immediately: queued run snapshot -> teacher may leave safely
  -> Monitor (optional): phase tracker + per-lesson deck states + narration (stoppable)
  -> Outcomes:
       complete -> every lesson row shows structure summary + authorized download
       partial_failure -> failed decks show reasons + scoped resume action
       capped_failure -> cap usage shown; completed decks downloadable; recovery guidance
       superseded -> banner names the newer confirmed version; run history preserved
       terminal_failure -> named final failure; completed decks still downloadable
Resume path (eligible failures):
  -> scoped resume re-dispatches the SAME run -> only failed/incomplete lessons run
Reconnect path:
  -> SSE drop -> reconnecting banner -> replay from Last-Event-ID -> snapshot remains pollable
Error paths:
  -> teacher_blocked (no confirmed versions): explanation + link to 单元蓝图
  -> teacher_blocked (lesson plans missing or incomplete): explanation + link to 教案生成
  -> provider failure: named error class + bounded-retry status, state preserved
  -> unauthorized/unknown project: safe not-found -> back to own project list
Cancel/back: leaving preserves the run and all completed decks; back never cancels; no run cancel action exists in F004.
```

- Success exit: run `complete`; every lesson row shows a valid deck with structure summary and download; the view names the bound versions the decks belong to
- Cancel/back behavior: free navigation away and back; return reconnects to authoritative state
- Permission denied/recovery: safe not-found (no existence disclosure) with one action back to the teacher's project list

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Workspace shell (extended) | Add `课件生成` context view with phase and unavailable reason naming the prerequisite chain | Lesson-plan run state for current versions | Switch context view | Hosts deck surfaces | Navigation item, Status marker |
| Deck panel — start | Show bound brief/blueprint version pair, language mode, lesson count, completed-plan prerequisite; start deck generation; explain idempotent duplicate handling | `GET /decks/generation`, `POST /decks/generation/start` | Start | Creates/returns deck run | Button, Status marker, version citation |
| Deck panel — progress | Phase tracker; per-lesson deck list; cap usage indicator; narration stream with stop | `GET /decks/generation/events` (SSE), `GET /decks/generation` snapshot | Stop narration; leave freely | Live run state | Phase tracker, shared artifact progress list (D-DECKDS), shared conversation region (D-DECKNARR) |
| Deck artifact list (D-DECKART) | Per-lesson outcomes: complete/valid with slide count, failed with reason, pending; download; scoped resume for eligible failures | `GET /decks/generation` snapshot, `GET /slide-decks/{id}/download` | Download, resume | Authorized PPTX delivery / re-dispatch | Status marker, Button, disclosure (reason/summary) |
| Outcome banners | complete / partial_failure / capped_failure / superseded / terminal_failure summaries with next actions | Run status in snapshot | Follow offered action | Recovery paths | Shared run-outcome banner (D-DECKDS) |
| Reconnect banner (D-DECKRECN) | Explain SSE drop and remote continuation; auto-reconnect with replay | SSE connection state | Wait / manual reconnect | Restored progress | Alert (offline), existing offline pattern |
| Safe not-found | Non-disclosing terminal for unauthorized/unknown resources | Route guard | Return to project list | -> Project list | Empty state, Button |

Component responsibility rule unchanged: networking/error normalization lives in the shared API layer; no component owns backend state transitions; SSE events update client projections only.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Deck generation | Unavailable (blueprint not confirmed) | No confirmed versions | Explanation naming the blueprint gate + link | Go to blueprint view | Blueprint state | Confirm blueprint |
| Deck generation | Unavailable (plans missing/incomplete) | Lesson-plan run for current versions absent or not `complete` | Explanation naming the lesson-plan prerequisite + link to 教案生成 (Spec D3) | Go to 教案生成 | Lesson-plan run state | Complete lesson plans |
| Deck generation | Empty (no run yet) | Prerequisites met, no deck run | Start panel with bound versions and lesson count | Start deck generation | `POST decks/start` | Run created/returned |
| Deck generation | Loading | Entry/refresh | Skeleton preserving layout | Wait | Request in flight | Success or error |
| Deck generation | Queued | Run created, work not started | Queued phase marker; safe-leave note | Leave freely | Snapshot/events | Generating |
| Deck generation | Generating | Active run | Phase tracker; per-lesson rows pending→drafting→rendering→validating→complete; narration stream | Stop narration; leave | SSE + snapshot | Validating → terminal states |
| Deck generation | Validating | All lessons processed | Validating phase marker | Wait | Snapshot/events | Complete or partial |
| Deck generation | Complete | Every deck valid | Success banner naming bound versions; all rows show slide count + download | Download each | Snapshot | F005 later |
| Deck generation | Partial failure | Some decks failed after retries | Failed rows with reasons; preserved rows clearly valid; scoped resume action | Resume eligible; download completed | `POST decks/resume` | Re-dispatch same run |
| Deck generation | Capped failure | Model-call cap reached | Cap usage banner; completed decks downloadable; recovery guidance (new version → new run) | Download completed; follow guidance | Snapshot | Owner decision |
| Deck generation | Superseded | Newer version confirmed | Superseded banner naming newer version; history preserved without current impression | View newer version entry | Snapshot | Start new run on new version |
| Deck generation | Terminal failure | Non-retryable final failure | Named failure class; completed decks preserved and downloadable | Download completed | Snapshot | Teacher decision |
| Deck generation | Teacher-blocked (start) | Missing prerequisite at submit | Explanation + link to the failed prerequisite view | Go fix prerequisite | Start error | Retry start after |
| Narration | Streaming / stopped | Narration in flight / stopped | Incremental text with stop control / stopped note (run continues) | Stop narration | SSE events | Narrative only |
| Global | Offline / SSE drop | Network loss | Reconnecting banner: remote work continues | Wait / reconnect | `Last-Event-ID` replay | Never duplicates work |
| Global | Permission denied | Non-owner or deleted resource | Safe not-found | Return to own projects | No disclosure | Project list |
| Download | Authorized / denied | Download click | File stream / safe denial without existence disclosure | Open or back | Authorized endpoint | Retry / report |

Assessed states: Initial, Loaded, Submitting (start/resume buttons loading + disabled), Disabled (start blocked with reason; resume disabled for terminal/superseded/complete), Unauthorized, Forbidden-as-not-found, Offline, Partial Failure, Superseded, Capped, Teacher-blocked (both prerequisite kinds).

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Start deck generation | Enabled only with confirmed versions AND complete lesson-plan run; shows bound version pair before submit | Idempotent same-version deck run return; teacher-blocked error naming the failed prerequisite | Button loading; focus to run status on ack | Server idempotent per project + bound versions + artifact kind |
| Duplicate start click | Second click during submit disabled | Same-version duplicate returns existing deck run | Button disabled while submitting | No duplicate run possible |
| Resume | Enabled only for eligible failures (partial/capped with incomplete lessons) | Rejects terminal/superseded/complete with explicit state error | Confirmation modal naming affected lessons | Re-dispatches SAME run id |
| Download | Enabled only for valid decks | Workspace-authorized stream; denial is non-disclosing | Direct; focus preserved | Artifact id immutable; repeat safe |
| Stop narration | Always available during stream | Server stop semantics (F001 pattern); run unaffected | Immediate visual stop | Idempotent stop |

Client validation never replaces server constraints; every governed transition is revalidated server-side.

## Frontend/Backend Contract

- Request/response: typed API client over the Spec's five deck endpoints (`/decks/generation/start`, `/decks/generation`, `/decks/generation/events` SSE with `Last-Event-ID`, `/decks/generation/resume`, `/slide-decks/{id}/download`); JSON for commands/queries; SSE for progress and narration. Exact DTO field names and the SSE event envelope are frozen schema-first (Zod) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: Clerk session token attached by the shared API client; 401 -> sign-in redirect; 404 (ownership) -> safe not-found; download denial non-disclosing.
- Pagination: `N/A - bounded lists` (one deck run per bound version pair; lessons bounded by blueprint).
- Optimistic update/rollback: `N/A - authoritative server state governs run/artifact status; SSE events append only`.
- Version preconditions: start binds the current confirmed versions server-side; UI displays the bound pair; no client-side version guessing.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in with return path | Sign in | Return | Yes |
| 404 (ownership/not-found, incl. download denial) | Safe not-found | Back to project list | None disclosed | Yes |
| REQUIREMENT (start without confirmed versions) | Explanation naming blueprint gate + link | Go to 单元蓝图 | Confirm versions | Yes |
| REQUIREMENT (start without complete lesson plans) | Explanation naming lesson-plan prerequisite + link | Go to 教案生成 | Complete lesson plans first | Yes |
| STALE_VERSION / CONFLICT (resume on non-eligible run) | State explanation naming current run state | Refresh view | Follow actual state | Yes |
| QUOTA_EXCEEDED (per-run cap) | Cap banner with usage and recovery guidance | Download completed; new-version guidance | Owner decision | Yes |
| PROVIDER_TRANSIENT | Named provider error class + bounded-retry indicator | Wait / resume when eligible | Checkpoint resume | Yes |
| PARTIAL_EXECUTION | Partial-failure summary with per-lesson reasons | Scoped resume | Resume path | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

Errors never collapse into one vague toast; mapping follows `docs/API.md` taxonomy and `docs/UX.md` state principles.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full deck view: phase tracker, complete per-lesson list with statuses, structure summaries, and actions, narration stream, outcome banners side-aware | Full context nav; keyboard accelerators | Dense progress layout; no horizontal scroll |
| Reduced <1024px | Read-only monitoring first: run status, phase, per-lesson status summary with slide counts, outcome banner, and downloads preserved (UX.md responsive mandate) | Start deck generation and scoped resume replaced by desktop-required notice naming the task | Single reading sequence |
| Reduced <1024px, structured tasks | Attempting start/resume | Explicit desktop-required notice | No degraded action surfaces |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md rule that small screens preserve task status, recovery information, and downloads while deferring structured actions.

## Accessibility

- Semantic structure/labels: deck surfaces reuse the workspace shell landmarks; the per-lesson deck list is a labelled status list (lesson heading + state text + slide-count text); the phase tracker is a labelled progress region; cap usage is text, not color-only.
- Keyboard and focus order/recovery: start, resume (modal), download, and stop-narration are keyboard reachable; the resume modal traps focus and returns to the trigger; on outcome arrival (complete/partial/capped/superseded/terminal) focus moves to the outcome banner; per-lesson failure reasons reachable in order.
- Live announcements: phase changes, per-lesson deck completions, and terminal outcomes announced via polite live region in throttled semantic batches (never per SSE event); narration text announced in batches (shared conversation region behavior).
- Contrast/non-color cues: per-lesson states pair text labels with markers (never color alone); superseded vs complete distinguished in language and treatment; token set >=4.5:1 body / >=3:1 components.
- Motion/reduced motion: progress indication must not depend on animation; streaming caret honors reduced-motion.
- Touch targets >=24px in reduced layout.
- Verification approach: automated checks plus manual/keyboard pass for prerequisite-gated start → leave/return → partial failure → resume → download and the superseded path; recorded in Test Design evidence.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, inputs, modals, alerts, status markers, disclosure, skeleton/empty, phase tracker, navigation item | F001/F002/F003 implementations of DESIGN_SYSTEM contracts | Reuse | All required variants exist | None |
| Shared conversation region | F002 shared component (D-CONVO) | Reuse (fourth consumer, D-DECKNARR) | Narration has identical stop/trace semantics | None |
| Per-lesson artifact progress list | F003 feature-local composition | Extend — promote to documented shared variant (D-DECKDS) | F004 is the recorded trigger; second consumer now, F005 third | `docs/DESIGN_SYSTEM.md` gains the shared variant at documentation sync; F003 panel refactored to consume it |
| Run-outcome banners (partial/capped/superseded/terminal/complete) | F003 feature-local composition | Extend — promote to documented shared variant (D-DECKDS) | Same trigger; identical state language | Same as above |
| Reconnect banner | F001 offline pattern | Reuse | Same semantics (remote continues, no duplicate) | None |

No new tokens; no new visual language; statuses use the shared draft/confirmed/waiting/stale/superseded status language from `docs/DESIGN_SYSTEM.md`.

## UI Acceptance Links

- AC-001 complete deck set: deck artifact list + complete banner + download
- AC-002 idempotent start: duplicate-start behavior in Forms table
- AC-003 fast ack: start panel + queued state
- AC-004 progress + structure summary visibility: phase tracker + per-lesson deck list (D-DECKPROG, D-DECKART)
- AC-005 transient failure resume: partial-failure rows + scoped resume
- AC-006 worker crash recovery: snapshot reconnect + resume path
- AC-007 cap: cap banner + usage + recovery guidance
- AC-008 supersession: superseded banner naming newer version
- AC-009 SSE replay: reconnect banner + Last-Event-ID (D-DECKRECN)
- AC-010 narration stop: D-DECKNARR stop control
- AC-011 partial visibility: per-lesson outcomes with reasons + resume
- AC-012 authorized download: download rows + non-disclosing denial
- AC-013 trace: evidence link on run outcomes (F006 deepens)
- AC-014 structural validation + editability: valid-deck status semantics with slide count
- AC-015 deletion: no F004 UI surface; deletion behavior owned by account/project flows
- AC-016 language mode: start panel names the bound language mode
- AC-017 prerequisite gate: unavailable states for both prerequisite kinds + teacher-blocked start error
- AC-018 lesson-plan context in trace: no additional UI surface beyond AC-013 evidence link (F006 deepens)

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact SSE event envelope and DTO field names for deck endpoints | Non-critical | Implementation assignee | Frozen schema-first (Zod) in the first implementation task within Spec semantics; behavior fixed by Spec D4 | RESOLVED |
| UIQ-002 | Structure-summary precision (slide count only vs per-section presence) | Non-critical | Implementation assignee | Slide count + validation status in F004 (Spec D9); per-section presence stays in validation detail on demand; richer summary only if teacher review asks | RESOLVED |
| UIQ-003 | Scope of the F003 panel refactor for D-DECKDS promotion | Non-critical | Implementation assignee | Behavior-preserving extraction only (same states, copy, and semantics); any visual or behavioral change to F003 surfaces would be a Design Change | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, and the complete User Flow are explicit. | YES | User Goal and Flow incl. both prerequisite kinds, resume, reconnect, outcome, error paths, cancel/back |
| UR-02 | Each affected Page, Screen, and Component has an explicit responsibility. | YES | Responsibilities table, 7 surfaces |
| UR-03 | The UI State Matrix covers applicable states. | YES | 16-row matrix + assessed-state paragraph covering both unavailable kinds, queued/generating/partial/capped/superseded/terminal/blocked/offline |
| UR-04 | Permission, validation, duplicate submit, cancel, back, and recovery are explicit. | YES | Forms table (duplicate protection), permission rows, safe-leave semantics |
| UR-05 | Frontend/Backend contract and error mapping are explicit. | YES | Contract section + 9-row error mapping over the five Spec deck endpoints |
| UR-06 | Responsive behavior is verifiable. | YES | 1024px table: monitoring + structure summaries + downloads preserved; start/resume desktop-required |
| UR-07 | Accessibility behavior is verifiable. | YES | A11y section with focus/live-region/contrast/reduced-motion behaviors + verification approach |
| UR-08 | Existing components and Design System checked with explicit reuse/extension decisions. | YES | Reuse table incl. D-DECKDS promotion of the two deferred compositions with their recorded F004 trigger |
| UR-09 | UI Acceptance linked to `AC-*`. | YES | All 18 ACs mapped to surfaces |
| UR-10 | No Critical UI Open Question `OPEN`/`DEFERRED`. | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (see Spec Gate Record) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `b727734` + this artifact `ux-ui-f004-r1` @ `05e5748c9a4d`
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `b913da61ec40`
- Validated UX/UI revision: `ux-ui-f004-r1` @ `05e5748c9a4d`
- Validated at: 2026-08-29
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-29
- Approval scope: F004 UX/UI refinement at `ux-ui-f004-r1`

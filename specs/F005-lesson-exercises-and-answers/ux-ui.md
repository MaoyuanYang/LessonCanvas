# Feature UX/UI: F005 Lesson Exercises and Answers

## Metadata

- Spec/Issue: `specs/F005-lesson-exercises-and-answers/spec.md` / [GitHub Issue #10](https://github.com/MaoyuanYang/LessonCanvas/issues/10)
- Validated Spec revision: `SPEC READY` PASS, content hash `41b391751a33` (Gate Record appended after validation)
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 123523a`
- UX/UI artifact revision/change-log ID: `ux-ui-f005-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: F004 deck surfaces (`specs/F004-editable-lesson-slide-decks/ux-ui.md` D-DECKGEN/D-DECKPROG/D-DECKNARR/D-DECKART/D-DECKRECN), shared artifact-run surfaces promoted with F004 (D-DECKDS: `ArtifactProgressList`, `RunOutcomeBanners`, `NarrationRegion`, `ReconnectBanner`, status label maps) with F005 recorded as the next consumer, shared conversation region (F002 D-CONVO)

### UI-level decisions (2026-08-31, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-EXGEN | Exercise-generation placement | Seventh project-context view `练习与答案` in the existing workspace shell, directly after `课件生成`; unavailable state names the prerequisite chain (blueprint confirmed AND lesson-plan run complete for the current versions, Spec D3); no new top-level navigation. The entry always shows the bound brief/blueprint version pair and language mode before start. Slide-deck completion is never shown as a requirement. |
| D-EXDIFF | Difficulty selection surface | On the start surface (no run yet), a required radio group of the three Spec D9 tiers with zh-Hans labels `基础` / `巩固` / `进阶` and one-line descriptions; no default selection — the teacher makes an explicit decision; client validation names the field before submit and the server revalidates (input-validation error listing the tiers). Once a run exists, the selector is replaced by the run's recorded tier shown in the bound-versions line and every snapshot; a duplicate start never re-opens the choice (Spec D9 immutability). |
| D-EXPROG | Progress surface | Same pattern as F003 D-PROG / F004 D-DECKPROG: one phase tracker (queued → generating → validating → terminal states) plus a per-lesson pair progress list (index, lesson title, per-lesson state) fed by SSE from the authoritative event log; the pollable snapshot is the fallback and the tie-breaker. Per-lesson rows never expose internal step names beyond the Spec's per-lesson states. |
| D-EXNARR | Narration reuse | The shared conversation region (F002 D-CONVO; fourth consumer in F004 D-DECKNARR) becomes the fifth consumer for exercise-generation narration; narration keeps its own stop control; stopping narration never affects the run (AC-010). |
| D-EXART | Pair list with pair summary and dual download | Per-lesson pair rows inside `练习与答案`: status marker, pair summary (item count + category count + validation status, Spec D1), two distinct download actions when complete and valid (`下载练习` and `下载答案`, each opening the corresponding authorized DOCX), per-lesson failure reason when failed, scoped resume action for eligible failures; superseded runs keep pairs visible under a superseded banner without a download-as-current impression. No in-browser DOCX preview or editing exists anywhere. |
| D-EXRECN | Reconnect behavior | Same pattern as F003 D-RECN / F004 D-DECKRECN: SSE drop shows a reconnecting banner stating remote work continues; reconnect replays missed events via `Last-Event-ID`; leaving the view never cancels the run; returning reconnects to the authoritative snapshot without creating a replacement run. |

No Design System promotion decision is needed: F005 is the recorded third consumer of the artifact-run shared variants promoted by F004 (D-DECKDS). The tier radio group reuses the existing form/radio contracts; no new tokens or variants.

These are interface refinements within Spec behavior (D1, D3, D4, D7, D9); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: start all-lesson exercise and answer generation at a chosen difficulty from the completed lesson plans of the current confirmed version, leave or monitor safely, understand partial failures, resume eligible work, and download every completed editable DOCX pair
- Entry point: workspace shell -> `练习与答案` context view (enabled once the lesson-plan run for the current confirmed versions is complete)
- Preconditions: valid Clerk session; confirmed brief and blueprint versions; a complete lesson-plan run bound to those versions (Spec D3)

```text
Workspace (lesson-plan run complete for current versions) -> 练习与答案 view
  -> Review bound versions (brief vX + blueprint vY), language mode, lesson count
  -> Select difficulty tier (基础 / 巩固 / 进阶, required, no default) -> Start exercise generation
       (idempotent: an existing same-version exercise run is returned and shown with its recorded tier)
  -> Acknowledged immediately: queued run snapshot -> teacher may leave safely
  -> Monitor (optional): phase tracker + per-lesson pair states + narration (stoppable)
  -> Outcomes:
       complete -> every lesson row shows pair summary + authorized 练习/答案 downloads
       partial_failure -> failed pairs show reasons + scoped resume action
       capped_failure -> cap usage shown; completed pairs downloadable; recovery guidance
       superseded -> banner names the newer confirmed version; run history preserved
       terminal_failure -> named final failure; completed pairs still downloadable
Resume path (eligible failures):
  -> scoped resume re-dispatches the SAME run -> only failed/incomplete lessons run
Reconnect path:
  -> SSE drop -> reconnecting banner -> replay from Last-Event-ID -> snapshot remains pollable
Error paths:
  -> teacher_blocked (no confirmed versions): explanation + link to 单元蓝图
  -> teacher_blocked (lesson plans missing or incomplete): explanation + link to 教案生成
  -> input validation (no tier selected): field-level message naming the required choice
  -> provider failure: named error class + bounded-retry status, state preserved
  -> unauthorized/unknown project: safe not-found -> back to own project list
Cancel/back: leaving preserves the run and all completed pairs; back never cancels; no run cancel action exists in F005.
```

- Success exit: run `complete`; every lesson row shows a valid pair with summary and both downloads; the view names the bound versions and the recorded difficulty tier
- Cancel/back behavior: free navigation away and back; return reconnects to authoritative state
- Permission denied/recovery: safe not-found (no existence disclosure) with one action back to the teacher's project list

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Workspace shell (extended) | Add `练习与答案` context view with phase and unavailable reason naming the prerequisite chain | Lesson-plan run state for current versions | Switch context view | Hosts exercise surfaces | Navigation item, Status marker |
| Exercise panel — start | Show bound brief/blueprint version pair, language mode, lesson count, completed-plan prerequisite; required difficulty radio group (D-EXDIFF); start exercise generation; explain idempotent duplicate handling | `GET /exercises/generation`, `POST /exercises/generation/start` | Select tier; start | Creates/returns exercise run | Button, Status marker, version citation, radio group |
| Exercise panel — progress | Phase tracker; per-lesson pair list; cap usage indicator; narration stream with stop | `GET /exercises/generation/events` (SSE), `GET /exercises/generation` snapshot | Stop narration; leave freely | Live run state | Phase tracker, shared artifact progress list, shared conversation region (D-EXNARR) |
| Pair artifact list (D-EXART) | Per-lesson outcomes: complete/valid with item and category counts, failed with reason, pending; dual download (练习/答案); scoped resume for eligible failures | `GET /exercises/generation` snapshot, `GET /exercises/{id}/download?file=...` | Download exercise; download answer; resume | Authorized DOCX delivery / re-dispatch | Status marker, Button, disclosure (reason/summary) |
| Outcome banners | complete / partial_failure / capped_failure / superseded / terminal_failure summaries with next actions | Run status in snapshot | Follow offered action | Recovery paths | Shared run-outcome banner |
| Reconnect banner (D-EXRECN) | Explain SSE drop and remote continuation; auto-reconnect with replay | SSE connection state | Wait / manual reconnect | Restored progress | Alert (offline), existing offline pattern |
| Safe not-found | Non-disclosing terminal for unauthorized/unknown resources | Route guard | Return to project list | -> Project list | Empty state, Button |

Component responsibility rule unchanged: networking/error normalization lives in the shared API layer; no component owns backend state transitions; SSE events update client projections only.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Exercise generation | Unavailable (blueprint not confirmed) | No confirmed versions | Explanation naming the blueprint gate + link | Go to blueprint view | Blueprint state | Confirm blueprint |
| Exercise generation | Unavailable (plans missing/incomplete) | Lesson-plan run for current versions absent or not `complete` | Explanation naming the lesson-plan prerequisite + link to 教案生成 (Spec D3) | Go to 教案生成 | Lesson-plan run state | Complete lesson plans |
| Exercise generation | Empty (no run yet) | Prerequisites met, no exercise run | Start panel with bound versions, lesson count, and tier radio group (no default) | Select tier; start | `POST exercises/start` | Run created/returned |
| Exercise generation | Loading | Entry/refresh | Skeleton preserving layout | Wait | Request in flight | Success or error |
| Exercise generation | Queued | Run created, work not started | Queued phase marker; recorded tier shown; safe-leave note | Leave freely | Snapshot/events | Generating |
| Exercise generation | Generating | Active run | Phase tracker; per-lesson rows pending→drafting→rendering→validating→complete; narration stream | Stop narration; leave | SSE + snapshot | Validating → terminal states |
| Exercise generation | Validating | All lessons processed | Validating phase marker | Wait | Snapshot/events | Complete or partial |
| Exercise generation | Complete | Every pair valid | Success banner naming bound versions and tier; all rows show pair summary + both downloads | Download each file | Snapshot | F006+ later |
| Exercise generation | Partial failure | Some pairs failed after retries | Failed rows with reasons; preserved rows clearly valid; scoped resume action | Resume eligible; download completed | `POST exercises/resume` | Re-dispatch same run |
| Exercise generation | Capped failure | Model-call cap reached | Cap usage banner; completed pairs downloadable; recovery guidance (new version → new run with new tier choice) | Download completed; follow guidance | Snapshot | Owner decision |
| Exercise generation | Superseded | Newer version confirmed | Superseded banner naming newer version; history preserved without current impression | View newer version entry | Snapshot | Start new run on new version |
| Exercise generation | Terminal failure | Non-retryable final failure | Named failure class; completed pairs preserved and downloadable | Download completed | Snapshot | Teacher decision |
| Exercise generation | Teacher-blocked (start) | Missing prerequisite at submit | Explanation + link to the failed prerequisite view | Go fix prerequisite | Start error | Retry start after |
| Exercise generation | Validation error (no tier) | Submit without tier selection | Field-level message naming the required tier choice; focus to the radio group | Select and retry | Client + server validation | Start proceeds |
| Narration | Streaming / stopped | Narration in flight / stopped | Incremental text with stop control / stopped note (run continues) | Stop narration | SSE events | Narrative only |
| Global | Offline / SSE drop | Network loss | Reconnecting banner: remote work continues | Wait / reconnect | `Last-Event-ID` replay | Never duplicates work |
| Global | Permission denied | Non-owner or deleted resource | Safe not-found | Return to own projects | No disclosure | Project list |
| Download (either file) | Authorized / denied / bad file param | Download click | File stream / safe denial without existence disclosure | Open or back | Authorized endpoint | Retry / report |

Assessed states: Initial, Loaded, Submitting (start/resume buttons loading + disabled), Disabled (start blocked with reason; resume disabled for terminal/superseded/complete), Unauthorized, Forbidden-as-not-found, Offline, Partial Failure, Superseded, Capped, Teacher-blocked (both prerequisite kinds), Input-validation (tier missing).

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Tier selection (D-EXDIFF) | Required radio group, no default; submit blocked with field message until chosen | Input-validation error listing the three accepted tiers | Field message inline; focus to radio group | Selection persisted only via run creation |
| Start exercise generation | Enabled only with confirmed versions AND complete lesson-plan run AND a chosen tier; shows bound version pair before submit | Idempotent same-version exercise run return (existing run wins, recorded tier shown); teacher-blocked error naming the failed prerequisite | Button loading; focus to run status on ack | Server idempotent per project + bound versions + artifact kind |
| Duplicate start click | Second click during submit disabled | Same-version duplicate returns existing exercise run with its recorded tier | Button disabled while submitting | No duplicate run possible; tier never overwritten |
| Resume | Enabled only for eligible failures (partial/capped with incomplete lessons) | Rejects terminal/superseded/complete with explicit state error | Confirmation modal naming affected lessons | Re-dispatches SAME run id |
| Download (exercise or answer) | Enabled only for valid pairs; the `file` parameter fixed per button | Workspace-authorized stream; denial is non-disclosing; invalid `file` parameter is a client contract bug surfaced as safe error | Direct; focus preserved | Artifact id immutable; repeat safe |
| Stop narration | Always available during stream | Server stop semantics (F001 pattern); run unaffected | Immediate visual stop | Idempotent stop |

Client validation never replaces server constraints; every governed transition is revalidated server-side.

## Frontend/Backend Contract

- Request/response: typed API client over the Spec's five exercise endpoints (`/exercises/generation/start` with required `difficulty` in the body, `/exercises/generation`, `/exercises/generation/events` SSE with `Last-Event-ID`, `/exercises/generation/resume`, `/exercises/{artifactId}/download?file=exercise|answer`); JSON for commands/queries; SSE for progress and narration. Exact DTO field names and the SSE event envelope are frozen schema-first (Zod) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: Clerk session token attached by the shared API client; 401 -> sign-in redirect; 404 (ownership) -> safe not-found; download denial non-disclosing.
- Pagination: `N/A - bounded lists` (one exercise run per bound version pair; lessons bounded by blueprint).
- Optimistic update/rollback: `N/A - authoritative server state governs run/artifact status; SSE events append only`.
- Version preconditions: start binds the current confirmed versions server-side; UI displays the bound pair and the recorded tier; no client-side version guessing.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in with return path | Sign in | Return | Yes |
| 404 (ownership/not-found, incl. download denial) | Safe not-found | Back to project list | None disclosed | Yes |
| REQUIREMENT (start without confirmed versions) | Explanation naming blueprint gate + link | Go to 单元蓝图 | Confirm versions | Yes |
| REQUIREMENT (start without complete lesson plans) | Explanation naming lesson-plan prerequisite + link | Go to 教案生成 | Complete lesson plans first | Yes |
| VALIDATION (missing/invalid tier) | Field-level message naming the three tiers | Select tier | Retry start | Yes |
| STALE_VERSION / CONFLICT (resume on non-eligible run) | State explanation naming current run state | Refresh view | Follow actual state | Yes |
| QUOTA_EXCEEDED (per-run cap) | Cap banner with usage and recovery guidance | Download completed; new-version guidance | Owner decision | Yes |
| PROVIDER_TRANSIENT | Named provider error class + bounded-retry indicator | Wait / resume when eligible | Checkpoint resume | Yes |
| PARTIAL_EXECUTION | Partial-failure summary with per-lesson reasons | Scoped resume | Resume path | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

Errors never collapse into one vague toast; mapping follows `docs/API.md` taxonomy and `docs/UX.md` state principles.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full exercise view: phase tracker, complete per-lesson pair list with statuses, pair summaries, and actions, narration stream, outcome banners side-aware | Full context nav; keyboard accelerators | Dense progress layout; no horizontal scroll |
| Reduced <1024px | Read-only monitoring first: run status, phase, recorded tier, per-lesson status summary with pair counts, outcome banner, and downloads preserved (UX.md responsive mandate) | Tier selection, start, and scoped resume replaced by desktop-required notice naming the task | Single reading sequence |
| Reduced <1024px, structured tasks | Attempting start/resume | Explicit desktop-required notice | No degraded action surfaces |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md rule that small screens preserve task status, recovery information, and downloads while deferring structured actions.

## Accessibility

- Semantic structure/labels: exercise surfaces reuse the workspace shell landmarks; the per-lesson pair list is a labelled status list (lesson heading + state text + pair-count text); the phase tracker is a labelled progress region; cap usage is text, not color-only; the tier radio group is a required fieldset with legend `难度档位`, per-option label + description, and an announced required state.
- Keyboard and focus order/recovery: tier selection, start, resume (modal), both download actions, and stop-narration are keyboard reachable; the resume modal traps focus and returns to the trigger; on outcome arrival (complete/partial/capped/superseded/terminal) focus moves to the outcome banner; per-lesson failure reasons reachable in order; the two download buttons carry distinct accessible names (`下载练习 DOCX` / `下载答案 DOCX`).
- Live announcements: phase changes, per-lesson pair completions, and terminal outcomes announced via polite live region in throttled semantic batches (never per SSE event); narration text announced in batches (shared conversation region behavior).
- Contrast/non-color cues: per-lesson states pair text labels with markers (never color alone); superseded vs complete distinguished in language and treatment; token set >=4.5:1 body / >=3:1 components.
- Motion/reduced motion: progress indication must not depend on animation; streaming caret honors reduced-motion.
- Touch targets >=24px in reduced layout.
- Verification approach: automated checks plus manual/keyboard pass for tier selection → prerequisite-gated start → leave/return → partial failure → resume → both downloads and the superseded path; recorded in Test Design evidence.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, inputs, modals, alerts, status markers, disclosure, skeleton/empty, phase tracker, navigation item | F001/F002/F003/F004 implementations of DESIGN_SYSTEM contracts | Reuse | All required variants exist | None |
| Shared artifact-run surfaces (`ArtifactProgressList`, `RunOutcomeBanners`, status label maps) | F004 promotion (D-DECKDS) | Reuse (third consumer; `noun` parameterized to 练习/答案 wording) | Recorded as next consumer in `docs/DESIGN_SYSTEM.md` | None (usage noted at documentation sync) |
| Shared conversation region | F002 shared component (D-CONVO) | Reuse (fifth consumer, D-EXNARR) | Narration has identical stop/trace semantics | None |
| Tier radio group | Existing form/radio contracts | Reuse (fieldset + legend + labelled options) | Standard required-choice form pattern | None |
| Reconnect banner | F001 offline pattern | Reuse | Same semantics (remote continues, no duplicate) | None |

No new tokens; no new visual language; statuses use the shared draft/confirmed/waiting/stale/superseded status language from `docs/DESIGN_SYSTEM.md`.

## UI Acceptance Links

- AC-001 complete pair set: pair artifact list + complete banner + dual download
- AC-002 idempotent start: duplicate-start behavior in Forms table
- AC-003 fast ack: start panel + queued state
- AC-004 progress + pair summary + tier visibility: phase tracker + per-lesson pair list + bound-versions line (D-EXPROG, D-EXART, D-EXDIFF)
- AC-005 transient failure resume: partial-failure rows + scoped resume
- AC-006 worker crash recovery: snapshot reconnect + resume path
- AC-007 cap: cap banner + usage + recovery guidance
- AC-008 supersession: superseded banner naming newer version
- AC-009 SSE replay: reconnect banner + Last-Event-ID (D-EXRECN)
- AC-010 narration stop: D-EXNARR stop control
- AC-011 partial visibility: per-lesson outcomes with reasons + resume
- AC-012 authorized dual download: both download actions + non-disclosing denial
- AC-013 trace: evidence link on run outcomes (F006 deepens)
- AC-014 deterministic pairing validation: valid-pair status semantics with item/category counts; failure rows show the structural reason
- AC-015 deletion: no F005 UI surface; deletion behavior owned by account/project flows
- AC-016 language mode: start panel names the bound language mode
- AC-017 prerequisite gate: unavailable states for both prerequisite kinds + teacher-blocked start error
- AC-018 lesson-plan context in trace: no additional UI surface beyond AC-013 evidence link (F006 deepens)
- AC-019 difficulty recording and immutability: tier radio group at start (D-EXDIFF); recorded tier on every snapshot; duplicate start keeps recorded tier
- AC-020 bounded category selection: pair summary shows category count and item count within bounds

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact SSE event envelope and DTO field names for exercise endpoints | Non-critical | Implementation assignee | Frozen schema-first (Zod) in the first implementation task within Spec semantics; behavior fixed by Spec D4 | RESOLVED |
| UIQ-002 | Teacher-facing wording of the three difficulty tiers | Non-critical | `YMY / Project Owner` | zh-Hans labels `基础` / `巩固` / `进阶` with one-line descriptions tied to classroom purpose (basic objectives / consolidation / extension); enum values fixed by Spec D9 | RESOLVED |
| UIQ-003 | Dual-download layout inside one pair row | Non-critical | Implementation assignee | Both actions render inside the shared list's action slot with distinct accessible names; failure rows show one reason disclosure; no second row per lesson | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, and the complete User Flow are explicit. | YES | User Goal and Flow incl. tier selection, both prerequisite kinds, resume, reconnect, outcome, error, input-validation, cancel/back paths |
| UR-02 | Each affected Page, Screen, and Component has an explicit responsibility. | YES | Responsibilities table, 7 surfaces |
| UR-03 | The UI State Matrix covers applicable states. | YES | 18-row matrix + assessed-state paragraph covering both unavailable kinds, tier-validation, queued/generating/partial/capped/superseded/terminal/blocked/offline |
| UR-04 | Permission, validation, duplicate submit, cancel, back, and recovery are explicit. | YES | Forms table (tier required-no-default, duplicate protection), permission rows, safe-leave semantics |
| UR-05 | Frontend/Backend contract and error mapping are explicit. | YES | Contract section + 10-row error mapping over the five Spec exercise endpoints |
| UR-06 | Responsive behavior is verifiable. | YES | 1024px table: monitoring + pair summaries + downloads + recorded tier preserved; tier selection/start/resume desktop-required |
| UR-07 | Accessibility behavior is verifiable. | YES | A11y section with tier fieldset semantics, dual-download distinct names, focus/live-region/contrast/reduced-motion behaviors + verification approach |
| UR-08 | Existing components and Design System checked with explicit reuse/extension decisions. | YES | Reuse table; third consumer of F004-promoted artifact-run variants; no promotion, no new tokens |
| UR-09 | UI Acceptance linked to `AC-*`. | YES | All 20 ACs mapped to surfaces |
| UR-10 | No Critical UI Open Question `OPEN`/`DEFERRED`. | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (see Spec Gate Record) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 123523a` + this artifact `ux-ui-f005-r1` @ `78923f6468b7`
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `41b391751a33`
- Validated UX/UI revision: `ux-ui-f005-r1` @ `78923f6468b7`
- Validated at: 2026-08-31
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-31
- Approval scope: F005 UX/UI refinement at `ux-ui-f005-r1`

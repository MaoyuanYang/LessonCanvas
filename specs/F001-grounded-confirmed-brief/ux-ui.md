# Feature UX/UI: F001 Grounded Confirmed Brief

## Metadata

- Spec/Issue: `specs/F001-grounded-confirmed-brief/spec.md` / [GitHub Issue #1](https://github.com/MaoyuanYang/LessonCanvas/issues/1)
- Validated Spec revision: `SPEC READY` PASS, content hash `d7ae5094c490` (base `de9306d`)
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `de9306d` plus working-tree edits listed in the UI READY Record
- UX/UI artifact revision/change-log ID: `ux-ui-f001-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (D-BP)
- Existing UX/UI/Design System references: `docs/UX.md` (flows, states, a11y), `docs/UI.md` (patterns), `docs/DESIGN_SYSTEM.md` (tokens, foundational components)

### UI-level decisions (2026-08-24, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-STACK | Frontend stack | TanStack Query + React Hook Form + Zod + Tailwind CSS (semantic token layer) + Radix UI + lucide-react |
| D-BP | Desktop/reduced breakpoint | 1024px: full desktop workspace at >=1024px; canonical reduced experience below |
| D-FONT | Font strategy | System font stacks only (zh-Hans interface stack + serif reading voice); no web-font downloads |

These are technology/interface refinements delegated to the first frontend Feature by `docs/FRONTEND.md` and `docs/DESIGN_SYSTEM.md`; they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: establish a private preparation project, ground it with allowed sources, answer targeted Agent questions, and confirm an immutable requirements brief
- Entry point: public entry page -> Clerk sign-in -> project list
- Preconditions: valid Clerk session; project quota available

```text
Public entry -> Sign in (Clerk) -> Project list
  -> [empty] Create project (name + optional hints) -> Workspace (sources phase)
  -> Upload sources -> policy results (ready / rejected / failed)
  -> Start discovery -> Agent streams questions -> Teacher answers (rounds <= 6)
  -> Draft presented (citations + unresolved-gap markers)
  -> Structured correction (new draft revisions) -> Confirm (all 7 fields non-empty)
  -> Confirmed brief state (authorized input for unit planning)
Error paths:
  -> rejected source: inline reason + fix/replace
  -> provider failure: named error + retry (state preserved)
  -> stale edit: conflict banner -> reload -> re-apply
  -> stop streaming: display stops; complete response stays in trace; explicit re-ask available
  -> permission denied / unknown project: safe not-found -> back to own project list
Cancel/back: leaving at any point preserves drafts and run state; return resumes authoritative state.
```

- Success exit: brief shows `confirmed` status marker with version label and evidence link; workspace states readiness for unit planning (built by F002)
- Cancel/back behavior: back never discards a draft; leaving during streaming lets the model call complete server-side; returning reconnects to authoritative state (no duplicate run)
- Permission denied/recovery: safe not-found page (no existence disclosure) with a single action back to the teacher's project list

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Public entry / sign-in | Explain product boundary and privacy in zh-Hans; hand off to Clerk | Static copy; Clerk session result | Sign in | -> Project list | Button (primary) |
| Project list | Find, create, resume, delete projects; show phase and last activity | `GET /projects` | Create, open, delete (confirm modal) | -> Workspace | List, Status marker, Empty state, Modal |
| New preparation (modal) | Capture project name and optional unit hints | Form input | Submit / cancel | Creates project -> Workspace | Modal, Input, Button |
| Workspace shell | Stable project context: name, brief status badge, context nav (sources / discovery / brief) | Project + brief state | Switch context view | Hosts surfaces below | Navigation item, Status marker |
| Sources panel | Upload and review private sources; show policy results | `POST/GET /sources` | Upload, remove, retry failed (re-upload) | Feeds discovery readiness | List, Status marker, Alert, Input |
| Discovery panel | Stream interview; collect answers; stop/re-ask | SSE stream, `POST /answers`, stop, re-ask | Answer, stop, re-ask | Produces draft | Progress/phase tracker, Button, Input, Disclosure (evidence) |
| Brief panel | Present 7 required fields with citations and gap markers; structured correction; confirmation | `GET/PATCH /brief/draft`, `POST /confirm` | Edit fields, save revision, confirm | Creates immutable version | Input, Status marker, Button, Modal (confirm consequence) |
| Account and usage | Identity, quota context, deletion entries | Session info, quotas | Delete project, delete account | Deletion cascade | Alert, Modal (destructive), Button |
| Safe not-found | Non-disclosing terminal for unauthorized/unknown resources | Route guard result | Return to project list | -> Project list | Empty state, Button |

Component responsibility rule: pages compose these regions; networking/error normalization lives in the shared API layer; no component owns backend state transitions.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Project list | Loading | Entry/refresh | Skeleton rows preserving layout | Wait | Request in flight | Success or error |
| Project list | Empty | No projects | Empty state: why empty + create action | Create project | Empty result | New preparation modal |
| Project list | Error | Fetch failure | Page-level error with correlation ref | Retry/back | Error code | Retry |
| Sources | Processing | Upload accepted | Per-source `processing` marker + note | Continue other work; start discovery disabled until >=1 ready source (explained) | Async parsing | Ready or failed marker |
| Sources | Rejected | Format/size/count/student-data policy | Inline alert naming the rule + recovery (fix file, choose another, rights note) | Replace/remove | Policy result | Re-upload |
| Sources | Failed | Parsing failure | `failed` marker + explanation; excluded from grounding | Remove/re-upload | Parse error | Replace source |
| Discovery | Waiting for answer | Agent question round presented | Question list with unanswered-gap context | Answer, stop | SSE events | Submit answer |
| Discovery | Streaming | Model response in flight | Incremental text, visible stop control | Stop display | SSE token events | Stop or wait |
| Discovery | Stopped-display | Teacher pressed stop | Note: response completing in background; full text remains in trace | Continue, re-ask (explicit, quota note) | Run continues | Re-ask or proceed |
| Discovery | Provider failure | Model outage/timeout | Named provider error (outage vs timeout vs rate) | Retry | provider/transient | Retry preserves state |
| Discovery | Round cap | 6 rounds reached with gaps | Draft presented; unresolved fields explicitly marked | Answer more or hand-fill | Draft ready | Brief panel |
| Brief | Draft | Draft produced/edited | Draft badge, revision label, citations + gap markers | Edit, save, confirm when enabled | Draft revision | Confirm |
| Brief | Confirm blocked | Required fields empty | Confirm disabled + reason listing missing fields | Fill fields | Requirement rule | Complete fields |
| Brief | Stale conflict | Save/confirm against old base | Conflict banner: newer revision exists | Reload, re-apply | stale-version/conflict | Reload |
| Brief | Confirmed | Confirmation success | Success label stating exact status: confirmed version N; downstream readiness note | View evidence; start correction (new draft) | Immutable version | Next feature (F002) entry later |
| Workspace | Quota | Quota exhausted | Quota alert with wait/cleanup guidance | None expensive | quota/rate-limit | Wait or delete unused sources/projects |
| Account | Deleting | Deletion requested | Progress state with scope being deleted | Wait | Cascade in flight | Success or failed |
| Account | Deletion failed | Partial cascade failure | Visible failed-deletion state naming remaining scope | Retry | partial-execution/recovery | Retry idempotently |
| Global | Offline / SSE disconnect | Network drop | Banner: connection lost; remote work may continue; reconnecting | Wait/auto-reconnect | Reconnect from authoritative state | Never duplicates run |
| Global | Permission denied | Non-owner or deleted resource | Safe not-found | Return to own projects | No disclosure | Project list |

Assessed states: Initial (empty project list), Loaded, Submitting (form/upload/confirm buttons show loading and disable), Disabled (confirm blocked, start-discovery blocked with reason), Unauthorized (redirect to sign-in), Forbidden-as-not-found (non-disclosure), Offline (SSE banner), Partial Failure (deletion failed, source failed subset).

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Project create | Name required, 1-60 chars; hints optional <=200 chars | Revalidate; quota check; requirement/input error | Inline on blur+submit; focus first invalid | Submit button loading+disabled |
| Source upload | Format allowlist, <=20MB, <=10 files, rights acknowledgement required before upload | Same rules + content scan; source/file-policy error | Immediate per-file feedback | Per-file upload identity; duplicates rejected by server |
| Discovery answer | Non-empty, <=4000 chars | Revalidate; requirement/input error | Submit on button; Ctrl/Cmd+Enter optional | Client-generated answer id -> server idempotency |
| Brief field edit | Per-field max length (field-specific), required awareness | Revalidate all rules on save | Field-level errors + summary focus | Base revision check -> stale conflict |
| Confirm brief | Enabled only when all 7 non-empty | Atomic server check; names missing fields | Consequence modal before final confirm | Confirmation idempotent per base revision |
| Re-ask | Available only after stop/completion | Quota check | Explicit button with quota note | Server rejects duplicate in-flight re-ask |
| Delete project/account | None (destructive) | Owner check; cascade result | Consequence text + typed/confirmed modal | Re-entry safe; failed state retryable |

Client validation never replaces server constraints. Rights and sensitive-data rules are displayed before upload, not only after rejection.

## Frontend/Backend Contract

- Request/response: typed API client over the Spec API Behavior endpoints; JSON for commands/queries; SSE for the discovery stream; multipart for uploads. Exact DTO field names and SSE event envelopes are frozen in this revision's companion contract table during implementation Task 1 (schema-first via Zod); any deviation from Spec semantics is a Design Change.
- Authentication/authorization: Clerk session token attached by the API client; FastAPI validates; every response assumes owner scope; 401 -> sign-in redirect; 404 (ownership) -> safe not-found.
- Pagination/retry/timeout: project/source/brief lists are bounded in F001 (quota-limited) so pagination is `N/A - bounded lists` per `docs/API.md`; retries only for documented idempotent operations; SSE reconnect uses server state.
- Optimistic update/rollback: `N/A - authoritative server state governs drafts/versions; no optimistic mutation of governed state` (draft save waits for server revision).

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in with return path | Sign in | Return to entry | Yes |
| 404 (ownership/not-found) | Safe not-found page | Back to project list | None disclosed | Yes |
| VALIDATION / REQUIREMENT | Field-level or summary errors naming fields | Fix and resubmit | Focus first problem | Yes |
| SOURCE_POLICY (format/size/count) | Inline rejection naming the rule | Replace/fix file | Re-upload | Yes |
| SOURCE_POLICY (student data) | Safe rejection explanation + recovery path | Remove/replace source | No partial acceptance | Yes (no echo of matched content) |
| STALE_VERSION | Conflict banner: newer revision exists | Reload, re-apply | Reload current | Yes |
| QUOTA_EXCEEDED | Quota alert with concrete guidance | Wait or cleanup | Guidance actions | Yes |
| PROVIDER_TRANSIENT | Named provider error (outage/timeout/rate) | Retry | State preserved | Yes |
| PARTIAL_RECOVERY (deletion) | Failed-deletion state naming remaining scope | Retry | Idempotent retry | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation ID | Retry/back | Report path later | Yes |

Errors never collapse into a single vague toast; mapping follows `docs/UX.md` state behavior and `docs/API.md` taxonomy.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full workspace: sources/discovery/brief context views with side-by-side evidence; current decision first | Full context nav; keyboard accelerators | Dense review layouts; no horizontal scroll for core content |
| Reduced <1024px | Read-only status first: project phase, brief status, waiting questions; conversational answering preserved | Simplified nav; destructive/structured actions replaced by desktop-required message | Single reading sequence; answer input and streaming text remain comfortable |
| Reduced <1024px, structured tasks | Attempting edit/confirm/upload/delete | Explicit desktop-required notice naming the task | No degraded editing surfaces |

Breakpoint: 1024px (D-BP). The boundary implements Spec D10 and `docs/UX.md` canonical reduced experience.

## Accessibility

- Semantic structure/labels: page landmarks (header/nav/main/complementary); context nav exposes current location; status markers pair text labels with visual treatment; streamed interview lives in a labelled conversation region.
- Keyboard and focus order/recovery: all actions keyboard reachable; modals trap focus and return it to the trigger; after save/confirm, focus moves to the status result; after error summary, focus moves to the first actionable problem.
- Error association and live announcements: field errors associated with controls; phase changes (question round arrived, draft ready, confirmed) announced via polite live region; streamed text announced in throttled semantic batches, not per-token.
- Contrast/non-color cues: proposed token set below targets >=4.5:1 body text and >=3:1 UI components; statuses never rely on color alone (labels/icons accompany).
- Motion/touch target considerations: streaming caret and progress transitions short and purposeful; reduced-motion preference honored (no animated progress meaning); touch targets >=24px in reduced layout.
- Verification approach: automated checks plus manual keyboard/focus pass for sign-in -> confirm journey during implementation; contrast verified for the token set; results recorded in Test Design evidence.

## Design System Reuse

F001 is the first UI Feature; it establishes the foundational components already contracted by `docs/DESIGN_SYSTEM.md` rather than inventing new ones.

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, inputs, status markers, alerts, modals, list, skeleton/empty, disclosure, progress tracker | DESIGN_SYSTEM foundational component contracts | Reuse (implement the documented contracts) | Contracts exist; F001 supplies first implementations | Implementation notes return to DESIGN_SYSTEM only if a contract gap is found |
| Semantic tokens (paper/ink/accent/evidence/warning/severe/success/stale/focus) | Token direction CONFIRMED, values open | Compose initial values (below) | First UI Feature must provide validated values | Values + contrast evidence recorded in DESIGN_SYSTEM at Documentation Sync |
| Streaming conversation region | Not previously specified | Compose Feature-local pattern; promote if reused | F001-specific now; F003/F006 will decide promotion | N/A - decision deferred with trigger |
| Phase tracker for discovery rounds | Progress/phase tracker contract | Reuse | Documented variant covers questioning/drafting | N/A - reason: contract sufficient |

Proposed initial semantic token values (validation by contrast testing during implementation; DESIGN_SYSTEM update at Documentation Sync):

| Token | Proposed value | Use |
| --- | --- | --- |
| surface.paper | `#FBFAF7` | Reading surfaces |
| surface.alt | `#F4F2EC` | Grouping surfaces |
| border.default | `#E3E0D8` | Rules and outlines |
| ink.primary | `#1C1B18` | Body text |
| ink.secondary | `#55534C` | Supporting text |
| accent.action | `#345C74` | Primary action (white text >=4.5:1) |
| evidence.citation | `#4A6741` | Source support markers |
| status.warning | `#8A6D1F` | Warnings (text-safe) |
| status.severe | `#A33B2E` | Rejection/severe |
| status.success | `#2F6B45` | Confirmed/ready |
| status.stale | `#6E6A5E` | Stale/superseded |
| focus.ring | `#2F5D8A` | Shared focus treatment |

Fonts (D-FONT): interface stack = system sans with zh-Hans faces (PingFang SC, Microsoft YaHei, Noto Sans CJK fallback); reading voice = system serif stack (Songti SC / SimSun / Noto Serif CJK fallback). No web-font downloads.

## UI Acceptance Links

- AC-001 sign-in/workspace: Public entry, redirect handling
- AC-002 project CRUD: Project list, new preparation modal, workspace shell
- AC-003 non-disclosure: Safe not-found surface
- AC-004/AC-005/AC-006 source policy: Sources panel states (rejected/failed/processing)
- AC-007/AC-008 questioning: Discovery panel rounds, cap, gap markers
- AC-009 streaming/stop/re-ask: Discovery streaming state + stop control
- AC-010 draft grounding: Brief panel citations/gap markers
- AC-011 correction/stale: Brief editing + conflict banner
- AC-012/AC-013 confirmation: Confirm modal + confirmed status marker
- AC-014 standards citation: citation markers distinguishing official snapshot evidence
- AC-015/AC-016 deletion: Account and usage deletion states
- AC-017 provider failure: provider error mapping
- AC-018 reconnect: offline banner + resume
- AC-019 small screen: reduced boundary behavior

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact SSE event envelope and DTO field names | Non-critical | Implementation assignee | Frozen schema-first in implementation Task 1 within Spec semantics; behavior already fixed | RESOLVED |
| UIQ-002 | Participating teacher validation of the flow | Non-critical (for F001 Gate) | `YMY / Project Owner` with teacher | Flow follows confirmed UX.md IA; teacher review scheduled during implementation demo; does not block Gate, recorded as follow-up evidence | RESOLVED |
| UIQ-003 | Promotion of streaming conversation pattern to Design System | Non-critical | Design System owner | Deferred until F003/F006 reuse evidence exists | RESOLVED (decision recorded: defer with trigger) |

No Critical UI Open Question is OPEN or DEFERRED.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, and the complete User Flow are explicit. | YES | User Goal and Flow section incl. error paths and cancel/back |
| UR-02 | Each affected Page, Screen, and Component has an explicit responsibility. | YES | Page/Screen/Component table, 9 surfaces |
| UR-03 | The UI State Matrix covers applicable Loading, Empty, Error, Success, and other states. | YES | 20-row matrix + assessed-state paragraph |
| UR-04 | Permission, validation, duplicate submit, cancel, back, and recovery behavior are explicit. | YES | Forms table (duplicate protection), permission rows, cancel/back in flow |
| UR-05 | The Frontend/Backend contract and error mapping are explicit. | YES | Contract section + 10-row error mapping |
| UR-06 | Responsive behavior is verifiable. | YES | 1024px breakpoint table with reduced-boundary behaviors testable |
| UR-07 | Accessibility behavior is verifiable. | YES | A11y section with concrete focus/announcement/contrast behaviors + verification approach |
| UR-08 | Existing components and the Design System were checked, with an explicit reuse/extension decision. | YES | Reuse table; foundational contracts implemented, token values proposed with validation plan |
| UR-09 | UI Acceptance is in the Spec or explicitly linked to `AC-*`. | YES | UI Acceptance Links maps every AC with UI surface |
| UR-10 | No Critical UI Open Question is `OPEN` or `DEFERRED`. | YES | Open Questions table; none Critical unresolved |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (see Spec Gate Record) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` (base `de9306d` + working-tree edits) + this artifact `ux-ui-f001-r1` @ `c4cd127cb372`
- Evidence checklist result: ALL YES
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `d7ae5094c490`
- Validated UX/UI revision: `ux-ui-f001-r1` @ `c4cd127cb372`
- Validated at: 2026-08-24
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-24
- Approval scope: F001 UX/UI refinement at `ux-ui-f001-r1`

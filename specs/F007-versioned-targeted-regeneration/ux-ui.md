# Feature UX/UI: F007 Versioned Targeted Regeneration

## Metadata

- Spec/Issue: `specs/F007-versioned-targeted-regeneration/spec.md` / [GitHub Issue #14](https://github.com/MaoyuanYang/LessonCanvas/issues/14)
- Validated Spec revision: `SPEC READY` PASS, content hash `fb351456a2ee`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md` (Revise Confirmed Intent flow), `docs/UI.md` (detail views, version comparison around changed intent), `docs/DESIGN_SYSTEM.md` (shared artifact-run surfaces, status language), `docs/FRONTEND.md` at base `main @ 87ae292`
- UX/UI artifact revision/change-log ID: `ux-ui-f007-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: brief/blueprint revision panels and confirm modals (F001/F002), shared artifact-run surfaces (`ArtifactProgressList`, `RunOutcomeBanners`, status label maps), F006 evidence disclosure patterns, desktop gate, ui foundations

### UI-level decisions (2026-08-31, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-REVSEED | Revision entry | When a confirmed version exists, the brief and blueprint panels gain 「基于已确认版本修订」 which seeds a fresh draft revision from the confirmed fields (existing PATCH-draft machinery; the immutable version is never edited in place). During revision the panel keeps showing the confirmed version as current until confirmation — drafts never masquerade as confirmed. |
| D-IMPACT | Impact preview surface | Inside the blueprint panel (the version-pair gate): a 「预览影响」 button renders the D1-matrix preview while drafting, and the 确认蓝图 modal embeds the same preview before its explicit consequence text ("确认后旧任务将安全停止，仅受影响范围需要再生成"). Every affected/retained row names its triggering change; an uncertainty notice appears whenever the matrix widened scope. |
| D-VERSTAB | Version comparison view | Ninth project-context view 「版本对比」: current transition header (from → to versions), intent diff (brief-diff pattern), scope table (lesson × family verdicts 受影响/沿用/历史 with reasons), per-lesson old/new artifact status with both downloads, and the version-pair history list. Read-only; links into the owning generation views for actions. |
| D-TARGET | Transition-aware generation panels | Each family panel's start surface shows the scoped reality before cost: button 「再生成受影响课程（N 课）」 with the affected-lesson count and family scope; the per-lesson list renders retained rows (沿用 + 源版本 badge + prior-run provenance tooltip + download) alongside in-run rows; prerequisite failures name the uncovered lessons and link to 教案生成. Duplicate starts keep returning the existing scoped run (button shows 进行中/已存在 states, never re-opens cost). |
| D-RETAINDS | Retained-row shared variant | The shared artifact-run surfaces gain a `retained` row variant (status label 沿用, prior-version badge, provenance line, download slot; no resume action) consumed by all three family panels — a Design System shared-surface extension recorded at documentation sync (same status-language rules; no Feature-local visual language). |
| D-VERSSMALL | Small-screen boundary | Below 1024px, 版本对比 keeps the transition header, verdict summary counts, and per-lesson old/new status readable; deep scope tables and diff browsing defer behind the existing desktop-required notice. Generation panels keep scoped-start availability (a teacher decision) but with the same desktop rule as existing starts. |

No new tokens; no new visual language; retained/historical/affected are text+marker distinctions per the shared status-language rule.

These are interface refinements within Spec behavior (D1–D7); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: revise confirmed intent safely — see what a change will cost before confirming, confirm a new version without losing valid work, rebuild only what is affected, and compare old vs new with downloads
- Entry points: 教学简报/单元蓝图 panels (revision + impact), generation/deck/exercise panels (targeted start + retained rows), 版本对比 view
- Preconditions: a confirmed brief+blueprint pair; prior generation output for retention to appear

```text
Workspace -> 单元蓝图 -> 基于已确认版本修订 (D-REVSEED; brief revisions follow the same pattern in 教学简报)
  -> Edit structured draft (draft visibly distinct from confirmed)
  -> 预览影响 (D-IMPACT): scope table + reasons + uncertainty
  -> 确认蓝图 (modal embeds preview + consequence text)
       stale base -> version-conflict modal naming current versions; nothing written (D7)
       older active runs -> settle superseded at checkpoint (banner; history preserved) (D3)
  -> Per family (D-TARGET): 教案生成/课件生成/练习与答案
       retained rows show 沿用 + provenance immediately (D5)
       再生成受影响课程（N 课） -> scoped run -> progress/recovery identical to F003-F005
       prerequisite uncovered lessons -> named with recovery link (D2)
  -> 版本对比 (D-VERSTAB): intent diff + scope table + per-lesson old/new + both downloads (D6)
Error paths: version conflict (409) -> conflict modal -> re-open from newer version; requirement (uncovered) -> guidance + link; provider/quota/superseded paths unchanged from F003-F005; permission -> safe not-found.
Cancel/back: drafts persist as drafts; leaving never cancels runs; comparison view is read-only.
```

- Success exit: affected scope regenerated under the new version pair; unaffected artifacts retained with provenance; comparison shows the full old/new picture with downloads.
- Permission denied: safe not-found without existence disclosure.

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| Brief/Blueprint revision entry | Seed revision draft from confirmed version; keep draft/confirmed distinction | Confirmed version state, draft endpoints | 基于已确认版本修订; edit; save draft | Draft saved (conflict on stale base) | Existing panels + Button/Alert |
| Impact preview region | Render D1 verdicts with reasons and uncertainty | `GET /projects/{id}/impact` | Inspect; adjust intent instead of accepting wider scope | Informs confirm decision | Table/density list, Alert (uncertainty), Status marker |
| Confirm modal (blueprint) | Explicit consequence text + embedded preview before confirmation | Impact + confirm endpoint | Confirm; cancel | New version pair or conflict modal | ConfirmModal, brief-diff pattern |
| Family panels (generation/decks/exercises) | Transition-aware start with scoped count; retained rows; coverage-gated availability | Family snapshot (scope, retained entries), start/resume endpoints | 再生成受影响课程; resume scoped failures; download retained/in-run artifacts | Scoped runs; downloads | Shared artifact-run surfaces + retained variant (D-RETAINDS) |
| 版本对比 view | Read-only transition comparison + version history | `GET /versions/current-transition` | Inspect; download old/new; link to owning views | Context for decisions | Table/density list, Status marker, evidence disclosure patterns |
| Small-screen notice | Defer deep comparison below 1024px | Viewport | Read summary | Desktop for depth | Desktop gate |

Component responsibility rule unchanged: networking/error normalization in the shared API layer; no component owns business-state transitions; comparison view issues no state-changing requests.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Revision entry | No confirmed version | Project pre-gate | Action hidden; existing gate guidance shown | Follow existing flow | Version state | Confirm first |
| Revision entry | Draft in progress | Seeded or edited draft | Draft badge 草稿修订 N; confirmed version still labeled current | Edit; preview impact; save | Draft endpoints | Confirm or discard |
| Impact preview | Loading | 预览影响 click | Skeleton preserving layout | Wait | Impact request | Rendered |
| Impact preview | Rendered | Response | Scope table with per-row reasons; uncertainty Alert when widened; structural adds/removes named | Adjust intent or proceed to confirm | Impact payload | Confirm path |
| Impact preview | No delta | Draft equals confirmed | 「未检测到实质变更」 with confirm disabled consequence note | Keep editing | Impact payload | — |
| Confirm modal | Conflict (stale base) | 409 on confirm | Conflict modal naming current versions; draft preserved | 从新版本重新修订 | Confirm error | Re-seed draft |
| Family panel | Transition available | New pair + prior runs | Scoped start button with N; retained rows visible | 再生成受影响课程 | Transition-aware start | Scoped run |
| Family panel | No prior runs | Ordinary first generation | Existing full-scope start (unchanged F003-F005 surface) | Start full | Existing start | Full run |
| Family panel | Uncovered prerequisite | Lessons not plan-covered | Requirement message naming lessons + link to 教案生成 | Fix coverage | Start error | Retry start |
| Family panel | Scoped run active/failed | Targeted run states | Existing progress/outcome surfaces scoped to affected lessons; retained rows inert | Resume scoped failures | Existing endpoints | Checkpoint resume |
| Retained row | Steady | Unaffected lesson under transition | 沿用 + 源版本 badge + provenance + download; no actions beyond download | Download | Snapshot retained entry | — |
| 版本对比 | Loading/empty/error | Entry/refresh | Skeleton; empty (no transition yet) explains first-version state; named error with retry | Retry/back | Transition endpoint | Rendered |
| 版本对比 | Rendered | Transition exists | Header from→to; intent diff; scope verdicts with reasons; old/new per-lesson status + downloads | Download both; navigate to owning views | Transition payload | Teacher decision |
| Global | Permission denied | Non-owner | Safe not-found | Back to own projects | No disclosure | Project list |

Assessed states: Initial, Loaded, Submitting (confirm/start buttons loading + disabled), Disabled (confirm without delta; start when uncovered), Unauthorized, Forbidden-as-not-found, Conflict, Partial Failure (scoped), Superseded, Uncertain-impact, Structural-add/remove.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Revision seeding | Enabled only with a confirmed version | Draft created from version fields; stale base on save → 409 | Focus to first editable field | Seeding is idempotent per draft revision chain |
| Confirm new version | Enabled with a material delta (preview-informed); consequence text in modal | Stale `base_revision` → 409 naming current versions; supersession transactional | Modal focus; on conflict focus the conflict summary | One confirm per base revision |
| 再生成受影响课程 | Shows scoped N before click; disabled while a run for the pair+family exists (shows its state) | Idempotent per project+pair+family; scope fixed at creation; uncovered lessons → REQUIREMENT | Button loading; focus to run status | Duplicate start returns existing scoped run |
| Resume scoped failures | Existing rules within scope | Existing state machine | Existing modal | Existing idempotency |
| Impact preview | Draft present | Requirement error if no confirmed pair | Inline region render | Read-only refresh |

Client validation never replaces server constraints.

## Frontend/Backend Contract

- Request/response: typed client over `GET /projects/{id}/impact`, `GET /projects/{id}/versions/current-transition`, and the transition-aware family starts/snapshots (snapshots gain `scope_lesson_indexes` and `retained_artifacts[]` with prior artifact id, source versions, run id, download availability); confirm endpoints unchanged except conflict payload already present. Exact DTO field names frozen schema-first (TypeScript interfaces per codebase convention, review-recorded M-3 pattern) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: shared API client token; 401 → sign-in; 404 → safe not-found; 409 → conflict modal; REQUIREMENT → inline guidance with links.
- Pagination: `N/A - bounded lists` (lessons bounded by blueprint; version history bounded in Phase 1).
- Optimistic update/rollback: `N/A - authoritative server state governs; reads refresh after confirm/start`.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in | Sign in | Return | Yes |
| 404 (ownership) | Safe not-found | Back to project list | None disclosed | Yes |
| 409 STALE_VERSION (confirm/save) | Conflict modal naming current versions | 从新版本重新修订 | Re-seed draft | Yes |
| REQUIREMENT (uncovered lessons) | Inline message listing lessons + link to 教案生成 | Complete/retain plan coverage | Retry start | Yes |
| QUOTA_EXCEEDED / PROVIDER_TRANSIENT / PARTIAL_EXECUTION | Existing family-panel treatments, scoped | Existing actions | Existing recovery | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

Errors never collapse into one vague toast; mapping follows `docs/API.md` and `docs/UX.md`.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full revision/impact/confirm flow; scoped starts with retained rows; complete comparison tables with old/new downloads | All actions keyboard operable | Scope tables wrap reasons; no horizontal scroll |
| Reduced <1024px | Transition header, verdict counts, per-lesson old/new status, retained markers and downloads preserved | Deep scope tables, diff browsing, and structured revision editing defer behind desktop-required notices | Single reading sequence |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md revise-flow mandate that status, recovery information, and downloads survive small screens.

## Accessibility

- Semantic structure: impact scope table is a labelled table with headers (课程 / 产物族 / 判定 / 原因); verdicts are text+marker (受影响/沿用/历史), never color-alone; uncertainty notice is an Alert with role=status; comparison view uses landmarks and labelled sections; retained rows carry provenance as text.
- Keyboard and focus: revision seed, preview, confirm-modal (focus trap + return), scoped start, resume, all downloads, and comparison navigation are keyboard reachable in reading order; conflict modal moves focus to the conflict summary; confirm returns focus to its trigger; no focus movement for passive preview refresh.
- Live announcements: confirm success/conflict and scoped-run state changes announced politely; impact preview render is passive (no announcement spam).
- Contrast/non-color cues: token set >=4.5:1 body / >=3:1 components; verdict distinctions in language and markers.
- Motion/reduced motion: no animation-dependent meaning; skeletons honor reduced motion.
- Verification approach: automated a11y checks in component/E2E plus the scripted keyboard pass over the revise→preview→confirm→scoped-start→comparison path, recorded in the Test Design execution snapshot.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, modals, alerts, status markers, tables/lists, skeleton/empty | F001–F006 foundations | Reuse | All variants exist | None |
| Per-lesson family lists + outcome banners | Shared artifact-run surfaces | Extend: `retained` row variant (D-RETAINDS) consumed by all three family panels | First cross-family need for retained presentation | Shared-surface extension documented at documentation sync |
| Intent diff presentation | F002 brief-diff pattern | Reuse | Same semantics under version transition | None |
| Evidence disclosure / density tables | F006 patterns | Compose (comparison view) | Same reading rules | None |
| Desktop gate | Existing pattern | Reuse | Same deferred-task semantics | None |

No new tokens; no Feature-local visual language.

## UI Acceptance Links

- AC-001 new version + visible scope: D-IMPACT preview + confirm modal
- AC-002 safe-checkpoint supersession: confirm path + superseded banner (existing treatment)
- AC-003 retained presentation + downloads: D-RETAINDS rows in family panels
- AC-004 stale conflict: conflict modal (Forms table + Error Mapping)
- AC-005 reasons + uncertainty: impact scope table rows + uncertainty Alert
- AC-006 lesson-level scoping: preview verdicts + scoped start count N
- AC-007 unit-level scoping: preview verdicts (all lessons × families)
- AC-008 structural add/remove: preview structural section + historical markers in comparison
- AC-009 scoped idempotent start: Forms table duplicate protection + button states
- AC-010 scoped resume: family panel existing recovery within scope
- AC-011 coverage prerequisite: REQUIREMENT mapping with lesson names + link
- AC-012 comparison view: D-VERSTAB surfaces
- AC-013 non-disclosure: permission row in State Matrix
- AC-014 deletion: no F007-specific UI action; account/project flows own it

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact DTO field names for impact/transition/snapshot extensions | Non-critical | Implementation assignee | Frozen schema-first (TypeScript interfaces) in the first implementation task within Spec semantics | RESOLVED |
| UIQ-002 | Whether impact preview also appears in the brief panel | Non-critical | `YMY / Project Owner` | No — the version-pair gate is blueprint confirmation; brief revisions show the existing brief diff, and the pair-level impact preview lives at the blueprint stage where the transition actually happens | RESOLVED |
| UIQ-003 | Retained-row actions | Non-critical | Implementation assignee | Download only; no resume/re-validate actions (D5); provenance line links to 运行证据 for depth | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, complete User Flow explicit | YES | Flow incl. revision, preview, conflict, scoped start/resume, comparison, permission paths |
| UR-02 | Each affected Page/Screen/Component has explicit responsibility | YES | Responsibilities table, 6 surfaces |
| UR-03 | UI State Matrix covers applicable states | YES | 14-row matrix + assessed states incl. uncertain-impact, structural, conflict, uncovered |
| UR-04 | Permission, validation, duplicate submit, cancel, back, recovery explicit | YES | Forms table (seed/confirm/start/resume idempotency), permission rows |
| UR-05 | Frontend/Backend contract and error mapping explicit | YES | Contract section + 6-row error mapping |
| UR-06 | Responsive behavior verifiable | YES | 1024px table preserving status/verdicts/downloads |
| UR-07 | Accessibility behavior verifiable | YES | A11y section: table semantics, focus rules, non-color verdicts, verification approach |
| UR-08 | Design System checked with explicit reuse/extension decisions | YES | Reuse table; one shared-surface extension (retained variant) recorded for documentation sync |
| UR-09 | UI Acceptance linked to `AC-*` | YES | All 14 ACs mapped |
| UR-10 | No Critical UI Open Question open/deferred | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `fb351456a2ee`) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 87ae292` + this artifact `ux-ui-f007-r1` @ `97597ad3c608`
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `fb351456a2ee`
- Validated UX/UI revision: `ux-ui-f007-r1` @ `97597ad3c608`
- Validated at: 2026-08-31
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-08-31
- Approval scope: F007 UX/UI refinement at `ux-ui-f007-r1`

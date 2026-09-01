# Feature UX/UI: F008 Alignment Review and Delivery

## Metadata

- Spec/Issue: `specs/F008-alignment-review-and-delivery/spec.md` / [GitHub Issue #16](https://github.com/MaoyuanYang/LessonCanvas/issues/16)
- Validated Spec revision: `SPEC READY` PASS, content hash `dc301bba1a83`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md` (review/delivery flow), `docs/UI.md` (unit workspace views), `docs/DESIGN_SYSTEM.md` (shared artifact-run surfaces, status language), `docs/FRONTEND.md` at base `main @ 2b36d73`
- UX/UI artifact revision/change-log ID: `ux-ui-f008-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: workspace tab shell (workspace-view), shared artifact-run surfaces and status label maps, F006 evidence disclosure patterns, F007 version-compare panel (对齐视图与之并列且互相链接), ui foundations

### UI-level decisions (2026-09-01, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-ALIGNTAB | Alignment/delivery entry | Tenth project-context view 「对齐与交付」 in the workspace tab shell. Header always shows the bound brief+blueprint version pair, technical package status (技术校验状态), and product-validation status (产品验证状态：未评估) side by side — the two statuses are never merged into one badge. |
| D-COVERAGE | Coverage presentation | Coverage is presented objective-first (blueprint objectives as rows) with per-family support markers (教案/课件/练习) plus a lesson-first collapsed section for per-lesson completeness. Markers are text+icon (已覆盖/缺失/冲突), never color-alone; each row expands to its evidence (owning versions, artifact status, validation outcome) using the F006 progressive-disclosure pattern. |
| D-FINDINGS | Findings list and recovery | Findings render in a severity-grouped list (严重/警告/提示). Each finding shows: rule name in teacher-readable language, affected scope (objective/lesson/family), evidence link, and the primary recovery action as an inline button — 修正意图 (links to revision entry), 定向再生成 (links to the owning family panel), or 记录理由并覆盖 (only on overridable disputed findings). |
| D-OVERRIDE | Override dialog | 记录理由并覆盖 opens a modal: finding summary (read-only), required free-text reason (min length enforced, character counter), consequence text ("覆盖不会修改被评内容，仅记录教学判断"), and confirm button requiring the reason. Withdrawal reuses the same surface from the recorded-override row with its own confirm. Recorded overrides list under 覆盖记录 with reason, time, and withdraw action. |
| D-EXPORT | Export surface | A 交付 region inside the view: current status sentence (可导出草稿 / 可交付技术校验包 / 存在未解决严重问题), two explicit actions — 导出草稿包 (always available with confirmed pair) and 交付校验包 (enabled only when validated) — each stating it binds the current version pair. Export history list (label, versions, time, download) below. Package download streams the ZIP through the authorized endpoint; no storage paths appear. |
| D-PRINT | Printable report | 打印对齐报告 opens a dedicated print-styled route in a new tab (browser print / save-as-PDF), reusing the report data: bound versions, label, status pair, objective coverage summary, findings with overrides, and per-lesson completeness. Same route serves an export's report snapshot for a historical export. Print stylesheet hides app chrome; no new rendering dependency. |
| D-ALIGNSMALL | Small-screen boundary | Below 1024px, the view keeps the status pair header, severity counts, findings list with recovery links, and export availability; the full coverage matrix and print report defer behind the existing desktop-required notice. |

No new tokens; no new visual language; draft/validated/not-evaluated are text+marker distinctions per the shared status-language rule. 严重/警告 severity follows existing status-language rules.

These are interface refinements within Spec behavior (D1–D8); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: individual senior-high English teacher (workspace owner)
- Goal: see how each objective is supported across the whole current package, resolve findings honestly, and deliver a labelled package with an honest status pair
- Entry points: 对齐与交付 workspace tab; links from 版本对比 and family panels
- Preconditions: a confirmed brief+blueprint version pair

```text
Workspace -> 对齐与交付 (D-ALIGNTAB)
  -> Coverage view (D-COVERAGE): objective-first rows + lesson-first section, evidence on expand
  -> Findings (D-FINDINGS): severity-grouped; each with evidence + recovery action
       修正意图 -> existing revision entry (F007 D-REVSEED surfaces)
       定向再生成 -> owning family panel scoped start (F007 D-TARGET)
       记录理由并覆盖 (D-OVERRIDE, overridable disputed only) -> modal -> recorded override -> status recalculates
  -> Status header updates: 技术校验状态 vs 产品验证状态（未评估）(D-ALIGNTAB)
  -> 交付 (D-EXPORT): 导出草稿包 (labelled 草稿) or 交付校验包 (validated only)
       unresolved severe -> 交付校验包 disabled with named blockers; draft stays available
  -> 打印对齐报告 (D-PRINT): print-styled route, browser print/save-PDF
Error paths: no confirmed pair -> prerequisite state with recovery link; requirement (ineligible override / validated export blocked) -> inline naming; stale version pair on action -> refresh-and-retry guidance; provider failure during build -> failed export row with retry; permission -> safe not-found.
Cancel/back: override modal cancels with nothing written; leaving the view never cancels an export build (history shows result).
```

- Success exit: findings resolved or honestly overridden; package exported with the correct label and both statuses visible on screen and in the report.
- Permission denied: safe not-found without existence disclosure.

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| 对齐与交付 view | Present coverage, findings, status pair, delivery for the current version pair | `GET /projects/{id}/alignment` | Inspect; expand evidence; navigate recovery actions; override; export; print | Overrides recorded; exports created; report opened | Tab shell, status markers, disclosure patterns |
| Coverage region | Objective-first + lesson-first coverage with evidence | Alignment payload | Expand/collapse; follow evidence links | Context for findings | Table/density list, status marker, F006 disclosure |
| Findings list | Severity-grouped findings with recovery actions | Alignment payload | 修正意图 / 定向再生成 / 记录理由并覆盖 | Navigation or override modal | Alert/list patterns, status markers |
| Override dialog | Record/withdraw owner decision with required reason | Override endpoints | Confirm with reason; withdraw; cancel | Override recorded/withdrawn; status refresh | Modal + textarea + Button |
| 交付 region | Status sentence + draft/validated export actions + history | Export endpoints | 导出草稿包; 交付校验包; download | Export records; ZIP download | Button, list, download pattern |
| Print report route | Print-styled report (current or snapshot) | Report endpoint | Browser print/save | Paper/PDF output | Print stylesheet over semantic report markup |
| Small-screen notice | Defer matrix/print below 1024px | Viewport | Read summary | Desktop for depth | Desktop gate |

Component responsibility rule unchanged: networking/error normalization in the shared API layer; no component owns business-state transitions; the report route is read-only.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| View | No confirmed pair | Project pre-gate | Prerequisite state naming missing gate | Follow link to confirm brief/blueprint | Alignment 4xx mapping | Confirm then return |
| View | Loading | Entry/refresh | Skeleton preserving header/matrix layout | Wait | Alignment request | Rendered |
| View | Error | Request failure | Named error with retry | Retry/back | Error mapping | Rendered |
| View | Rendered | Response | Status pair header; coverage; findings; delivery region | All actions above | Alignment payload | Teacher decision |
| Coverage | Full coverage | All supported | 已覆盖 markers throughout | Inspect evidence | Alignment payload | Proceed to delivery |
| Coverage | Gap/conflict present | Missing/failed member | 缺失/冲突 markers + linked finding | Recovery action | Alignment payload | Resolve |
| Findings | Severe unresolved | Any severe open | 严重 group visible; 交付校验包 disabled with named blockers | 修正/再生成/覆盖(若可) | Alignment payload | Resolve or draft export |
| Override dialog | Reason empty/too short | Submit attempt | Inline field error; focus to textarea | Edit reason | Client + server validation | Confirm |
| Override dialog | Server rejection (ineligible/stale) | 4xx | Inline error naming why; nothing written | Refresh view | Override error mapping | Re-open from current state |
| Recorded override | Steady | Override saved | 覆盖记录 row: finding, reason, time | 撤销覆盖 | Override endpoints | Finding returns open |
| 交付 | Draft exportable | Confirmed pair | 导出草稿包 enabled; label 草稿 explicit | Export | Export create | Download/history |
| 交付 | Validated | D3 satisfied, zero severe | 交付校验包 enabled | Export | Export create | Download/history |
| 交付 | Building | Export in progress | Building indicator on the row | Wait | Export status | Ready or failed |
| 交付 | Failed | Storage/provider error | Failed row with named error + retry | 重新导出 | Export error mapping | Retry |
| 交付 | Ready (repeat) | Unchanged manifest re-request | Existing record returned; no duplicate row confusion | Download | Idempotent create | Download |
| History | Stale export listed | Newer version exists | Older exports visibly bound to their versions/labels; never current | Download historical | Export list | Truthful history |
| Print report | Loading/rendered | Open/print | Report renders fully before print dialog guidance | Print/save | Report data | Output |
| Global | Permission denied | Non-owner | Safe not-found | Back to own projects | No disclosure | Project list |

Assessed states: Initial, Loaded, Submitting (override confirm, export create — loading + disabled), Disabled (validated export while blocked), Unauthorized, Forbidden-as-not-found, Conflict (stale version pair), Partial (mixed coverage), Superseded-stale (history rows), Provider failure.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| Override reason | Required, min length, counter | Same + eligibility + version-pair binding; ineligible → REQUIREMENT; mismatch → STALE | Focus to textarea on open; error focus to field | Identical open override re-submits return existing decision; button disabled while submitting |
| Withdraw override | Confirm step only | Owner + current binding checks | Confirm modal focus | Withdraw of already-withdrawn → refresh state |
| 导出草稿包 | Confirmed pair present | Label eligibility; idempotent per (pair, label, manifest) | Button loading; focus to history row | Repeat returns existing export (D8) |
| 交付校验包 | Enabled only when status validated | REQUIREMENT naming blockers if state changed server-side | Button loading; on refusal show named blockers | Same idempotency |
| 打印报告 | Report data loaded | Read-only | New tab; no focus steal from main view | Read-only refresh |

Client validation never replaces server constraints.

## Frontend/Backend Contract

- Request/response: typed client over `GET /projects/{id}/alignment`, `POST/DELETE alignment/overrides`, `GET alignment/report`, `POST/GET delivery/exports`, `GET delivery/exports/{id}/download` (report snapshot download alongside). Exact DTO field names frozen schema-first (TypeScript interfaces per codebase convention) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: shared API client token; 401 → sign-in; 404 → safe not-found; REQUIREMENT → inline guidance naming blockers/eligibility; STALE → refresh guidance; provider class → failed-row retry.
- Pagination: `N/A - bounded lists` (objectives/lessons bounded by blueprint; export history bounded in Phase 1).
- Optimistic update/rollback: `N/A - authoritative server state governs; reads refresh after override/export`.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in | Sign in | Return | Yes |
| 404 (ownership/export id) | Safe not-found | Back / history | None disclosed | Yes |
| REQUIREMENT (no pair / ineligible override / validated blocked) | Inline message naming the gate, finding, or blockers + link | Fix state then retry | Recovery path named | Yes |
| STALE_VERSION (version-pair mismatch on action) | Refresh guidance "版本已更新，正在刷新" | Auto-refresh view | Re-decide on current state | Yes |
| PROVIDER_TRANSIENT (export build) | Failed export row with named error | 重新导出 | Retry | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

Errors never collapse into one vague toast; mapping follows `docs/API.md` and `docs/UX.md`.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full coverage matrix, findings with recovery actions, override dialog, export region + history, print report | All actions keyboard operable | Matrix wraps evidence text; no horizontal scroll |
| Reduced <1024px | Status pair header, severity counts, findings with recovery links, export availability preserved | Full coverage matrix and print report defer behind desktop-required notice | Single reading sequence |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md mandate that status, recovery, and delivery availability survive small screens.

## Accessibility

- Semantic structure: coverage is a labelled table (教学目标 / 课时 / 产物族 / 判定); findings are a labelled list grouped by severity with headings; statuses are text+marker (已覆盖/缺失/冲突, 草稿/技术校验通过, 未评估), never color-alone; the report route uses semantic headings and a print stylesheet.
- Keyboard and focus: view entry, evidence disclosure, all recovery-action buttons, override modal (focus trap, focus to textarea on open, return to trigger on close), export actions, history downloads, and print-route operation are keyboard reachable in reading order; field errors move focus to the failing field; building/failed export rows are announced.
- Live announcements: status-header recalculation after override/withdraw/export announced politely; coverage expansion is passive.
- Contrast/non-color cues: token set >=4.5:1 body / >=3:1 components; severity and label distinctions in language and markers.
- Motion/reduced motion: no animation-dependent meaning; skeletons honor reduced motion.
- Verification approach: automated a11y checks in component/E2E plus a scripted keyboard pass over open-alignment → expand-evidence → override → export → print path, recorded in the Test Design execution snapshot.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, modals, alerts, status markers, tables/lists, skeleton/empty/error | F001–F007 foundations | Reuse | All variants exist | None |
| Progressive evidence disclosure / density tables | F006 patterns | Compose (coverage + findings) | Same reading rules | None |
| Status-pair presentation | Existing status marker + label map | Compose (two adjacent markers with distinct semantics) | First paired-status need; composition suffices | None |
| Desktop gate, download patterns | Existing | Reuse | Same semantics | None |
| Print stylesheet | None project-wide yet | Extend: one print stylesheet for the report route (hides app chrome) | First printable surface; minimal, token-consistent | Documented at documentation sync as a shared print pattern |

No new tokens; no Feature-local visual language.

## UI Acceptance Links

- AC-001 objective relationships + evidence: D-COVERAGE rows and expansion
- AC-002 deterministic recomputation, no model call: view refresh behavior (no narration/run surfaces introduced)
- AC-003 missing-family severe gap: findings 严重 group + disabled validated export
- AC-004 failed-validation conflict finding: findings list + evidence expansion
- AC-005 validated export blocked / draft available: D-EXPORT enabled/disabled states
- AC-006 gap not overridable: override action absent on gap findings; server REQUIREMENT mapping
- AC-007 reasoned override auditable: D-OVERRIDE dialog + 覆盖记录 list
- AC-008 withdraw restores finding: 覆盖记录 withdraw action + live status recalculation
- AC-009 version change makes prior state historical: History stale rows + refresh guidance
- AC-010 validated vs not-evaluated pair: D-ALIGNTAB status pair header
- AC-011 labelled byte-identical ZIP, idempotent repeat: D-EXPORT actions + Ready (repeat) row
- AC-012 printable report content: D-PRINT route contents
- AC-013 non-disclosure + deletion: permission rows; deletion owned by project flows

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact DTO field names for alignment/override/export/report | Non-critical | Implementation assignee | Frozen schema-first (TypeScript interfaces) in the first implementation task within Spec semantics | RESOLVED |
| UIQ-002 | Print trigger details (dialog guidance vs silent) | Non-critical | Implementation assignee | Report renders fully first; a one-line 打印提示 with the browser print shortcut; no custom print engine | RESOLVED |
| UIQ-003 | Whether family panels link into 对齐与交付 | Non-critical | Implementation assignee | Yes — completion banners of family runs gain a passive link 查看对齐情况; no state change | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, complete User Flow explicit | YES | Flow incl. coverage, findings, override/withdraw, export, print, permission paths |
| UR-02 | Each affected Page/Screen/Component has explicit responsibility | YES | Responsibilities table, 7 surfaces |
| UR-03 | UI State Matrix covers applicable states | YES | 17-row matrix + assessed states incl. building/failed/idempotent-repeat/stale-history |
| UR-04 | Permission, validation, duplicate submit, cancel, back, recovery explicit | YES | Forms table (override/export/print), permission rows |
| UR-05 | Frontend/Backend contract and error mapping explicit | YES | Contract section + 6-row error mapping |
| UR-06 | Responsive behavior verifiable | YES | 1024px table preserving status/findings/delivery availability |
| UR-07 | Accessibility behavior verifiable | YES | A11y section: table semantics, focus rules, non-color statuses, verification approach |
| UR-08 | Design System checked with explicit reuse/extension decisions | YES | Reuse table; one minimal extension (shared print stylesheet) recorded for documentation sync |
| UR-09 | UI Acceptance linked to `AC-*` | YES | All 13 ACs mapped |
| UR-10 | No Critical UI Open Question open/deferred | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `dc301bba1a83`) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 2b36d73` + this artifact `ux-ui-f008-r1` @ `08ce833627d7`
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `dc301bba1a83`
- Validated UX/UI revision: `ux-ui-f008-r1` @ `08ce833627d7`
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01
- Approval scope: F008 UX/UI refinement at `ux-ui-f008-r1`

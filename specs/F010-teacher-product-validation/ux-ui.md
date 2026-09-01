# Feature UX/UI: F010 Teacher Product Validation

## Metadata

- Spec/Issue: `specs/F010-teacher-product-validation/spec.md` / [GitHub Issue #20](https://github.com/MaoyuanYang/LessonCanvas/issues/20)
- Validated Spec revision: `SPEC READY` PASS, content hash `66a3c94329a9`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md` (evidence-panel flow, small-screen boundary), `docs/UI.md` (evidence region rules, print convention), `docs/DESIGN_SYSTEM.md` (status markers, evidence disclosure, printable report pattern), `docs/FRONTEND.md` at base `main @ 352db99`
- UX/UI artifact revision/change-log ID: `ux-ui-f010-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced read-only experience below 1024px (F001 D-BP, F002 D8)
- Existing UX/UI/Design System references: 运行证据 panel and its 技术评估 region (F009), status marker + label maps, F006 disclosure patterns, F008 alignment status pair and print report route, ui foundations

### UI-level decisions (2026-09-01, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-PVREGION | Product-validation entry | A 「产品验证」 region in the existing 运行证据 (evidence) panel, rendered below the 技术评估 region — no new workspace tab (Spec D7). The panel order mirrors the product principle 技术证据为先，产品验证独立呈现. The region always shows: rubric revision (`rubric-r1`), overall product-validation status with the bounded-conclusion sentence (一位外部高中英语教师的有限证据，不可推广), and one row per unit assignment (unit name, package binding summary, state chip). |
| D-PVSTATUS | Live status vocabulary | The 对齐与交付 status pair's second chip (currently hardcoded 产品验证状态：未评估) and the status lines in the technical-evaluation report and delivery print report render the live D6 vocabulary: 未评估 / 进行中 / 待证据 / 未完成 / 通过 / 失败, plus 已过时（历史） for superseded results. Technical and product statuses always render as two adjacent but separate chips/lines; neither ever merges into the other. |
| D-PVCREATE | Fixing an assignment | The region offers 创建评审分派 (desktop only): a modal listing the project's technically complete unit packages (unit name, dataset revision, confirmed brief/blueprint versions, artifact-set summary); confirmation fixes the immutable package identity. A duplicate create shows 「该分派已存在」 with the existing assignment — never a silent second row (Spec D8). Packages with any missing family member are not selectable, with the F008 D3 gap named. |
| D-PVIMPORT | Evidence import | 导入量表证据 opens an expandable inline form (F006 disclosure pattern, not a modal — the rubric is long): five dimension scores (1–5) each with its evidence note, a severe-finding repeater (类别 / 课时 / 证据说明), the structural-rework question (是否需要结构性返工 + required reason when true), evaluator attestation (伪匿名评审者标识 + 完成日期), and a required upload of the evaluator's original completed rubric document (stored privately, treated as untrusted input). Submit is disabled while submitting; the server validates the full schema and returns every violating field at once. |
| D-PVDETAIL | Assignment detail | Each assignment row expands (F006 disclosure) to: package identity (dataset revision, brief/blueprint versions, per-family checksum summary), dimension scores with notes, severe findings, structural-rework answer, computed outcome, capture-channel label 所有者代录 (owner-mediated import), and the evidence-revision history where superseded revisions remain visible with 历史版本 markers. |
| D-PVSTALE | Stale results | When a bound package is superseded, the row settles 已过时（历史） with a pointer to what superseded it; 导入量表证据 is disabled on stale rows with guidance to fix a new assignment (Spec D5); prior results stay readable. |
| D-PVSMALL | Small-screen boundary | Below 1024px the region keeps the overall status chip, per-unit outcome chips, and the bounded-conclusion sentence (read-only); 创建评审分派, the import form, and expanded detail defer behind the existing desktop-required notice. |

No new tokens; no new visual language; all statuses are text+marker distinctions per the shared status-language rule.

These are interface refinements within Spec behavior (D1–D9); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: workspace owner (project owner); the external teacher evaluator never uses the application (Spec D3)
- Goal: fix complete unit packages for external review, import the evaluator's completed rubric evidence, and read honest per-unit and overall product-validation status alongside — never merged with — technical status
- Entry points: 运行证据 panel (产品验证 region); status chips in 对齐与交付; status lines in the technical-evaluation report and delivery print report
- Preconditions: a technically complete package for the chosen unit; the evaluator's completed rubric for import

```text
Workspace -> 运行证据 panel
  -> 产品验证 region (D-PVREGION): rubric revision + overall status + per-unit assignment rows
       empty -> 「尚未进行产品验证」 + 创建评审分派 (desktop)
       创建评审分派 (D-PVCREATE): modal (select complete package) -> confirm -> assignment 待证据
            duplicate -> 「该分派已存在」 notice, existing assignment shown
       导入量表证据 (D-PVIMPORT): inline form (scores/notes, severe findings, rework answer,
            attestation, original document) -> submit -> outcome computed (通过 / 失败)
            invalid -> inline field errors listing every violation; nothing persisted
       stale row -> 已过时（历史） + pointer; import disabled (D-PVSTALE)
  -> Assignment detail (D-PVDETAIL): package identity, scores, findings, outcome, evidence history
  -> 对齐与交付 status pair (D-PVSTATUS): 技术校验状态 chip + live 产品验证状态 chip
  -> technical-evaluation report / delivery print report status lines (D-PVSTATUS)
Error paths: incomplete package selected -> not selectable with named gap; schema violation -> requirement errors listing fields; stale assignment import -> named supersession guidance; permission -> safe not-found; request failure -> named error with retry.
Cancel/back: import form collapses with nothing written; 创建评审分派 modal cancels with nothing written; assignments persist server-side.
```

- Success exit: every in-scope unit concluded with imported evidence; overall status 通过/失败/未完成 displayed honestly.
- Permission denied: safe not-found without existence disclosure.

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| 产品验证 region (in 运行证据 panel) | Overview: rubric revision, overall status, per-unit assignment states, entry actions | `GET /projects/{id}/product-validation` | 创建评审分派; 导入量表证据; expand detail | Assignment/evidence created; no navigation | Status markers, chips/list, empty state |
| 创建评审分派 modal | Bounded package selection with binding summary | Overview payload + create endpoint | Select package; confirm; cancel | Assignment created or existing returned | Modal + list + Button |
| Import form (inline, expandable) | Structured rubric capture with full-schema validation display | Assignment + import endpoint | Fill scores/notes/findings/rework/attestation; upload document; submit/collapse | Evidence imported; outcome computed | F006 disclosure, Form fields, File input, Button |
| Assignment detail (expandable) | Evidence and outcome inspection | `GET .../assignments/{assignment_id}` | Expand; inspect history | Read-only | Disclosure rows, status markers |
| 对齐与交付 status pair | Live product-validation chip beside technical chip | Existing alignment read (field now live) | Read-only | None | Existing chip pair |
| Report status lines (technical-evaluation report, delivery print report) | Live status sentence with bounded-conclusion wording | Existing report reads (field now live) | Print (existing) | Paper/PDF | Print stylesheet, existing routes |
| Small-screen notice | Defer create/import/detail below 1024px | Viewport | Read summary | Desktop for actions | Desktop gate |

Component responsibility rule unchanged: networking/error normalization in the shared API layer; no component owns business-state transitions; all F010 surfaces are synchronous reads/imports with no streaming.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Region | Not evaluated | No assignments | 「尚未进行产品验证」 + 创建评审分派 | Create (desktop) | Overview (empty) | First assignment |
| Region | Loading | Entry/refresh | Skeleton preserving region layout | Wait | Overview request | Rendered |
| Region | Error | Request failure | Named error with retry | Retry/back | Error mapping | Rendered |
| Region | In progress | Assignments exist, evidence pending | 进行中 chip + per-unit 待证据 rows | Import; inspect | Overview | Concluded units |
| Region | Pending evidence | Unit awaiting rubric | 待证据 chip per unit | 导入量表证据 (desktop) | Overview/detail | Outcome |
| Region | Passed | All units passed | 通过 chip + bounded-conclusion sentence | Inspect detail | Overview | Portfolio claim supported |
| Region | Failed | Any unit failed | 失败 chip (definitive) + failing unit(s) named | Inspect detail | Overview | Recovery via new rubric revision or regeneration flow |
| Region | Not complete | Unit concluded without evidence / stale | 未完成 chip + reason | Fix new assignment; inspect | Overview | Complete the set |
| Region | Stale (historical) | Bound package superseded | 已过时（历史） + pointer; import disabled | Read history | Overview/detail | New assignment |
| Import form | Submitting | Submit | Loading + disabled submit | Wait | Import request | Outcome or errors |
| Import form | Schema violation | Server requirement error | Inline field errors listing every violating field; nothing persisted | Correct; resubmit | Error mapping | Valid import |
| Import form | Duplicate revision | Same rubric revision re-imported | 「该量表版本已导入」; existing evidence shown | Inspect | Idempotent import | Read outcome |
| Import form | Stale assignment | Package superseded | Named supersession guidance; import blocked | Fix new assignment | Error mapping | New assignment |
| Detail | Evidence history | Superseded rubric revisions | 历史版本 markers; prior outcomes readable | Read | Detail payload | Context |
| Modal | No complete package | Nothing selectable | 「暂无可评审的完整单元包」 + named gap per package | Close; complete generation first | Overview | Technically complete package |
| Global | Permission denied | Non-owner | Safe not-found | Back to own projects | No disclosure | Project list |

Assessed states: Initial, Loaded, Submitting (import — loading + disabled), Pending, Pass, Fail, Not-complete, Stale-historical, Validation error, Duplicate-idempotent, Unauthorized, Forbidden-as-not-found, Error-retry, Empty-not-evaluated.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| 创建评审分派 (package) | Selection required | Package completeness re-checked; incomplete → REQUIREMENT naming the gap; duplicate → existing assignment returned | Focus to package list on open; confirm disabled while submitting | Idempotent identity tuple; repeat returns existing with notice (Spec D8) |
| 导入量表证据 | Scores 1–5 integers; notes non-empty; severe findings have class+lesson+evidence; rework reason when true; attestation fields present; document file chosen | Full rubric-schema validation; every violating field listed at once; invalid persists nothing; duplicate revision idempotent; stale blocked | Focus to first score on expand; errors listed in order, focus to first error | Idempotent per (assignment, rubric revision); corrected revision supersedes, prior retained (Spec D8) |
| Detail/report reads | None (read-only) | Standard reads | — | Read-only refresh |

Client validation never replaces server constraints; the server remains the rubric-schema authority.

## Frontend/Backend Contract

- Request/response: typed client over `GET /projects/{id}/product-validation`, `POST .../product-validation/assignments`, `POST .../product-validation/assignments/{assignment_id}/evidence`, `GET .../product-validation/assignments/{assignment_id}`; existing alignment/technical-evaluation/delivery report reads gain the live `product_validation_status` value (field name unchanged — constant becomes computed). Exact DTO field names frozen schema-first (TypeScript interfaces per codebase convention) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: shared API client token; 401 → sign-in; 404 → safe not-found; REQUIREMENT → inline guidance naming the violated rule(s); UNEXPECTED → page-level safe error with correlation id.
- Pagination: `N/A - bounded lists` (assignments bounded by dataset units and package identity).
- Optimistic update/rollback: `N/A - authoritative server state governs; reads refresh after import; no polling (synchronous imports and deterministic computation)`.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in | Sign in | Return | Yes |
| 404 (ownership/assignment id) | Safe not-found | Back / region | None disclosed | Yes |
| REQUIREMENT (rubric schema violation) | Inline field errors listing every violating field | Correct; resubmit | Valid import | Yes |
| REQUIREMENT (incomplete package / stale assignment) | Named gap or supersession guidance | Complete generation / fix new assignment | Eligible state | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

No quota/provider classes exist on this surface (zero model calls). Errors never collapse into one vague toast; mapping follows `docs/API.md` and `docs/UX.md`.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full region, import form, expandable detail, live status chips everywhere | All actions keyboard operable | Score/finding text wraps; evidence-history list scrolls within region |

| Reduced <1024px | Overall status chip, per-unit outcomes, bounded-conclusion sentence (read-only) | 创建评审分派, import form, expanded detail defer behind desktop-required notice | Single reading sequence |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md mandate that status and recovery information survive small screens.

## Accessibility

- Semantic structure: the region is a labelled section (产品验证) inside the evidence panel; assignment detail is a labelled disclosure group; statuses are text+marker (未评估/进行中/待证据/未完成/通过/失败/已过时（历史）), never color-alone; report status lines use semantic text within the existing report markup.
- Keyboard and focus: region entry, 创建评审分派 modal (focus trap, focus to package list, return to trigger), import form (focus to first score, errors associated with fields, focus to first error), disclosure expansion, and report-route operation are keyboard reachable in reading order; server errors move focus to the region alert.
- Live announcements: import outcome (通过/失败/未完成) announced politely on settle; disclosure expansion is passive.
- Contrast/non-color cues: token set >=4.5:1 body / >=3:1 components; outcome and state distinctions carried in language and markers.
- Motion/reduced motion: no animation-dependent meaning; skeletons honor reduced motion.
- Verification approach: automated a11y checks in component tests plus a scripted keyboard pass over open-region → create-assignment → import-evidence (valid and invalid) → inspect-detail → status-pair path, recorded in the Test Design execution snapshot.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, modal, alerts, chips/status markers, skeleton/empty/error, form fields, file input | F001–F008 foundations | Reuse | All variants exist | None |
| Progressive evidence disclosure / detail rows | F006 patterns | Compose (assignment detail + evidence-revision history) | Same reading rules | None |
| Region-in-evidence-panel composition | F009 技术评估 region pattern | Compose (sibling 产品验证 region) | Exactly this pattern | None |
| Product-validation status label map | Existing label-map convention in `lib/api.ts` | Compose (new map, existing convention) | Consistent with existing label maps | None |
| Status pair chips (对齐与交付) | F008 status pair | Reuse (second chip becomes live) | Surface exists | None |

No new tokens; no Feature-local visual language.

## UI Acceptance Links

- AC-001 rubric schema governance: import-form validation rows, REQUIREMENT error listing every field
- AC-002 assignment binding + idempotency: D-PVCREATE modal binding summary, 「该分派已存在」 notice, named-gap non-selectable packages
- AC-003 deterministic computation: outcome renders immediately from imported evidence; identical evidence identical outcome
- AC-004 failed/not-complete explicitness: 失败/未完成 chips, per-unit pending rows, blocked teacher-usability wording
- AC-005 separate display: D-PVSTATUS chips and report lines; technical pass + product fail both visible
- AC-006 staleness: D-PVSTALE rows with pointer; not-complete until new assignment
- AC-007 import idempotency + revision supersession: 「该量表版本已导入」 notice, 历史版本 markers
- AC-008 privacy/publication boundary: pseudonymous evaluator reference only; original document never rendered inline in publishable surfaces; bounded-conclusion sentence
- AC-009 non-disclosure: permission rows
- AC-010 real-review evidence: imported assignments with retained originals visible in detail; not_complete fallback display

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact DTO field names for overview/create/import/detail | Non-critical | Implementation assignee | Frozen schema-first (TypeScript interfaces) in the first implementation task within Spec semantics | RESOLVED |
| UIQ-002 | Rubric hand-out document format for the evaluator | Non-critical | Implementation assignee | A generated printable rubric sheet (zh-Hans labels, fixed schema order) exported from the assignment detail; paper or PDF handled by the evaluator; format details in the Implementation Plan | RESOLVED |
| UIQ-003 | Whether a dedicated product-validation print report is added | Non-critical | Implementation assignee | No — F012 owns the deployed portfolio surface; F010 carries the status line in existing reports only | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, complete User Flow explicit | YES | Flow incl. create assignment, hand-out/export, import evidence (valid/invalid/duplicate/stale), inspect detail, status surfaces, permission and failure paths |
| UR-02 | Each affected Page/Screen/Component has explicit responsibility | YES | Responsibilities table, 7 surfaces |
| UR-03 | UI State Matrix covers applicable states | YES | 16-row matrix covering the full Spec D6 vocabulary incl. stale-historical, not-complete, schema-violation, duplicate-idempotent |
| UR-04 | Permission, validation, duplicate submit, cancel, back, recovery explicit | YES | Forms table (create/import), permission rows, idempotent notices, collapse/cancel behavior |
| UR-05 | Frontend/Backend contract and error mapping explicit | YES | Contract section + 5-row error mapping; unchanged field name on existing reads |
| UR-06 | Responsive behavior verifiable | YES | 1024px table preserving status/outcomes read-only below breakpoint |
| UR-07 | Accessibility behavior verifiable | YES | A11y section: section semantics, focus rules, non-color statuses, verification approach |
| UR-08 | Design System checked with explicit reuse/extension decisions | YES | Reuse table; composition only, no extensions |
| UR-09 | UI Acceptance linked to `AC-*` | YES | All 10 ACs mapped |
| UR-10 | No Critical UI Open Question open/deferred | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `66a3c94329a9`) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 352db99` + this artifact `ux-ui-f010-r1` (hash below)
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `66a3c94329a9`
- Validated UX/UI revision: `ux-ui-f010-r1` @ (hash recorded in `STAGE.md` Gate Snapshot)
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01 (Spec approval D1–D9 covers the evidence-experience direction and no-new-tab rule; this artifact's interface decisions compose existing patterns within it)
- Approval scope: F010 UX/UI refinement at `ux-ui-f010-r1`

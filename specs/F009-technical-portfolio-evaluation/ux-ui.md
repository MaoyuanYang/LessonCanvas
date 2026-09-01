# Feature UX/UI: F009 Technical Portfolio Evaluation

## Metadata

- Spec/Issue: `specs/F009-technical-portfolio-evaluation/spec.md` / [GitHub Issue #18](https://github.com/MaoyuanYang/LessonCanvas/issues/18)
- Validated Spec revision: `SPEC READY` PASS, content hash `15803bdc1837`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md` (inspect-technical-evidence flow), `docs/UI.md` (evidence region rules, print convention), `docs/DESIGN_SYSTEM.md` (status markers, evidence disclosure, printable report pattern), `docs/FRONTEND.md` at base `main @ 13dbee6`
- UX/UI artifact revision/change-log ID: `ux-ui-f009-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced experience below 1024px (F001 D-BP)
- Existing UX/UI/Design System references: 证据 workspace panel and its run inventory/disclosure patterns (F006), status marker + label maps, F008 print report route and shared print stylesheet, ui foundations

### UI-level decisions (2026-09-01, `YMY / Project Owner`)

| ID | Decision | Resolution |
| --- | --- | --- |
| D-EVALREGION | Evaluation entry | A 「技术评估」 summary region at the top of the existing 证据 (evidence) panel — no new workspace tab (Spec D11). The region always shows, in order: dataset revision, per-unit × per-pass state (单元 × 遍次), overall blocking outcome per pass, and links to the report view and pass detail. |
| D-EVALCRIT | Criterion outcomes | Pass detail renders blocking criteria as a labelled list grouped 阻断判定 (C-TRACE-1..C-MEM-1 in teacher-readable names) with 通过 / 未通过 / 证据缺失 text+icon markers, each expandable to its evidence links (runs, artifacts, versions, trace references) using the F006 disclosure pattern. Diagnostic metrics (延迟、成本、方差、覆盖、模型意见) render in a separate 诊断指标 (非判定) group with raw values and an explicit 非阻断 label; they never carry pass/fail markers. |
| D-EVALCOMPARE | Cross-pass comparison | When passes share unit + dataset revision + model configuration, the report and pass views show a side-by-side per-pass column comparison of raw criterion outcomes and diagnostic metrics with no aggregation row. Any incomparability renders 对比不可用 with the precise reason (不同配置 / 不同数据集版本 / 不同单元); nothing is merged or averaged (Spec D3, D5). |
| D-EVALREPORT | Printable report | 打印技术评估报告 opens a dedicated print-styled route in a new tab composing the F008 print pattern: bound versions, dataset revision, model configuration snapshot, memory state, per-unit per-pass criterion outcome table, fault-scenario outcomes, cost/latency evidence, and the explicit technical-vs-product status sentence (产品验证状态：未评估，直至 F010). Print stylesheet hides app chrome; no new rendering dependency. |
| D-EVALCREATE | Starting a pass | The region offers 启动评估: a modal selecting unit (三单元), pass index (第 1/2 遍), and mode (确定性 / 真实模型). Live mode states the cost consequence explicitly («真实模型运行将产生实际模型费用») before confirm. Duplicate submission returns the existing pass with an 「该遍次已存在」 notice — never a silent second run (Spec D10). |
| D-EVALPROG | Active-pass progress | Active evaluation passes show state chips (排队中 / 进行中 / 部分证据) refreshed by polling, plus a link to the underlying runs already listed by the evidence inventory below — evaluation itself adds no new streaming surface and never streams private content of other projects. Provider-unavailable passes show 供应商不可用 with retained partial evidence and the same-pass resume path. |
| D-EVALSMALL | Small-screen boundary | Below 1024px, the region keeps the state chips, overall outcomes, and report availability; the full criterion/comparison detail and the print report defer behind the existing desktop-required notice. |

No new tokens; no new visual language; 通过/未通过/证据缺失, 阻断/诊断, 排队中/进行中 are text+marker distinctions per the shared status-language rule.

These are interface refinements within Spec behavior (D1–D11); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: workspace owner (project owner/evaluator; teacher classroom use is out of scope)
- Goal: start controlled technical evaluation passes on the fixed dataset, inspect per-criterion evidence honestly, compare passes, and produce a printable technical report
- Entry points: 证据 workspace panel (技术评估 region); report route opened from the region
- Preconditions: dataset package loads (manifest valid); live mode requires the live provider configuration

```text
Workspace -> 证据 panel
  -> 技术评估 region (D-EVALREGION): dataset revision + per-unit × per-pass states + overall outcomes
       empty -> 「尚未运行技术评估」 + single next action 启动评估
       启动评估 (D-EVALCREATE): modal (unit / pass index / mode) -> live mode cost sentence -> confirm
            duplicate -> 「该遍次已存在」 notice, existing pass shown
       active pass -> state chips + link to underlying runs in evidence inventory (D-EVALPROG)
  -> Pass detail (D-EVALCRIT): 阻断判定 group (expand evidence) + 诊断指标 (非判定) group
       未通过/证据缺失 criterion stays explicit; no aggregate score masks it
  -> Comparison (D-EVALCOMPARE): side-by-side passes of same unit+revision+config, else 对比不可用 with reason
  -> 打印技术评估报告 (D-EVALREPORT): print-styled route, browser print/save-PDF
Error paths: dataset governance failure -> requirement notice naming the rule, no pass starts; provider unavailable -> 供应商不可用 + partial evidence + same-pass resume; quota -> named quota notice; permission -> safe not-found; request failure -> named error with retry.
Cancel/back: 启动评估 modal cancels with nothing written; leaving the region never cancels an active pass (state persists server-side).
```

- Success exit: evaluation set with explicit per-criterion outcomes; report printed with honest statuses.
- Permission denied: safe not-found without existence disclosure.

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| 技术评估 region (in 证据 panel) | Overview: dataset revision, unit × pass states, overall outcomes, entry actions | `GET /projects/{id}/technical-evaluation` | 启动评估; open pass detail; open report | Evaluation pass created; navigation | Status markers, chips/list, empty state |
| 启动评估 modal | Bounded pass creation with consequence text | Overview payload + create endpoint | Select unit/pass/mode; confirm; cancel | Pass created or existing returned | Modal + radio/select + Button |
| Pass detail view | Per-criterion outcomes with evidence; diagnostic metrics | `GET .../runs/{evaluation_run_id}` | Expand evidence; follow run/artifact links | Evidence inspection | F006 disclosure rows, status markers |
| Comparison view (within detail/report) | Side-by-side comparable passes | Overview/detail payloads | Inspect; no mutating actions | Diagnosis | Density table |
| Technical report route | Print-styled report across the evaluation set | `GET .../technical-evaluation/report` | Browser print/save | Paper/PDF output | Print stylesheet + semantic report markup |
| Small-screen notice | Defer detail/report below 1024px | Viewport | Read summary | Desktop for depth | Desktop gate |

Component responsibility rule unchanged: networking/error normalization in the shared API layer; no component owns business-state transitions; the report route is read-only.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| Region | Not run | No evaluation passes | 「尚未运行技术评估」 + 启动评估 | Start | Overview (empty) | First pass |
| Region | Loading | Entry/refresh | Skeleton preserving region layout | Wait | Overview request | Rendered |
| Region | Error | Request failure | Named error with retry | Retry/back | Error mapping | Rendered |
| Region | Queued/Active passes | Pass created/running | 排队中/进行中 chips + underlying-run links | Inspect; wait | Polling overview | Completed state |
| Region | Partial evidence | Interrupted pass | 部分证据 chip + retained evidence | Inspect; resume same pass | Overview/detail | Complete or settle |
| Region | Provider unavailable | Live provider failure | 供应商不可用 + partial evidence + resume path | 恢复本遍次 | Error mapping | Same-pass resume |
| Region | Superseded configuration | Newer dataset revision/config exists | 旧结果标记为「配置已过时」; still readable | Read historical | Overview | New revision passes |
| Pass detail | Pass outcome | Completed pass | Overall 通过/未通过 + per-criterion list (D-EVALCRIT) | Expand evidence | Detail payload | Diagnose failure |
| Criterion | Fail | Unmet blocking criterion | 未通过 marker + rule name + evidence links | Inspect; follow links | Detail payload | Recovery path in owning flow |
| Criterion | Missing evidence | Unevaluable criterion | 证据缺失 + precise reason (e.g., provider cannot report stream usage) | Inspect reason | Detail payload | Re-run or accept as evidence gap |
| Diagnostic group | Steady | Any recorded metrics | Raw values + 非阻断 label; never pass/fail markers | Inspect | Detail payload | Context only |
| Comparison | Comparable | Same unit+revision+config | Side-by-side columns, no aggregate row | Inspect | Overview/report | Variance visible |
| Comparison | Not comparable | Differing unit/revision/config | 对比不可用 + precise reason | None | Overview/report | Nothing merged |
| Report | Loading/rendered | Open/print | Report renders fully before print guidance | Print/save | Report data | Output |
| Modal | Reasonable input | Open | Unit/pass/mode selectors; live cost sentence | Confirm/cancel | Client + server | Created or notice |
| Modal | Duplicate pass | Existing identity tuple | 「该遍次已存在」; existing pass shown | Open existing | Idempotent create | Inspect |
| Global | Permission denied | Non-owner | Safe not-found | Back to own projects | No disclosure | Project list |

Assessed states: Initial, Loaded, Submitting (create — loading + disabled), Queued/Active, Partial, Provider failure, Superseded-stale (configuration), Missing evidence, Unauthorized, Forbidden-as-not-found, Error-retry, Empty-not-run.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| 启动评估 (unit/pass/mode) | All fields required; pass index within defined range | Unit/revision governance + mode/adapter eligibility; ineligible → REQUIREMENT naming the rule; quota → quota class | Focus to first selector on open; confirm disabled while submitting | Idempotent identity tuple; repeat returns existing pass with notice (Spec D10) |
| 打印技术评估报告 | Report data loaded | Read-only | New tab; no focus steal | Read-only refresh |

Client validation never replaces server constraints.

## Frontend/Backend Contract

- Request/response: typed client over `GET /projects/{id}/technical-evaluation`, `POST .../technical-evaluation/runs`, `GET .../technical-evaluation/runs/{evaluation_run_id}`, `GET .../technical-evaluation/report`. Exact DTO field names frozen schema-first (TypeScript interfaces per codebase convention) in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: shared API client token; 401 → sign-in; 404 → safe not-found; REQUIREMENT → inline guidance naming the governance rule; PROVIDER class → provider-unavailable state with same-pass resume; quota class → named quota notice.
- Pagination: `N/A - bounded lists` (units and passes bounded by definition: 3 units × 2 passes + fault scenarios).
- Optimistic update/rollback: `N/A - authoritative server state governs; reads refresh after create/settle; polling only while non-terminal passes exist`.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in | Sign in | Return | Yes |
| 404 (ownership/evaluation id) | Safe not-found | Back / region | None disclosed | Yes |
| REQUIREMENT (dataset governance / ineligible mode or pass) | Inline message naming the rule | Fix configuration; retry | Governance or config fix | Yes |
| PROVIDER_TRANSIENT / provider unavailable | 供应商不可用 + retained partial evidence | 恢复本遍次 | Same-pass resume | Yes |
| QUOTA_EXCEEDED | Named quota notice with the evaluation-project rule | Adjust environment quota (owner action documented) | Retry after adjustment | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path later | Yes |

Errors never collapse into one vague toast; mapping follows `docs/API.md` and `docs/UX.md`.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full region, pass detail with evidence expansion, comparison columns, print report | All actions keyboard operable | Metric text wraps; comparison table scrolls within region, never horizontally past content |
| Reduced <1024px | State chips, overall outcomes, report availability preserved | Criterion detail, comparison, and print report defer behind desktop-required notice | Single reading sequence |

Breakpoint: 1024px (F001 D-BP), implementing the UX.md mandate that status and recovery information survive small screens.

## Accessibility

- Semantic structure: the region is a labelled section (技术评估) inside the evidence panel; pass detail is a labelled list grouped by heading (阻断判定 / 诊断指标); states and outcomes are text+marker (排队中/进行中/部分证据/通过/未通过/证据缺失/供应商不可用/配置已过时/对比不可用), never color-alone; the report route uses semantic headings and the shared print stylesheet.
- Keyboard and focus: region entry, 启动评估 modal (focus trap, focus to first selector, return to trigger), evidence disclosure, report-route operation are keyboard reachable in reading order; state-chip updates announced politely; server errors move focus to the region alert.
- Live announcements: pass state transitions (queued → active → terminal) announced politely on polled change; disclosure expansion is passive.
- Contrast/non-color cues: token set >=4.5:1 body / >=3:1 components; outcome and state distinctions carried in language and markers.
- Motion/reduced motion: no animation-dependent meaning; skeletons honor reduced motion.
- Verification approach: automated a11y checks in component tests plus a scripted keyboard pass over open-region → start-pass modal → inspect-criterion → compare → report path, recorded in the Test Design execution snapshot.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, modal, alerts, chips/status markers, skeleton/empty/error | F001–F008 foundations | Reuse | All variants exist | None |
| Progressive evidence disclosure / density tables | F006 patterns | Compose (criterion outcomes + comparison) | Same reading rules | None |
| Print stylesheet + report route pattern | F008 shared print pattern | Compose (second printable surface) | Pattern exists for exactly this | None |
| Evaluation status label maps | Existing label-map convention in `lib/api.ts` | Compose (new map, existing convention) | Consistent with EVIDENCE_KIND_LABELS etc. | None |

No new tokens; no Feature-local visual language.

## UI Acceptance Links

- AC-001 dataset governance: requirement notice path (governance failure), revision display
- AC-002 result binding: pass-detail evidence links (versions, runs, artifacts, config, trace)
- AC-003 deterministic criterion outcomes: D-EVALCRIT list with evidence expansion
- AC-004/AC-005/AC-006/AC-007 fault-evidence visibility: criterion rows 未通过/证据缺失 with links to the recorded scenario evidence
- AC-008 memory state recorded: report field and pass-detail config block
- AC-009 two live passes side by side without masking: D-EVALCOMPARE columns
- AC-010 failure never masked, diagnostics labeled: D-EVALCRIT groups + 非阻断 labels
- AC-011 model-opinion boundary: 诊断指标 group never carries pass/fail markers
- AC-012 token/cost capture display: cost metrics 未记录 vs values per the NULL-means-not-recorded rule
- AC-013 evidence experience + report: D-EVALREGION, D-EVALREPORT
- AC-014 comparison-unavailable state: D-EVALCOMPARE incomparable rows
- AC-015 non-disclosure: permission rows; deletion owned by project flows

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact DTO field names for overview/create/detail/report | Non-critical | Implementation assignee | Frozen schema-first (TypeScript interfaces) in the first implementation task within Spec semantics | RESOLVED |
| UIQ-002 | Whether evaluation gets narration (解释 narration) | Non-critical | Implementation assignee | No — evaluation is an owner/technical surface; explanation stays with the existing evidence narration over underlying runs; no new narration cost surface | RESOLVED |
| UIQ-003 | Print trigger details | Non-critical | Implementation assignee | Same as F008: report renders fully first, one-line 打印提示, browser print engine | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, complete User Flow explicit | YES | Flow incl. start pass, inspect outcomes, compare, report, permission and failure paths |
| UR-02 | Each affected Page/Screen/Component has explicit responsibility | YES | Responsibilities table, 6 surfaces |
| UR-03 | UI State Matrix covers applicable states | YES | 18-row matrix covering the full Spec state vocabulary incl. missing-evidence, superseded-configuration, comparison-unavailable, provider-unavailable |
| UR-04 | Permission, validation, duplicate submit, cancel, back, recovery explicit | YES | Forms table (create/print), permission rows, idempotent-duplicate notice |
| UR-05 | Frontend/Backend contract and error mapping explicit | YES | Contract section + 6-row error mapping |
| UR-06 | Responsive behavior verifiable | YES | 1024px table preserving states/outcomes/report availability |
| UR-07 | Accessibility behavior verifiable | YES | A11y section: section semantics, focus rules, non-color statuses, verification approach |
| UR-08 | Design System checked with explicit reuse/extension decisions | YES | Reuse table; composition only, no extensions |
| UR-09 | UI Acceptance linked to `AC-*` | YES | All 15 ACs mapped |
| UR-10 | No Critical UI Open Question open/deferred | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `15803bdc1837`) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 13dbee6` + this artifact `ux-ui-f009-r1` (hash below)
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `15803bdc1837`
- Validated UX/UI revision: `ux-ui-f009-r1` @ `9ecd8faab98e`
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01 (Spec approval covers the D11 evidence-experience direction; this artifact's interface decisions compose existing patterns within it)
- Approval scope: F009 UX/UI refinement at `ux-ui-f009-r1`

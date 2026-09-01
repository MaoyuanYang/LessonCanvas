# Feature UX/UI: F011 Public Multi-Account Guardrails

## Metadata

- Spec/Issue: `specs/F011-public-multi-account-guardrails/spec.md` / [GitHub Issue #22](https://github.com/MaoyuanYang/LessonCanvas/issues/22)
- Validated Spec revision: `SPEC READY` PASS, content hash `d27deee5bfc8`
- Upstream input manifest link/revisions: SPEC READY Gate Record in the Spec; `docs/UX.md` (account-and-usage area, state/feedback principles incl. quota/provider failure, small-screen boundary), `docs/UI.md` (account region rules, feedback treatment, disabled-with-reason), `docs/DESIGN_SYSTEM.md` (status markers, disclosure, chips), `docs/FRONTEND.md` at base `main @ 683172b`
- UX/UI artifact revision/change-log ID: `ux-ui-f011-r1` (this document, first revision)
- UI Impact: `YES`
- `UI READY` Status: `PASS`
- Affected platforms/devices: desktop-first Web; canonical reduced read-only experience below 1024px (F001 D-BP, F002 D8)
- Existing UX/UI/Design System references: account page (identity + deletion), workspace panels' error/disabled patterns, F006 progressive disclosure, status marker + label maps, desktop gate, ui foundations

### UI-level decisions

| ID | Decision | Resolution |
| --- | --- | --- |
| D-ACCTREGION | Account surface composition | The existing 账号与数据 page (global navigation, no new top-level tab) is extended into labelled sections in reading order: 登录身份 (existing line), 使用与限额 (D-USAGE), 隐私与运营访问 (D-DISCLOSE), 敏感操作审计 (D-AUDITLIST), 删除账号 (existing destructive region, extended by D-DELEXT). Each section is a semantic `<section>` with a heading; the page remains one calm reading sequence per UI.md layout principles. |
| D-USAGE | Usage and limits region | 使用与限额 shows every D2 limit as one row: 请求速率（当前窗口） current/max + 窗口重置倒计时, 并发生成运行 x/2, 并发实时流 x/6, 今日上传量 x MB/200 MB, plus the existing cumulative quotas (项目数 x/5, 规划运行数 x/50, 讲解生成 x/50) so the teacher sees every authoritative boundary in one place. Read-only with a manual 刷新 action; data from `GET /account/usage`. No projected warnings beyond the named numbers. |
| D-LIMITERR | Limit and admission feedback | Rate rejection (429) surfaces where the request was made as a named 速率限制 inline alert: the limit name, 已达上限 statement, and 自动恢复倒计时 (`retry_after`), with a link to 使用与限额 — never a generic toast, never a retry storm (retry is disabled while the window is saturated). Concurrent-run admission rejection surfaces at the generation/deck/exercise start controls through the established disabled-with-reason treatment: 已有 N 个生成运行进行中 + a pointer/link to the active run(s) and guidance (等待完成、安全停止或按 F007 版本语义处理); the start control re-enables based on authoritative state. SSE stream cap rejection surfaces in the stream region with the same named-limit pattern. |
| D-DISCLOSE | Operator-access and privacy disclosure | 隐私与运营访问 states, in plain zh-Hans: (1) workspace content is only ever read by its owner through the app; (2) there is no in-app operator account or content-reading path (D3); (3) for troubleshooting, the project operator reaches the underlying managed infrastructure (database / object storage / identity / model accounts) through the providers' administrative consoles — defense in depth, content never copied out; (4) after account deletion a minimal content-free security ledger (操作类型、时间、工作区标识 only — never content, filenames, or traces) is retained per D4(b) and disclosed here. Wording is static page copy, not per-request data. |
| D-AUDITLIST | Sensitive-action audit list | 敏感操作审计 uses the F006 progressive-disclosure pattern (collapsed by default, expand on demand): a bounded recent list of the workspace's audit events — 下载 (artifact/evidence documents), 删除, 证据导入, and the existing audited actions — each rendered as action kind + target label + time, never payloads or content; cursor pagination via `GET /account/audit`. Empty state: 暂无敏感操作记录. |
| D-DELEXT | Deletion states and repair | Project deletion keeps its existing flow and adds the completeness truth: while a store remains, the project list/workspace shows 删除未完成 with the named store (数据库残留 / 对象存储残留) and a 重试删除 action (idempotent re-issue); at zero residuals it settles the existing deleted state. Account deletion response extends the existing result handling: partial failure lists the remaining store and offers 重试修复; the Clerk step keeps its existing separate status line. Source delete with an object-store failure shows the source row state 删除未完成（存储残留，可修复） with a 重试 action instead of silently disappearing (Spec D5). |
| D-SMALL | Small-screen boundary | Below 1024px the account page preserves the reading sequence with: identity line, a compact usage summary (per-limit current/max chips without countdown interaction), the disclosure text, and deletion availability (destructive action stays desktop-gated per existing pattern); the audit list and repair actions defer behind the existing desktop-required notice. Limit/admission error alerts remain fully visible and readable wherever they occur (status and recovery information survives small screens per UX.md). |

No new tokens; no new visual language; statuses are text+marker distinctions; all limit/deletion states use shared status language.

These are interface refinements within Spec behavior (D1–D11); they change no Spec observable behavior, so `SPEC READY` remains valid.

## User Goal and Flow

- User/role: workspace owner (teacher); no operator role exists in-app (D3)
- Goal: understand and trust the boundaries — see current usage against every limit, understand what was denied and how to recover, inspect who can access what, verify sensitive actions, and delete everything completely
- Entry points: global account navigation (账号与数据); limit/admission feedback inline in the flow where a denial occurs; deletion states in project list/workspace and sources panel

```text
Account page (账号与数据)
  -> 使用与限额 (D-USAGE): every limit row with current consumption + reset countdown
  -> 隐私与运营访问 (D-DISCLOSE): operator model + retained-ledger disclosure
  -> 敏感操作审计 (D-AUDITLIST): expand -> bounded audit list -> paginate
  -> 删除账号 (existing destructive region, D-DELEXT extension)
In-flow denial
  -> rate limited -> named 速率限制 alert + countdown + 使用与限额 link
  -> concurrent-run rejected -> disabled-with-reason + active-run pointer
  -> SSE cap -> named limit in stream region
Deletion paths
  -> project delete -> complete | 删除未完成(named store) -> 重试删除 -> complete
  -> source delete -> complete | 删除未完成（存储残留） -> 重试
  -> account delete -> purged(+clerk status) | purge_failed(named store) -> 重试修复
Error paths: usage/audit request failure -> named error + retry; permission -> safe not-found.
Cancel/back: audit list collapses; deletion confirmations keep existing explicit-consequence modals.
```

- Success exit: limits understood; denial recovered; deletion reaches complete (or visible repairable partial).
- Permission denied: safe not-found without existence disclosure.

## Page / Screen / Component Responsibilities

| Surface | Responsibility | Inputs/source | User actions | Navigation/output | Reused component |
| --- | --- | --- | --- | --- | --- |
| 使用与限额 section (account) | Present every authoritative limit with current consumption and reset | `GET /account/usage` | 刷新 | None | List rows, status markers, chips |
| 隐私与运营访问 section (account) | Static disclosure copy (D3/D4) | Static content | Read | None | Typography, section |
| 敏感操作审计 section (account) | Owner-inspectable bounded audit list | `GET /account/audit` | Expand/collapse; paginate | None | F006 disclosure, list, cursor pagination |
| 删除账号 region (account, extended) | Destructive deletion with completeness + repair | Existing DELETE /account + status reads | 删除账号; 重试修复 | Sign-out on success | Existing region, ConfirmModal, Alert |
| Limit/admission feedback (in-flow) | Named denial with recovery at the point of action | Existing endpoints' new 429/admission errors + run state | Wait/countdown; follow active-run pointer; 使用与限额 | Active run / usage | Inline alert, disabled-with-reason, countdown text |
| Deletion states (project list/workspace, sources) | Visible partial-deletion truth + repair | Existing status reads + completeness fields | 重试删除 / 重试 | Settled state | Status markers, existing list rows |
| Small-screen notice | Defer audit list + repair actions below 1024px | Viewport | Read summary | Desktop for actions | Desktop gate |

Component responsibility rule unchanged: networking/error normalization in the shared API layer; no component owns business-state transitions; no streaming on F011 surfaces.

## UI State Matrix

| Surface | State | Trigger | Visible UI/message | Allowed action | API/data | Recovery/next |
| --- | --- | --- | --- | --- | --- | --- |
| 使用与限额 | Loading | Entry/refresh | Skeleton rows | Wait | Usage request | Rendered |
| 使用与限额 | Loaded | Success | Every limit row current/max (+countdown for windowed) | 刷新 | Usage read | Current truth |
| 使用与限额 | Error | Request failure | Named error + retry | Retry | Error mapping | Rendered |
| In-flow | Rate limited | 429 from any action | 速率限制 alert: limit name, 已达上限, countdown, usage link | Wait (retry disabled while saturated) | Error body `retry_after` | Window reset |
| In-flow | Concurrent-run rejected | Admission error at family start | Disabled-with-reason: 已有 N 个运行进行中 + active-run pointer | Inspect active run; wait; supersession path | Run state + admission error | Start after settle |
| In-flow | SSE cap | Stream connect rejected | Named limit in stream region with countdown | Wait; close another stream | Error body | Stream available |
| 敏感操作审计 | Collapsed/Empty | Default / no events | 暂无敏感操作记录 | Expand | Audit read | List |
| 敏感操作审计 | Loaded | Expand success | Bounded rows (kind + target + time) | Paginate | Cursor pagination | Older events |
| 敏感操作审计 | Error | Request failure | Named error + retry | Retry | Error mapping | List |
| Project deletion | Complete | Zero residuals | Existing deleted state | — | Status read | Terminal |
| Project deletion | Partial (deleting) | Residual store | 删除未完成 + named store | 重试删除 | Status + completeness fields | Complete |
| Source deletion | Complete | Object + row gone | Existing removal | — | Sources read | Terminal |
| Source deletion | Partial | Object-store failure | 删除未完成（存储残留，可修复） | 重试 | Sources read | Complete |
| Account deletion | Purged | All stores + Clerk ok | Existing success handling (sign-out) | — | Deletion response | Terminal |
| Account deletion | Partial (purge_failed) | Store residual | Remaining store named + 重试修复 | 重试修复 | Deletion response/status | Purged |
| Account deletion | Clerk-only failure | Existing clerk_failed | Existing warning + retry | Retry | Existing | Full deletion |
| Global | Permission denied | Non-owner | Safe not-found | Back to own boundary | No disclosure | Project list |

Assessed states: Initial, Loaded, Loading, Submitting (deletion/repair), Disabled-with-reason, Rate-limited countdown, Admission-rejected, Partial-failure repairable, Empty, Error-retry, Unauthorized, Forbidden-as-not-found, Terminal-complete.

## Forms, Validation, and Duplicate Actions

| Input/action | Client validation | Server validation/error | Timing/focus | Duplicate protection |
| --- | --- | --- | --- | --- |
| 删除账号 / 重试删除 / 重试修复 | Existing explicit-consequence confirmation modal | Deletion idempotent; partial states named by store | Focus rules unchanged (existing modals) | Idempotent re-issue converges on complete (Spec D5) |
| Start controls under admission cap | None (server-authoritative) | Admission error with active-run pointer | Disabled-with-reason; no submit while capped | Existing run-idempotency identity (Spec AC-003) |
| Audit pagination | None | Cursor bounded | Focus kept on list | Read-only |
| Usage 刷新 | None | Standard read | — | Read-only |

Client behavior never replaces server constraints; limits are always server-decided.

## Frontend/Backend Contract

- Request/response: typed client over `GET /account/usage`, `GET /account/audit`; existing endpoints gain error payloads — 429 with `limit`, `retry_after_seconds`, and window fields; admission conflict with active-run references; deletion responses/statuses gain per-store completeness fields. TypeScript interfaces per codebase convention, frozen schema-first in the first implementation task within Spec semantics; deviations are a Design Change.
- Authentication/authorization: shared API client token; 401 → sign-in; 404 → safe not-found; 429/admission → named treatments above; UNEXPECTED → page-level safe error with correlation id.
- Pagination: cursor pagination for the audit list only (bounded pages); usage is a single bounded read.
- Optimistic update/rollback: `N/A - authoritative server state governs; usage and audit refresh on read; limit states never client-fabricated`.

### Error Mapping

| Backend code/status | User-visible state/message | Enabled action | Recovery | Sensitive detail hidden? |
| --- | --- | --- | --- | --- |
| 401 AUTH_REQUIRED | Redirect to sign-in | Sign in | Return | Yes |
| 429 RATE_LIMITED (named limit) | 速率限制 alert + countdown + usage link | Wait | Window reset | Yes |
| Admission conflict (active-run pointer) | Disabled-with-reason + run link | Inspect/wait/supersede | Start after settle | Yes |
| 404 (ownership) | Safe not-found | Back | Own boundary | Yes |
| REQUIREMENT (source policy / upload) | Existing named source/file-policy errors (extended for content-mismatch/oversize/bomb classes) | Correct input | Valid upload | Yes |
| Provider/transient | Existing named provider states | Existing bounded retry | Existing | Yes |
| UNEXPECTED_SYSTEM | Page-level safe error + correlation id | Retry/back | Report path | Yes |

No vague single-toast collapses; mapping follows `docs/API.md` and `docs/UX.md`.

## Responsive Behavior

| Viewport/device | Layout/information priority | Navigation/input changes | Overflow/touch behavior |
| --- | --- | --- | --- |
| Desktop >=1024px | Full account page (all sections), audit expansion + pagination, repair actions, in-flow limit alerts everywhere | All actions keyboard operable | Usage rows wrap; audit list scrolls within its region |

| Reduced <1024px | Identity, compact usage chips (current/max), disclosure text, deletion visibility; in-flow limit/admission alerts fully readable | Audit list and repair actions defer behind desktop-required notice | Single reading sequence |

Breakpoint: 1024px (F001 D-BP); status and recovery information survives small screens per UX.md.

## Accessibility

- Semantic structure: each account section is a labelled `<section>` (使用与限额 / 隐私与运营访问 / 敏感操作审计 / 删除账号); audit rows are a semantic list; limit/deletion states are text+marker, never color-alone.
- Keyboard and focus: section reading order; audit expand/paginate keyboard reachable; deletion/repair keep existing modal focus and return-to-trigger; a rate-limit alert receives focus (it changes available actions); admission disabled controls keep reason text reachable.
- Live announcements: rate-limit resolution (window reset) announced politely where an action was blocked; repair completion announced politely; pagination is passive.
- Contrast/non-color cues: token set >=4.5:1 body / >=3:1 components; limit and partial-deletion distinctions carried in language and markers.
- Motion/reduced motion: countdown is text-based; skeletons honor reduced motion.
- Verification approach: automated a11y checks in component tests plus a scripted keyboard pass over account page (usage read, disclosure read, audit expand/paginate) and one in-flow rate-limit + admission-rejection path, recorded in the Test Design execution snapshot.

## Design System Reuse

| Need | Existing token/component | `Reuse/Compose/Extend` | Reason | Project-level update |
| --- | --- | --- | --- | --- |
| Buttons, alerts, chips/status markers, skeleton/empty/error, list rows, ConfirmModal | F001–F010 foundations | Reuse | All variants exist | None |
| Progressive disclosure list | F006 pattern | Compose (audit list) | Same reading rules | None |
| Disabled-with-reason + pointer | Existing workspace pattern | Compose (admission rejection) | Established treatment | None |
| Desktop gate / reduced boundary | Existing desktop-gate component | Reuse | Canonical rule | None |
| Limit/usage label map | Existing label-map convention in `lib/api.ts` | Compose (new map) | Consistency | None |

No new tokens; no Feature-local visual language.

## UI Acceptance Links

- AC-002 limits visible + enforced: D-USAGE rows, D-LIMITERR named rejections with countdown
- AC-003 admission: disabled-with-reason + active-run pointer; no duplicate billing surfaced via existing idempotency notices
- AC-005 upload rejections: existing named source/file-policy error pattern extended
- AC-006 deletion completeness/repair: D-DELEXT states (project/source/account) with named store + 重试
- AC-007 audit + disclosure + D4(b): D-AUDITLIST, D-DISCLOSE sections
- AC-011 truthful surfaces incl. small screen: D-USAGE/D-LIMITERR/D-SMALL

## Open Questions

| ID | Question | `Critical/Non-critical` | Owner | Resolution | Status |
| --- | --- | --- | --- | --- | --- |
| UIQ-001 | Exact DTO field names for usage/audit/completeness payloads | Non-critical | Implementation assignee | Frozen schema-first (TypeScript interfaces) in the first implementation task within Spec semantics | RESOLVED |
| UIQ-002 | Disclosure copy exact wording (zh-Hans) | Non-critical | Implementation assignee | Static copy following D-DISCLOSE content points, reviewed in implementation review; no new mechanism | RESOLVED |
| UIQ-003 | Whether usage counts down live or on refresh | Non-critical | Implementation assignee | Refresh-only with server-provided reset timestamps; countdown text derived from `retry_after`/window fields, no client-side ticking beyond display of the provided instant | RESOLVED |

No Critical UI Open Question is `OPEN` or `DEFERRED`.

## `UI READY` Evidence

| ID | Requirement | Result | Evidence/reason |
| --- | --- | --- | --- |
| UR-01 | User Goal, Entry, Exit, complete User Flow explicit | YES | Flow incl. usage read, disclosure, audit, in-flow denials, three deletion paths with repair, permission and failure exits |
| UR-02 | Each affected Page/Screen/Component has explicit responsibility | YES | Responsibilities table, 7 surfaces |
| UR-03 | UI State Matrix covers applicable states | YES | 17-row matrix incl. rate-limited countdown, admission-rejected, partial-repairable, terminal-complete |
| UR-04 | Permission, validation, duplicate submit, cancel, back, recovery explicit | YES | Forms table; idempotent re-issue rules; modal focus preserved |
| UR-05 | Frontend/Backend contract and error mapping explicit | YES | Contract section + 7-row error mapping incl. 429/admission classes |
| UR-06 | Responsive behavior verifiable | YES | 1024px table; alerts readable below breakpoint; actions gated |
| UR-07 | Accessibility behavior verifiable | YES | A11y section: labelled sections, focus rules, text-based countdown, verification approach |
| UR-08 | Design System checked with explicit reuse/extension decisions | YES | Reuse table; composition only, no extensions |
| UR-09 | UI Acceptance linked to `AC-*` | YES | AC-002/003/005/006/007/011 mapped (remaining ACs are backend-verified with no UI surface) |
| UR-10 | No Critical UI Open Question open/deferred | YES | All three UIQs resolved (non-critical) |

## `UI READY` Record

- Status: `PASS`
- Input manifest: SPEC READY manifest (spec @ `d27deee5bfc8`) + `docs/UX.md`, `docs/UI.md`, `docs/DESIGN_SYSTEM.md`, `docs/FRONTEND.md` at base `main @ 683172b` + this artifact `ux-ui-f011-r1` (hash recorded in `STAGE.md` Gate Snapshot)
- Evidence checklist result: ALL YES (UR-01..UR-10)
- Critical UI Open Questions at `OPEN` or `DEFERRED`: NONE
- Validated Spec revision: `d27deee5bfc8`
- Validated UX/UI revision: `ux-ui-f011-r1` @ (hash recorded in `STAGE.md` Gate Snapshot)
- Validated at: 2026-09-01
- Decision Authority (named human + role): `YMY / Project Owner`
- Approval source: interactive session, 2026-09-01 — the question-form Spec approval (D2 relaxed limits "visible in the account usage surface", D3 "无角色+披露" with the account-page disclosure, D4(b) retained-ledger disclosure statement) covers the account-surface directions; this artifact's remaining interface decisions (D-LIMITERR in-flow treatments, D-AUDITLIST, D-DELEXT, D-SMALL) compose existing project patterns within that approved Spec behavior, following the repo's F010 UI-approval precedent. Explicitly ratified by `YMY / Project Owner` ("追认") in the same interactive session that approved the F011 Test Design, 2026-09-01.
- Approval scope: F011 UX/UI refinement at `ux-ui-f011-r1`

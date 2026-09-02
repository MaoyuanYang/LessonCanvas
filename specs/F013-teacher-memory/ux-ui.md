# F013 UX/UI Design — Teacher Memory

- Artifact ID: `ux-ui-f013-r1`
- Bound Spec: `specs/F013-teacher-memory/spec.md` @ `75ee61c2cf0b` (SPEC READY, 2026-09-02)
- Product Content Language: `zh-Hans` (per `AGENTS.md` Language Policy; existing UI copy convention)
- Last Updated: 2026-09-02

## Gate Record: UI READY

- Status: `PASS`
- Validation time: 2026-09-02
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-02 (question-form "批准 UI READY" ratifying U1 account-area 教师记忆 section with pending-proposal consolidation, U2 in-panel proposal cards + navigation badge, U3 evidence-panel 教师记忆（本项目） region with project-scoped toggles, U4 category chips, U5 conflict/truncation honesty, U6 injection budget priority order), scope: `ux-ui-f013-r1`
- Checklist: 10/10 YES (Goal/Entry/Exit/Flow; page responsibilities incl. account section, four host panels, header badge, evidence region; state matrix incl. generating/failed/empty/pending/stale/quota/applied/conflict/deletion; permission/validation with client+server boundary and duplicate-submit protection; contract/error mapping with distinct `MEMORY_LIMIT` copies and stale-decision refresh; verifiable responsive behavior incl. desktop-required record editing; verifiable accessibility behavior incl. badge label, section labelling, dialog focus restore, keyboard path; Design System reuse with explicit no-extension decision; UI acceptance linked to AC-001..AC-009; no Critical UI Open Question)
- Input manifest: `specs/F013-teacher-memory/spec.md` @ `75ee61c2cf0b`; `specs/F013-teacher-memory/ux-ui.md` @ (this file, hash below); `AGENTS.md` @ `ecde9412a7df`; `docs/UX.md` @ `bce8aecf872f`; `docs/UI.md`; `docs/DESIGN_SYSTEM.md`; `apps/web/` route/component inventory (OBSERVED 2026-09-02, `main @ 505232e`)

## UI Impact Detection (all answered against the SPEC READY revision)

- Changes the user's task path/entry: YES — a new memory-management section enters the account area; proposal cards appear inside existing confirmation/run panels.
- Adds/changes pages, components, navigation, visible states: YES — account "教师记忆" section, workspace proposal cards + pending badge, evidence-panel applied-context section.
- Changes Loading/Empty/Error/Success/permission feedback: YES — proposal pass generating/failed/empty states, quota (`MEMORY_LIMIT`) states, stale-proposal errors, deletion confirmation.
- Changes responsive behavior, accessibility, copy, tokens, Design System components: PARTIAL — new compositions of existing tokens/primitives; no token or primitive changes planned.
- Backend change altering frontend error mapping: YES — new memory endpoints introduce new error codes to map.

Conclusion: `UI Impact: YES`; this document is required.

## UX Decisions

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| U1 | Memory management placement | A "教师记忆" section inside `/account` (below usage/privacy, above destructive deletion): confirmed-record list with category chip, text, evidence reference, applied/conflict summary, quota counter (n/20), edit modal, delete with `ConfirmModal` consequence text; pending proposals also listed here (same confirm/edit/reject components as the workspace cards) with a link to the originating project, so a teacher with several projects can address everything in one place. Records remain workspace-scoped; the section renders the same honest empty state when nothing is confirmed yet. | Proposed; owner-ratified 2026-09-02 (with UI READY approval) |
| U2 | Proposal surface and badge | A "记忆提议" card region renders inside the panel where the trigger happened: brief panel after brief confirmation, blueprint panel after blueprint confirmation, and the artifact-run panels (教案/课件/练习) after run settlement. Each card shows category chip, proposed text (inline-editable before confirming), evidence reference (version/run link), and actions 确认 / 拒绝. The workspace header shows a persistent badge "记忆提议 N" (aria-label with count) while any workspace proposal is pending; the badge links to the first panel holding a pending proposal. Pass states render inside the region: 生成中 (skeleton line), 失败 with 重试 (explicit retry action, never blocks the triggering flow), and the honest "暂无新提议" empty result. | Proposed; owner-ratified 2026-09-02 (with UI READY approval) |
| U3 | Applied-context section | The evidence panel (运行证据) gains a top region "教师记忆（本项目）": the project's effective record list with per-record 在此项目停用/启用 toggles (project-scoped override, audited), known `language_mode` conflict notices (确认版本优先 wording), and — per selected run — the applied set: category, text, injected character count, conflicts skipped, and budget-skipped records. A quiet link opens the account management section. The section composes existing evidence-panel typography and `StatusBadge` chips; it is a view over the recorded trace state, never a second authority. | Proposed; owner-ratified 2026-09-02 (with UI READY approval) |
| U4 | Category labels and chips | The four categories render as `StatusBadge` chips with stable zh-Hans labels: `language_mode` 语言模式, `exercise_format` 练习格式, `pacing_structure` 节奏结构, `assessment_style` 测评风格. No new colors or tokens; existing neutral/accent badge variants. | Resolved from evidence (Design System reuse); confirmed with UI READY approval |
| U5 | Conflict and truncation honesty | Conflicts show an explicit notice in the applied-context section and on the record row in account management: "与当前确认版本冲突，已按确认版本执行" (confirmed version wins; never silently resolved). When the effective set exceeds the 2500-character injection budget, the skipped records are listed as "未注入（超出记忆预算）" — truncation is disclosed, never silent. | Resolved from Spec D5/D8; confirmed with UI READY approval |
| U6 | Injection budget priority | Deterministic order when budget-exceeded: category priority `language_mode` > `exercise_format` > `pacing_structure` > `assessment_style`; within a category, most-recently-confirmed first; whole records only (no partial text truncation of a record). This fixes the Spec's NON-CRITICAL open question (visible truncation disclosure per U5). | Proposed; owner-ratified 2026-09-02 (with UI READY approval) |

## User Flow (workspace owner / teacher)

- Goal: let confirmed preferences carry into future preparation, with every remembered thing visible, adjustable, and deletable.
- Entry 1 (proposal): confirm a brief/blueprint or settle a run → the proposal region appears in that panel with the badge → confirm (optionally edit text first) or reject → confirmed cards move to the record set (account section); rejected cards disappear and are never re-proposed identically.
- Entry 2 (management): `/account` → 教师记忆 → review records with evidence and conflicts → edit (modal), delete (ConfirmModal), or jump to a pending proposal.
- Entry 3 (application): open a project's 运行证据 tab → 教师记忆（本项目） → see what applied (and what was skipped for conflict/budget) on the selected run → toggle per-record applicability for this project → future runs reflect the change; the viewed run's history stays immutable.
- Success exit: teacher states "the system remembered X because I confirmed Y, it applied Z here, and I can delete it".
- Cancel/Back: rejecting/closing a proposal card or the edit modal changes nothing; back from account/evidence returns to prior view; no navigation discards a pending proposal (it persists until addressed).
- Failure recovery: pass failure shows 重试 (idempotent); `MEMORY_LIMIT` shows the quota message with a management link (delete or edit within caps, then retry confirm); stale proposal decisions refresh the list with an honest "提议已被处理" message.

## Page / Screen Responsibilities

| Surface | Responsibility | Data / API | Notes |
| --- | --- | --- | --- |
| `/account` 教师记忆 section | Workspace-level record management + pending-proposal decisions + quota display | `GET /memory`, `POST /memory/proposals/{id}/confirm|reject`, `POST /memory/passes/{id}/retry`, `PATCH /memory/records/{id}`, `DELETE /memory/records/{id}` | section owns listing and dialogs only; no business logic beyond API calls |
| Brief / blueprint panels | Host the 记忆提议 region after their confirmation events | `GET /memory` (proposal subset) | existing panels unchanged otherwise |
| Artifact-run panels (plans/decks/exercises) | Host the 记忆提议 region after run settlement | same | composed identically to the brief/blueprint region |
| Workspace header | Pending-proposal badge with count and link | proposal count from `GET /memory` (or existing workspace fetch) | quiet badge; no new navigation item |
| Evidence panel 教师记忆（本项目） | Project applicability + per-run applied context + conflicts/budget skips | `GET /projects/{id}/memory`, `POST /projects/{id}/memory/records/{id}/override`, existing run-summary/events payloads extended with the memory section | read-mostly; toggles are the only write |

## UI State Matrix

| State | Trigger | Visible UI | Allowed Action | Recovery/Next |
| --- | --- | --- | --- | --- |
| Loading | section/region entry or refresh | `SkeletonRows` | wait | loaded or error |
| Pass generating | trigger fired, pass running | inline "提案生成中…" line in the region | continue other work | completed or failed |
| Pass failed | provider/transient failure | `Alert` "记忆提案生成失败" + 重试 button | retry (idempotent per trigger) | pass re-runs; trigger flow unaffected |
| Empty — no proposals | pass completed, no surviving candidates | honest "暂无新提议" text | continue | next trigger event |
| Pending proposals | valid candidates waiting | proposal cards + badge count | 确认 (optionally edit inline first) / 拒绝 | record created / rejection recorded |
| Proposal decided concurrently | stale decision attempt | honest "该提议已被处理" + list refresh | review current state | no duplicate effect |
| Records empty | no confirmed records yet | `EmptyState` "尚未确认任何教师记忆" + explanation | proposals appear after trigger events | — |
| Records loaded | one or more confirmed | record rows with category chip, evidence, conflict marks, quota n/20 | edit / delete / follow evidence link | — |
| Quota exceeded (`MEMORY_LIMIT`) | confirm/edit beyond caps | inline error "记忆数量已达上限（20 条）" or "单条记忆不超过 300 字符" + management link | delete a record or shorten text, then retry | explicit, never silent |
| Applied context — none | run used no memory (empty set or all disabled/conflicted) | "本次运行未应用教师记忆" (+ reasons when records were skipped) | adjust toggles | next run reflects changes |
| Applied context — applied | run injected memory | applied list with chars, conflicts, budget skips | inspect, toggle, open account section | — |
| Record deleted | delete confirmed | row removed + success note; quota counter updates | continue | future runs stop applying it |
| Permission denied | non-owner access | existing safe denial (no cross-workspace disclosure) | return to own boundary | — |

## Contract and Error Mapping

- New endpoints and shapes follow the Spec's API Behavior; the web client adds typed functions in `lib/api.ts` mirroring existing patterns.
- Error mapping: `AUTH_REQUIRED` → existing in-app honest state; `MEMORY_LIMIT` → specific inline quota message + management link (distinct copy for count vs length caps); stale/proposal-decided → refresh with honest message; `PROVIDER_TRANSIENT`/network on passes or section loads → existing honest unavailable pattern with retry; project-memory `NOT_FOUND` → existing safe project-boundary behavior. No vague toast-only errors; correlation ids follow the existing pattern.
- Duplicate-submit protection: confirm/reject/delete/override buttons disable while their request is in flight (existing button patterns).

## Permission and Validation

- Every surface requires the workspace owner; per-project memory views additionally resolve through existing project ownership. Unauthorized access never discloses another workspace's existence.
- Client validation precedes server calls where the rule is known (300-character edit limit with live counter in the edit modal; server remains authoritative and re-validates).
- Proposal confirm with edit validates length client-side first; server `MEMORY_LIMIT`/validation errors map to the fields above.
- Dangerous action: record deletion uses `ConfirmModal` with consequence text ("删除后今后的运行将不再应用该记忆；历史运行记录保持不变，并随项目删除一并移除").

## Responsive and Accessibility

- Desktop (≥1024px): full management table, proposal cards beside their panels, applied-context region in the evidence layout.
- Reduced small-screen: proposal cards (confirm/reject are lightweight primary actions) and read-only applied-context remain available; record editing (modal form) follows the existing desktop-required convention for structured editing with the documented desktop-gate message; the account section stays reachable through existing navigation.
- Accessibility: proposal region is a labelled section (`aria-labelledby`) inside each panel; the badge exposes "N 条待处理记忆提议"; cards are list items with heading + chip + text + actions in reading order; conflict and truncation notices use the existing alert/note patterns and are announced; dialogs reuse the shared focus trap and restore focus on close; all actions keyboard reachable; chips carry text (never color-only); reduced-motion respected globally as today. Verifiable: keyboard-only path from badge → proposal card → confirm → account section; focus returns to the trigger after each dialog.

## Design System Reuse

Reuses: `Button` (primary/quiet), `Modal` + `ConfirmModal`, `StatusBadge` (category chips and pass states), `EmptyState`, `Alert`, `SkeletonRows`, evidence-panel section composition, existing card borders/typography, semantic tokens. No new primitives, tokens, or variants; all new visuals are compositions. If a shared "proposal card" is used in four panels, it becomes a single Feature component reused across them (not four copies).

## UI Acceptance (linked to Spec ACs)

- Proposal journey: trigger → generating/failed/empty honesty → pending cards → confirm-with-edit / reject → badge clears; rejected never re-proposed identically (AC-001, AC-005; U2).
- Application journey: evidence-panel region shows applied set, chars, conflicts (确认版本优先), budget skips, and per-project toggles that change future runs only (AC-002, AC-003, AC-007, AC-009; U3, U5, U6).
- Management journey: account section lists records with evidence/conflicts/quota; edit/delete with consequence confirmation; `MEMORY_LIMIT` paths explicit (AC-009; U1).
- Deletion honesty: deleted record disappears, future runs stop applying it, historical traces stay inspectable until project deletion (AC-004; state matrix).

## UI Open Questions

- None Critical. `NON-CRITICAL` final copy polish of proposal/empty/quota strings during implementation (zh-Hans inline convention).

# F015 UX/UI Design — Governed Model Tool Calling

- Artifact ID: `ux-ui-f015-r1`
- Bound Spec: `specs/F015-governed-model-tool-calling/spec.md` (SPEC READY PASS 2026-09-03 @ `7f6f230aae81`)
- Product Content Language: `zh-Hans` (per `AGENTS.md` Language Policy; existing UI copy convention)
- Last Updated: 2026-09-03

## Gate Record: UI READY

- Status: `PASS`
- Validation time: 2026-09-03
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-03 (routing decision "走 UI READY" confirmed at SPEC READY approval; UX decisions U1–U4 resolved from evidence following the F014 U4/U5 precedents; explicit UI READY approval), scope: `ux-ui-f015-r1`
- Checklist: 10/10 YES (Goal/Entry/Exit/Flow; surface responsibilities incl. evidence-panel label table and summary chips; state matrix incl. request/result/refused/fallback states; permission/validation boundary unchanged; contract/error mapping incl. four new trace event types and no-new-endpoint rule; verifiable responsive behavior within the existing desktop technical-evidence section and canonical small-screen boundary; verifiable accessibility behavior reusing the aria-expanded row pattern; Design System reuse with no token or primitive changes; UI acceptance linked to AC-001..AC-006; no Critical UI Open Question)
- Artifact hash: `ux-ui-f015-r1` @ `c9df861b2b7e`
- Input manifest: `specs/F015-governed-model-tool-calling/spec.md` @ SPEC READY revision; `AGENTS.md`; `docs/UX.md`; `docs/UI.md`; `docs/DESIGN_SYSTEM.md`; `apps/web/` component inventory (OBSERVED 2026-09-03 on `main`: `evidence-panel.tsx` generic event rows with expand + label table + `retrievalSummaryChips` collapsed-row precedent; `EVIDENCE_EVENT_LABELS` in `lib/api.ts`; `technical-evaluation-region.tsx` renders only the derived `superseded_configuration` stale state, never the raw `model_config`)

## UI Impact Detection (all answered against the SPEC READY revision)

- Changes the user's task path/entry: NO — no new pages or navigation; existing panels gain event rows.
- Adds/changes components or visible states: YES — the evidence panel renders four new event types (`tool.request` / `tool.result` / `tool.refused` / `tool.fallback`) with collapsed-row summary chips.
- Changes Loading/Empty/Error/Success/permission feedback: YES — new honest states (tool refusal with reason; deterministic fallback with cause).
- Changes responsive behavior, accessibility, copy, tokens, Design System components: PARTIAL — new label-table entries and chip compositions of existing tokens/primitives; no token, primitive, or shared-component changes.
- Backend change altering frontend error mapping: NO — no new error classes; trace payload extensions only (no new public endpoints).

Conclusion: `UI Impact: YES` (minor); this document is required.

## UX Decisions

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| U1 | Tool-round visibility in evidence | The four new event types render with zh-Hans labels in the existing label table — `tool.request` 工具请求（模型）, `tool.result` 工具结果, `tool.refused` 工具拒绝, `tool.fallback` 工具循环回退 — and each collapsed row shows summary chips following the F014 `retrievalSummaryChips` precedent: request → `第 N 轮 · <工具名>`, result → `返回 M 条` (or the tool-specific count), refused → `拒绝：<原因>`, fallback → `回退：<原因>` (轮次耗尽 / 循环失败). Existing per-row latency/tokens/cost/model columns already make every round's cost visible; the expanded view keeps the existing raw-JSON disclosure (arguments, result sections, refusal reason, round index). | Resolved from evidence (F014 U4 precedent); confirmed with UI READY approval |
| U2 | Fallback disclosure placement | The deterministic fallback (Spec D2) is its own traced event (`tool.fallback`) rendered with the cause chip where the teacher/reviewer already reads the run's tool story — the same evidence stream — instead of a new surface or a modal. Reviewers comparing pre-F015 and post-F015 runs see orchestration-issued `tool.standards_search` vs model-driven rounds as ordinary labeled rows. | Resolved from Spec D2; confirmed with UI READY approval |
| U3 | Cost/cap visibility | No new UI: round model calls carry tokens/estimated cost on their own event rows (existing columns), the run header's existing 模型调用 N/上限 and 工具调用计数 already aggregate `tool.*` events server-side, and cap accounting is the AC-003 backend obligation. The evidence panel stays a view over recorded events. | Resolved from evidence; confirmed with UI READY approval |
| U4 | Comparability signature display | `tool_mode` joins `model_config_snapshot()` backend-side; the web surfaces render only the derived 配置已过时 stale state and pass-comparison grouping, never the raw config, so no UI change is needed for the signature. | Resolved from evidence (OBSERVED: raw `model_config` is never rendered); confirmed with UI READY approval |

## User Flow (workspace owner / technical reviewer)

- Goal: verify that the planning specialist's tool use was real, bounded, and honestly governed.
- Entry: open 运行证据 for a planning run → the technical-evidence section lists `tool.request`/`tool.result` pairs with round chips → expand a request to read the model-issued arguments → expand the paired result to read the returned standards sections.
- Refusal path: a `tool.refused` row shows 拒绝：<原因> on the collapsed row; expansion shows the refused name/arguments; subsequent rounds show the model correcting or the loop continuing.
- Fallback path: a `tool.fallback` row shows 回退：<原因>; the following `tool.standards_search` and `model.planning_build_draft` rows show the deterministic path completing the stage.
- Success exit: reviewer states "the specialist requested the standards search itself in round 2, the result returned 3 sections, and every round's latency/tokens/cost is visible — refusals and the fallback are on the record".
- Cancel/Back: collapsing rows changes nothing; all surfaces are read-only views over recorded events.
- Failure recovery: nothing to recover in UI (refusals/fallback are disclosed states, not blocking errors); run retry paths unchanged.

## Surface Responsibilities

| Surface | Responsibility | Data / API | Notes |
| --- | --- | --- | --- |
| Evidence panel (technical section, desktop) | Render the four new event types with labels, collapsed-row chips, and raw payload on expand | new trace event types in the existing events endpoint | label-table entries + one chip helper; no structural change |
| F009 evaluation region / report | No change; `tool_mode` participates in comparability backend-side | `model_config` extension | existing 配置已过时 state renders as today |
| All other surfaces | Unchanged | — | planning interview/blueprint flows have no new teacher-visible states (tool rounds are evidence-level detail; progressive disclosure rule 6) |

## UI State Matrix

| State | Trigger | Visible UI | Allowed Action | Recovery/Next |
| --- | --- | --- | --- | --- |
| Tool round requested | `tool.request` event | labeled row + `第 N 轮 · 工具名` chip + latency/tokens/cost | expand for raw arguments | read-only |
| Tool round executed | `tool.result` event | labeled row + `返回 M 条` chip | expand for raw result | read-only |
| Tool round refused | `tool.refused` event | labeled row + `拒绝：<原因>` chip | expand for refused name/args | read-only; later rounds show correction or fallback |
| Loop fell back | `tool.fallback` event | labeled row + `回退：<原因>` chip | expand for cause detail | read-only; deterministic rows follow |
| No tool rounds (model answered directly) | no `tool.*` round events | nothing new rendered (existing events only) | — | honest absence; no fabricated indicator |
| Events still loading / empty | existing query states | existing skeleton / empty copy | existing pagination | unchanged |

## Responsive Behavior

- The technical-evidence section is desktop-gated today (F006/F014 convention) and stays so; the canonical reduced small-screen experience documented in `docs/UX.md` is unchanged. Within the section, chips wrap in the existing `flex-wrap` row layout; long tool names truncate via existing text patterns.

## Accessibility Behavior

- New rows reuse the existing expandable-row button pattern (`aria-expanded`, keyboard activation, `focus-visible` outline); chips are decorative text spans (rounded background, `text-xs`) already used by retrieval chips, with the information also present in the row text and expanded payload. No new dialogs, no motion, contrast inherits existing token pairs.

## Design System Reuse

- Reuses semantic tokens (`evidence` tint for chips, `ink-secondary` for meta) and the existing evidence-row and chip compositions; no token, primitive, or shared-component additions or promotions. Nothing to record in `docs/DESIGN_SYSTEM.md` beyond the label-table entries at documentation sync (component docs unaffected).

## UI Acceptance Criteria Mapping

- AC-001 → tool request/result rows visible on a live run's evidence stream (U1).
- AC-002 → refused rows with reason chips (U1/U2 state matrix).
- AC-003 → per-round latency/tokens/cost columns; existing run-header cap counters (U3).
- AC-004 → adversarial coverage is backend-level; UI shows refusals honestly when they occur (U1).
- AC-005 → round visibility + `tool_mode` comparability without new UI (U1/U4).
- AC-006 → fallback row with cause chip followed by deterministic-path rows (U2).

## Open Questions

None blocking `UI READY`.

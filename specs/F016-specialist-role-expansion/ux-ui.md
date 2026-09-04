# F016 UX/UI Design — Specialist Role Expansion

- Artifact ID: `ux-ui-f016-r1`
- Bound Spec: `specs/F016-specialist-role-expansion/spec.md` (SPEC READY PASS 2026-09-04 @ `f37d7519f8f9`)
- Product Content Language: `zh-Hans` (per `AGENTS.md` Language Policy; existing UI copy convention)
- Last Updated: 2026-09-04

## Gate Record: UI READY

- Status: `PASS`
- Validation time: 2026-09-04
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-04 (UX decisions U1–U5 resolved from evidence following the F013/F014/F015 precedents; explicit UI READY approval), scope: `ux-ui-f016-r1`
- Checklist: 10/10 YES (Goal/Entry/Exit/Flow; surface responsibilities incl. evidence-panel stage labels, review-round chips, sources analysis region, artifact `reviewing` status, narration sentences; state matrix incl. analysis failed/retry, reviewing/revise rounds, failed-after-revise, minor-only pass, cap under the formula budget; permission/validation boundary unchanged with read-only D4 regions and permission-gated retry; contract/error mapping incl. seven new trace event kinds, artifact payload additions, one source-scoped retry endpoint, no new top-level API areas; verifiable responsive behavior within the existing surfaces and canonical 420px boundary; verifiable accessibility behavior reusing the aria-expanded row pattern, semantic lists, text-not-color severity; Design System reuse with no token or primitive changes; UI acceptance linked to AC-001..AC-006; no Critical UI Open Question)
- Artifact hash: `ux-ui-f016-r1` @ `519b499459a0`
- Input manifest: `specs/F016-specialist-role-expansion/spec.md` @ SPEC READY revision; `AGENTS.md`; `docs/UX.md`; `docs/UI.md`; `docs/DESIGN_SYSTEM.md`; `apps/web/` component inventory (OBSERVED 2026-09-04 on `main`: `evidence-panel.tsx` generic event rows with `retrievalSummaryChips`/tool-round chip precedents; `EVIDENCE_EVENT_LABELS` / `EVALUATION_CRITERION_LABELS` in `lib/api.ts` (`C-TOOL-1` currently missing); `artifact-run.tsx` `ARTIFACT_STATUS_LABELS`; `sources-panel.tsx` F014 chunk-view expandable pattern; family-panel `narrationText` mappers)

## UI Impact Detection (answered against the SPEC READY revision)

- Changes the user's task path/entry: NO — no new pages or navigation.
- Adds/changes components or visible states: YES — new stage event labels and review-round chips, `reviewing` artifact status, findings/design read-only regions, sources analysis badge + retry, narration sentences.
- Changes shared components/tokens: NO — composition only (plus a label-registry entry fix for the missing `C-TOOL-1`).

## UX framing

## UX framing

The teacher's question changes from "what did the system produce?" to "who checked what, and what did they find?" Three honest-disclosure moments: a source carries its own analysis state (or honest failure), a lesson artifact passes through visible design/review stages, and review findings — including the ones that ended in failed-after-revise — stay visible with severity. Nothing may look "complete" that was not reviewed, and nothing reviewed-failed may look passed. Progressive disclosure: stage chips and status badges first; findings/design/findings detail on demand.

## U1 Evidence-panel stage events and role labels

- `EVIDENCE_EVENT_LABELS` additions: `model.generation_design_lesson` → 模型调用·活动设计; `model.generation_review_lesson` / `model.generation_review_deck` / `model.generation_review_exercises` → 模型调用·质量评审（教案/课件/练习）; `model.generation_revise_lesson` / `model.generation_revise_deck` / `model.generation_revise_exercises` → 模型调用·修订重写（教案/课件/练习）.
- Review/revise event rows render collapsed-row summary chips (the F014 `retrievalSummaryChips` / F015 tool-round chip precedent): `第 N 轮`, `严重 X · 轻微 Y`, and the round outcome — `未触发修订`（minor-only or clean pass）, `触发修订`, `修订后通过`, `修订后仍未通过`. Severity counts reuse existing danger (严重) and neutral (轻微) semantics; no new tokens.
- Per-event latency/tokens/cost/model columns are unchanged — the new stages become visible through the same columns (AC-002/AC-005).
- Contract: the events' existing payload shape carries `round`, `severe_count`, `minor_count`, `revise_triggered`, `outcome` fields; no endpoint change.

## U2 Artifact stage status and narration

- `ARTIFACT_STATUS_LABELS` gains `reviewing: "评审中"`. The per-artifact progress list shows the honest stage order drafting → reviewing → rendering → validating → complete/failed; the reviewing badge appears for both the review and the revise round (round detail lives in U1 chips and U3 findings, so a revise round is never mistaken for a first review).
- Narration mappers in the three family panels gain sentences: 正在设计第 N 课活动…（plans only）; 第 N 课进入质量评审…; 第 N 课触发一轮修订…; 第 N 课评审未通过（修订后仍存在严重问题）…; 评审通过（含轻微发现，已披露）. Deck/exercise variants drop the design sentence. Existing queue/supersede/terminal sentences are unchanged.
- A failed-after-revise artifact shows its existing failure-reason line naming the review stage (评审阶段：修订后仍存在严重发现); no generic 生成失败 substitution is allowed (honesty rule).
- Contract: run/artifact payloads expose per-artifact `stage`, `review_rounds`, and `failure_reason` as delivered by the backend; statuses render from the same `artifact.status` field as today.

## U3 Findings and design visibility (evidence detail, read-only)

- Per-artifact expandable 评审发现 region (native button + `aria-expanded`, the F014 chunk-view pattern) inside the run detail/artifact row expansion: findings as a semantic list, each row = dimension label (目标覆盖 / 课件对应 or 练习对应 for plan-coverage in decks/exercises, 依据支撑, 内在一致性) + severity badge + bounded message; a round caption（第 1 轮 / 修订后第 2 轮）discloses which round produced the shown findings (latest round persisted per the Spec).
- Empty state: 评审通过，无严重或轻微发现. Minor-only pass shows 评审通过（含轻微发现） with the findings listed — never hidden.
- Plans only: expandable 活动设计 region showing the design digest — covered blueprint objectives, activities with timing, assessment approach, evidence references (chunk positions). Read-only by contract (D4): no edit affordance, no confirm action; the region header states 设计为运行中间产物，仅查看.
- Contract: design and findings ride the existing artifact detail payloads; no new endpoints.

## U4 Sources-surface analysis region

- Per-source card gains an analysis badge: 待分析 / 分析中 / 已分析 / 分析失败（可重试）. The retry action (重试分析) renders only for the failed state and only with write permission; it is disabled while an analysis is in flight (one-in-flight rule made visible).
- Expandable 查看来源分析 region (chunk-view precedent): topics, language points, suitability flags, key passages with 第 N 段 chunk references, and a cost line — model label, latency, 约 $X（估算） or 未记录 (telemetry honesty rule). The failed state shows the stored reason plus the retry action; the source itself remains usable and its existing parse/chunk regions are unaffected (analysis failure never blocks the source).
- Upload flow is unchanged; the analysis badge appears after parse settles, so the card honestly reads 解析完成 → 分析中 → 已分析.
- Discovery/planning disclosure: the `source_analyses_state` (ready/partial/none + reasons) of consumed analyses is inspectable in the existing expandable evidence payload of planning/discovery model events — labeled subordinate context, no separate evidence region.
- Contract: source list/detail payloads gain `analysis` (status, digest fields, telemetry, error); one retry endpoint scoped to the source.

## U5 Technical-evaluation surfaces

- `stage_set` stays backend-signature-only (the F015 U4 `tool_mode` precedent): no new pass-row display; the report view's existing comparison-unavailable messaging covers signature changes automatically.
- `EVALUATION_CRITERION_LABELS` gains the new blocking stage criterion label (阶段执行与留痕) and, as a registry-consistency fix riding this Feature, the missing F015 `C-TOOL-1` label (工具调用治理) so it stops falling back to the raw key.

## State coverage (UI/UX long-term rule 3)

- Loading: existing panel skeletons; no new spinners beyond status badges. Empty: 无发现 / 尚无分析 with one-line explanation. Error: 分析失败 + 重试分析；评审输出异常 follows existing artifact failure display. Waiting/Active: 分析中 / 评审中 badges and narration sentences. Partial failure: per-lesson failure with the stage-named reason; completed lessons stay green. Stale/Superseded: unchanged existing behavior. Permission denied: retry hidden in read-only contexts. Quota/cap: existing 模型调用 used/cap display now reflects the formula cap; cap exhaustion keeps the existing capped-failure messaging.
- Reduced small screen (420px): all new regions stack in the existing single-column layout; no fixed widths. Keyboard/focus: expanders are native buttons with `aria-expanded` (chunk-view precedent); findings are semantic lists; severity conveyed by text, not color alone.

## Out of UI scope

Teacher editing/confirmation of designs or findings (D4); new top-level surfaces; new Design System tokens or variants; in-flight cancel of a review round; export changes (F008 packaging unchanged).

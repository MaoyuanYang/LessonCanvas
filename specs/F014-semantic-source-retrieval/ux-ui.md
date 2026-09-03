# F014 UX/UI Design — Semantic Source Retrieval

- Artifact ID: `ux-ui-f014-r1`
- Bound Spec: `specs/F014-semantic-source-retrieval/spec.md` (SPEC READY PASS 2026-09-03)
- Product Content Language: `zh-Hans` (per `AGENTS.md` Language Policy; existing UI copy convention)
- Last Updated: 2026-09-03

## Gate Record: UI READY

- Status: `PASS`
- Validation time: 2026-09-03
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-03 (question-form answers selecting U1 "徽章展开+摘录随引用下发" and U2 "工件详情内逐课标注"; explicit UI READY approval), scope: `ux-ui-f014-r1`
- Checklist: 10/10 YES (Goal/Entry/Exit/Flow; surface responsibilities incl. shared citation chip, three artifact panels, sources chunk expansion, evidence retrieval rows; state matrix incl. retrieved/empty/excluded/failed/stale states; permission/validation boundary unchanged; contract/error mapping incl. payload extensions and no-new-endpoint rule; verifiable responsive behavior on 420px; verifiable accessibility behavior incl. keyboard expansion and aria-expanded; Design System reuse with one documented shared-variant promotion; UI acceptance linked to AC-001..AC-007; no Critical UI Open Question)
- Artifact hash: `ux-ui-f014-r1` @ `f913f17b7f41`
- Input manifest: `specs/F014-semantic-source-retrieval/spec.md` @ SPEC READY revision; `AGENTS.md`; `docs/UX.md`; `docs/UI.md`; `docs/DESIGN_SYSTEM.md`; `apps/web/` component inventory (OBSERVED 2026-09-03 on `main`: `blueprint-panel.tsx` `citationLabel` chips, `evidence-panel.tsx` generic event rows with expand + label table, `sources-panel.tsx` without any chunk view, artifact panels without citations)

## UI Impact Detection (all answered against the SPEC READY revision)

- Changes the user's task path/entry: NO — no new pages or navigation; existing panels gain content.
- Adds/changes components or visible states: YES — citation chips become expandable and chunk-level everywhere they appear; artifact details gain per-lesson citations and an explicit ungrounded notice; sources panel gains chunk expansion; evidence panel gains retrieval event rows with summary chips.
- Changes Loading/Empty/Error/Success/permission feedback: YES — new honest states (无强相关来源语料, 未嵌入 chunk 披露, 排除披露).
- Changes responsive behavior, accessibility, copy, tokens, Design System components: PARTIAL — new compositions of existing tokens/primitives plus one shared-variant promotion (citation chip); no token or primitive changes.
- Backend change altering frontend error mapping: NO — no new error classes; payload extensions only (no new public endpoints).

Conclusion: `UI Impact: YES`; this document is required.

## UX Decisions

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| U1 | Citation-to-chunk tracing | Citation badges become expandable: click (or keyboard activate) a badge to expand an inline region showing 文件名, chunk 序号（第 N 段）, a server-delivered excerpt (~200 characters, injected with the citation object at normalization time), and the content-hash prefix (8 hex chars). The badge label upgrades from `来源：文件名` to `来源：文件名 · 第N段`（multiple chunks collapse to a count until expanded）. The sources panel additionally gains per-source expansion listing every chunk (position + full text; chunks with `embedding_failed` render a 未嵌入 state with reason) as the full-fidelity view. Self-contained data — no new public endpoints; excerpts ride existing blueprint/artifact payloads, chunk lists extend the existing sources payload. | `YMY / Project Owner`, 2026-09-03 (interactive, "徽章展开+摘录随引用下发") |
| U2 | Zero-relevance (D4) visibility | Artifact detail views (教案/课件/练习) show a per-lesson notice line "无强相关来源语料" when that lesson's retrieval produced no above-threshold chunks, next to the lesson's citations area; the same state is visible in the expanded retrieval trace event. Teachers see the honest ungrounded state where they consume the artifact, not only in the evidence tab. | `YMY / Project Owner`, 2026-09-03 (interactive, "工件详情内逐课标注") |
| U3 | Shared citation-chip promotion | The citation chip (today a feature-local pattern in `blueprint-panel.tsx`) is promoted to one shared component used by the blueprint panel and all three artifact panels, with documented variants: source-chunk citation (expandable), standards citation (static, current shape). Visual language unchanged (evidence-tinted chip); promotion recorded in `docs/DESIGN_SYSTEM.md` at documentation sync. | Resolved from evidence (Design System reuse); confirmed with UI READY approval |
| U4 | Retrieval disclosure in evidence | Retrieval trace events render with a zh-Hans label in the existing label table and show summary chips on the collapsed row: 命中 N · 排除 M · 预算 x/y 字; the expanded view keeps the existing raw-JSON disclosure (query, hit chunk ids, similarities, reasons). No second authority — the panel stays a view over recorded events. | Resolved from evidence; confirmed with UI READY approval |
| U5 | Excluded/failed chunk visibility | Sources-panel chunk expansion marks `embedding_failed` chunks as 未嵌入（原因）; per-retrieval exclusion counts ride the evidence row (U4). Upload/embedding failure never blocks or degrades the surrounding source row beyond this disclosure. | Resolved from Spec D3; confirmed with UI READY approval |
| U6 | Copy and interaction language | All new copy is zh-Hans; expansion uses the evidence-panel expand pattern (button + `aria-expanded`, no dialogs, no motion); badges wrap within existing flex layouts. | Resolved from evidence (UX rules 3/6, language policy); confirmed with UI READY approval |

## User Flow (workspace owner / teacher)

- Goal: verify that generated content is actually grounded in the teacher's own materials, chunk by chunk.
- Entry 1 (blueprint): open the blueprint panel → objectives/lessons carry chunk-level citation badges → expand a badge → compare excerpt against the original → optionally open 来源材料 and expand that source to read the full chunk and its neighbors.
- Entry 2 (artifacts): open 教案/课件/练习 detail → each lesson shows its citation badges (from that artifact's own retrieval) → expand to verify; lessons without hits show 无强相关来源语料 instead of citations.
- Entry 3 (evidence): open 运行证据 → retrieval rows show 命中/排除/预算 summaries → expand for query, similarities, and exclusion reasons.
- Success exit: teacher states "this objective is grounded in paragraph 7 of my reading-text file, and this lesson had no strongly related source content — visibly".
- Cancel/Back: collapsing a badge or source row changes nothing; all surfaces are read-only views over recorded state.
- Failure recovery: nothing to recover in UI (embedding failures are disclosed states, not blocking errors); generation retry paths unchanged.

## Surface Responsibilities

| Surface | Responsibility | Data / API | Notes |
| --- | --- | --- | --- |
| Shared citation chip (new shared component) | Render source-chunk citations (expandable: filename, 第N段, excerpt, hash prefix) and standards citations (static) | citation objects inside existing blueprint/artifact payloads | one component, two documented variants (U3) |
| Blueprint panel | Existing objectives/lessons render upgraded badges via the shared chip | blueprint payload citation extension | layout unchanged |
| Artifact panels (plans/decks/exercises) | Per-lesson citations via the shared chip + 无强相关来源语料 notice (U2) | artifact payload `citations` + `grounding_state` per lesson | no new panels |
| Sources panel | Source-row expansion listing chunks: position, text, 未嵌入 state + reason (U1/U5) | existing sources payload extended with chunk list | read-only |
| Evidence panel | Retrieval rows with summary chips + raw payload on expand (U4) | new trace event type in existing events endpoint | label-table entry only |

## UI State Matrix

| State | Trigger | Visible UI | Allowed Action | Recovery/Next |
| --- | --- | --- | --- | --- |
| Retrieved with citations | lesson/item retrieval hit ≥1 chunks | citation badges (来源：文件名 · 第N段) | expand badge; open sources | verify against original |
| Zero relevance (D4) | no chunk above threshold | 无强相关来源语料 notice + retrieval event with 0 hits | view evidence detail | none needed (honest state) |
| Excluded chunks (D3) | embedding_failed/not-embedded chunks exist | 排除 M chip on retrieval row; 未嵌入（原因） in sources expansion | view reasons | re-deploy backfill or re-upload source |
| No sources at all | project has no ready sources | no retrieval events; existing empty-source states unchanged | upload sources | existing flow |
| Embedding failed at upload | adapter failure during parse | chunks persist as 未嵌入; source stays ready with disclosure | view reason in sources panel | retry via re-upload (parse re-runs embedding) |
| Citation stale (source deleted after citation) | cited source no longer exists | badge shows filename + 已删除 state | none | citations are historical record; deletion sweep owns cleanup |

## Contract Notes (frontend/backend boundary)

- Citation object (source type) gains: `chunk_position: int`, `text_sha256: string` (full hash; UI shows prefix), `excerpt: string` (server-trimmed, ~200 chars, injected only at server-side normalization from the retrieved set).
- Artifact payloads gain per-lesson: `citations: [...]` and `grounding_state: "retrieved" | "none"`.
- New trace event type `retrieval.semantic_search` with payload: `{family, lesson_index?, query, hits: [{chunk_id, source_id, position, similarity}], excluded_count, excluded_reasons, budget_chars, used_chars}`.
- Sources listing payload gains an optional `chunks` array (position, text, embedding status/reason) — extension of an existing endpoint, no new public endpoints.
- Payload-supplied citations from models are never rendered (server-injected only); UI renders only authoritative payload fields.

## Accessibility and Responsive Behavior

- Every expansion is a native-focusable button with `aria-expanded` and visible focus ring (existing evidence-panel pattern); no dialogs, no motion — reduced-motion safe by construction.
- Citation badges and summary chips wrap within existing flex layouts; verified at the canonical 420px reduced small-screen experience (read-only surfaces; no desktop-gated writes introduced).
- Notices (无强相关来源语料, 未嵌入) are text states adjacent to their items, readable by screen readers in document order; counts in aria labels where chips are icon-only.

## UI Acceptance Mapping

- AC-002 visible via U4 (retrieval rows with hits/exclusions/budget).
- AC-003 visible via U1/U3 (expandable chunk citations across blueprint and three artifact families).
- D3 visible via U4/U5; D4 visible via U2; stale-citation honesty via state matrix row.
- AC-001 observable by teachers via U5 (未嵌入 states in sources panel).

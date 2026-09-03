# F014: Semantic Source Retrieval

- Spec Status: `REVIEW` (implementation complete; see Gate Record)
- Roadmap Status: `REVIEW`
- Priority: `P0`
- Owner: `YMY / Project Owner` (driving `ZCode feature-dev` session)
- Work item: [GitHub Issue #28](https://github.com/MaoyuanYang/LessonCanvas/issues/28) — bound 2026-09-03 (authorized); work-status authority
- Decision Authority: `YMY / Project Owner`
- Dependencies: None hard (Phase 1 complete); integrates with delivered F001 grounding, F003–F005 generation call sites, F006 evidence trace, F009 evaluation pinning, F011 quota/deletion guardrails, F012 deploy chain
- Last Updated: 2026-09-03 (implementation T0–T8 complete on `feature/F014-semantic-source-retrieval`; review `review-f014-r1` recorded; delivery steps pending owner authorization)

## Gate Record: REVIEW

- Status: `PASS` (implementation and evidence under review; delivery pending authorization)
- Validation time: 2026-09-03
- Implementation (plan `plan-f014-r1`, T0–T8): embedding adapter (`adapters/embedding.py`, fake + fastembed behind settings, ADR-0007); migrations `f014c1e3f5a7` (vector extension, `vector(512)` + HNSW cosine, embedding status/error, content/text hashes, legacy hash backfill) and `f014d5f7b9c2` (artifact `citations_json`/`grounding_state`); parse-time embedding with explicit failure states; idempotent deploy-time backfill (`scripts/backfill_embeddings.py`, deploy chain step 4/5, image pre-bakes weights via the `embedding` dependency group); retrieval service (`sources_grounding/retrieval.py`: cosine top-k, rank-order budget trim, exclusion disclosure, honest none-state); planning corpus swap + per-objective/per-lesson citation retrieval with traced events; per-lesson retrieval wired into all three generation families with payload `retrieved_sources`/`grounding_state`; server-injected chunk citations on blueprint and all artifact families (payload citations stripped); F009 signature gains `retrieval_mode`; F011 deletion coverage verified; web surfaces (shared citation chip, artifact citations + 无强相关来源语料 notice, sources chunk expansion with 未嵌入 disclosure, evidence retrieval rows with 命中/排除/预算 chips).
- Verification: backend 547 passed + 4 skipped + ruff clean (baseline 515+4 → +32 F014 tests); web 113/113 + tsc clean + eslint 0 errors (3 pre-existing warnings); E2E TS-025 green behind `E2E_RETRIEVAL=1` on the deterministic stack (35.8s, keyboard + 420px included). Review `review-f014-r1`: SF-1..SF-3 + M-1/M-2/L-1 dispositioned, no Critical/unfixed-High; residuals M-1/M-2 owner-visible.
- Documentation synced 2026-09-03: README (embedding row), DATABASE (F014 open-items record), ARCHITECTURE (adapter + external-service row + dependency note), API (payload extensions + event type), UX (grounding-honesty states), DESIGN_SYSTEM (shared citation chip), TESTING (F014 suites + E2E gate + deploy backfill), ADR-0007 + index. AGENTS unchanged (no command or module-ownership change).
- Delivery evidence 2026-09-03 (owner-authorized): deployed-stack chain PASS (build with baked weights via HF mirror + xet disabled, migrations applied, idempotent backfill step, smoke; sample re-seeded with real fastembed embeddings — 3 chunks ok, 3 plan artifacts `retrieved` with citations). Delivery found and fixed latent defect M-4 (worker never registered `lessoncanvas.parse_source`; queued uploads on the deployed stack never parsed — regression test added). TS-026 full live re-baseline under `retrieval_mode=fastembed`: all six passes `completed/pass` with zero blocking failures (previous truncation-era baseline had travelling-around p2 fail C-ART-1); retrieval quality judged plausible on every pass (teacher-intent source ranked first, cosine 0.61-0.81; reading passages 0.32-0.57). Evidence: `live-evidence.json`, `live-evidence-summary.txt`, runner `live-rebaseline-runner.py`; polluted first attempt (pre-M-4-fix) purged via the app's workspace deletion cascade and not part of the baseline.
- Pending delivery-time steps (each under separate owner authorization): commit/push/PR; main re-verification; Issue #28 status sync.

## Gate Record: SPEC READY

- Status: `PASS`
- Validation time: 2026-09-03
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-03 (question-form answers selecting D1 "本地进程内模型", D2 "部署时批量回填", D3 "排除+披露", D4 "继续+显式无grounding", D5 "交付时重跑全部 live pass", D6 "归入上传处理", D9 "三个工件族都检索"; D7/D8 recorded as maintainer judgment; explicit SPEC READY approval; Issue #28 creation separately authorized), scope: F014 Spec @ `21794b907af1`
- Checklist: 11/11 YES (Goal/Scope incl. Out-of-Scope, Flows, Rules/States incl. every degradation state, Data/API incl. migration + deploy-chain backfill step + settings, Errors/Security incl. preserved untrusted-input discipline, Idempotency/Concurrency incl. backfill idempotency and captured-set citations, Dependencies/Migration/Non-functional incl. ADR-0007 image-size/CPU impact, unique observable ACs AC-001..AC-007, OBSERVED baseline inventory retained in Background incl. the generation-injection gap that produced D9, no unresolved conflicts, no Critical Open Question OPEN/DEFERRED — UI presentation details routed to the UI READY gate)
- Related artifacts: ADR-0007 `docs/adr/0007-local-in-process-embedding-adapter.md` @ `b350468fa4fc` (Accepted, satisfies the required pre-coding L3 decision); work item [Issue #28](https://github.com/MaoyuanYang/LessonCanvas/issues/28)

## Refinement Decision Log

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| D1 | Embedding provider/model/dimension (L3) | Local in-process embedding model behind a thin adapter: `fastembed` + `BAAI/bge-small-zh-v1.5` (512-dim, zh-primary with en support, CPU inference, weights baked into the image for offline deploy). No external embedding API; the Phase-1 single-hosted-model constraint holds (the embedding adapter is in-process compute, not a second hosted service). Recorded as ADR-0007 before coding. A hosted embedding API would supersede the constraint and is rejected for Phase 2. | `YMY / Project Owner`, 2026-09-03 (interactive, "本地进程内模型") |
| D2 | Backfill policy for pre-migration chunks | Idempotent deploy-time batch backfill: a backfill step (management command invoked by the deploy chain, mirroring the migrate step) embeds all chunks lacking embeddings; it is idempotent, re-runnable, and its completion is part of deploy verification. No lazy first-retrieval embedding. | `YMY / Project Owner`, 2026-09-03 (interactive, "部署时批量回填") |
| D3 | Retrieval policy for `embedding_failed` / not-yet-embedded chunks | Exclude from similarity results with explicit disclosure: the retrieval trace event and evidence panel record the excluded chunk count and reasons. No bounded fallback injection of unranked text — the retrieved set stays semantically explainable. | `YMY / Project Owner`, 2026-09-03 (interactive, "排除+披露") |
| D4 | Zero-relevance behavior | Generation proceeds honestly ungrounded: the payload carries an explicit "no strongly related source content" state, surfaced in trace and UI; no fabricated grounding, no new human interruption point. Consistent with the existing no-sources behavior. | `YMY / Project Owner`, 2026-09-03 (interactive, "继续+显式无grounding") |
| D5 | F009 re-baselining under the new signature | Existing live evidence passes are marked incomparable once retrieval mode joins the pass-comparability signature; at F014 delivery a complete owner-authorized live re-baseline (all representative units, full pass set) is executed under the new signature. | `YMY / Project Owner`, 2026-09-03 (interactive, "交付时重跑全部 live pass") |
| D6 | Quota/rate classification of embedding compute | Embedding compute is part of upload processing (and deploy-time backfill), consuming local CPU only; it is bounded by the existing upload quota (200 MB/day) and per-source chunk caps. No new quota or rate-limit dimension; `max_model_calls_per_*` (API cost) is untouched. | `YMY / Project Owner`, 2026-09-03 (interactive, "归入上传处理") |
| D7 | Defaults for `k`, budget, and the final payload guard | Settings-driven: `retrieval_top_k = 6`, `retrieval_budget_chars = 2000`; the 2000-character cap remains as the final deterministic payload guard (rank-order trim when the top-k payload exceeds budget). | Maintainer judgment (refinement session), 2026-09-03; low-risk, tunable settings |
| D8 | Curriculum-standards retrieval path | Stays deterministic keyword scoring in this feature: the standards snapshot is a small static set, deterministic scoring is inspectable, and semantic recall over teacher sources is the actual gap. Moving standards onto the vector path is a future change with its own evidence. | Maintainer judgment (refinement session), 2026-09-03 |
| D9 | Scope of generation-side retrieval (found during refinement: generation payloads currently inject no source text at all) | All three artifact families (lesson plans, decks, exercises) retrieve per lesson and inject their own top-k chunks; each retrieval records its own trace event, and each artifact's citations bind to the chunk set actually retrieved for that artifact. Discovery's corpus use is regex-only field extraction (no model injection today) and stays unchanged. | `YMY / Project Owner`, 2026-09-03 (interactive, "三个工件族都检索") |

## Goal

Replace full-corpus truncation injection with genuine semantic recall over teacher sources using pgvector, and make every generated citation traceable to the exact chunk — with content hashes — that grounded it.

## Business Value

Generation grounding stops degrading as source volume grows (today the corpus is hard-truncated at 2000 characters regardless of relevance), and the project's documented "PostgreSQL+pgvector bounded retrieval" claim becomes true and inspectable instead of aspirational. Generation artifacts additionally become directly source-grounded for the first time (D9).

## User Story

As a senior-high English teacher, I want the system to read the parts of my materials that actually matter for each lesson and cite exactly where each grounded item came from, so that I can check the generated teaching package against my own sources chunk by chunk.

## Background

Baseline observed on `main` (capability audit 2026-09-03, re-verified during refinement):

- `README.md`, `docs/DATABASE.md`, and `docs/ARCHITECTURE.md` document PostgreSQL/pgvector retrieval, but no embedding exists anywhere: `SourceChunk` (`apps/backend/src/lessoncanvas/models.py`) carries only `source_id/position/text`; no vector column, embedding adapter, or `vector` extension migration was ever written. The `pgvector/pgvector:pg16` image and the `pgvector>=0.4` package are already present — the documentation was ahead of the code.
- Current grounding is full injection with truncation: `modules/discovery_planning/planning.py` (`build_grounding`) concatenates all ready chunks in position order, then `corpus_excerpt[:2000]` truncates in both `analyze_node` and `build_draft_node`.
- Discovery (`discovery_planning/graph.py` `build_corpus`) uses the corpus only for regex field extraction — no model injection, nothing to swap (D9).
- Generation payloads (lesson plans, decks, exercises) inject **no source text at all** — only lesson plan/blueprint/brief fields. Generation-side retrieval is therefore a new capability, not a truncation swap (D9).
- Curriculum-standards retrieval is deterministic keyword substring counting (`modules/sources_grounding/standards.py` `_score`), not similarity (D8: stays deterministic).
- Citations keep the right discipline (server-authoritative, never trusted from model payloads) but are coarse: `normalize_blueprint` attaches `grounding["sources"][0]` / first standards section per objective/lesson; there is no chunk-level provenance, and `Source` carries no content hash.
- The generation provider (DeepSeek, `adapters/model.py`) has no embedding endpoint; AGENTS.md Phase-1 constraint: one hosted model behind a thin adapter — resolved by D1/ADR-0007 (local in-process embedding).

## User Flow

1. The teacher uploads a source; the existing parse pipeline chunks it (unchanged behavior).
2. A new embedding step computes one vector per chunk at write time; a chunk that cannot be embedded keeps an explicit `embedding_failed` state with a recorded reason — never a silent gap (AC-001).
3. When planning (unit-level query from the confirmed brief) or any artifact family (per-lesson query from lesson topic/objectives and the confirmed plan) assembles grounding context, vector-similarity top-k retrieves the most similar chunks within the injection budget (D7); the retrieved set (query, chunk ids, similarity, budget use, excluded-chunk disclosure) is recorded as a trace event (AC-002).
4. Blueprint objectives/lessons and every generated artifact (plans, decks, exercises) cite source + chunk position + content hash, injected server-side from the actually retrieved chunks for that item (D9, AC-003).
5. The teacher sees retrieval-backed citations in the workspace and can trace any cited item back to the exact chunk of the original file; zero-relevance and excluded-chunk states are visible, never silent (D3/D4).

## Scope

- Thin embedding adapter (in-process, fastembed + bge-small-zh-v1.5, 512-dim) owned by Sources and Grounding behind settings keys; deterministic tests use a fixture/fake embedder (D1).
- One migration: `source_chunks.embedding vector(512)` with HNSW cosine index, `source_chunks.embedding_status`/`embedding_error`, `sources.content_sha256`, `source_chunks.text_sha256`; `CREATE EXTENSION IF NOT EXISTS vector`.
- Embedding at parse time for every new chunk, plus idempotent deploy-time batch backfill for pre-migration chunks (D2).
- Vector top-k retrieval service replacing truncation assembly at the planning call sites and adding per-lesson retrieval to all three generation families (D9); `k` and budget settings-driven (D7).
- Retrieval trace events with query, hits, similarities, budget use, and excluded-chunk disclosure (D3); explicit zero-relevance state (D4).
- Chunk-level, hash-bound, server-injected citations on blueprint objectives/lessons and generated artifacts (D9).
- F009 pass-comparability signature gains retrieval mode; full live re-baseline at delivery (D5).
- F011 deletion-completeness coverage for new columns; embedding compute classified under upload processing with no new quota dimension (D6).
- UI surfaces: chunk-level citation display in blueprint/artifact views and retrieval disclosure in the evidence panel (UI READY gate applies).

### Out of Scope

- Moving curriculum-standards retrieval onto the vector path (D8).
- Hosted embedding APIs, model routing, or any second hosted service (D1).
- Changing discovery's regex-based field extraction (D9).
- Re-chunking or re-parsing existing sources (chunk boundaries stay as delivered).

## Requirements

- Embedding runs behind a thin adapter per ADR-0007; provider, model, and dimension are settled by D1 and must not change without a superseding ADR.
- Embeddings are computed once at write time (parse hook) or by the deploy-time backfill (D2) — never per read.
- Vector retrieval replaces truncation assembly at planning call sites and adds per-lesson grounding to all three generation families (D9); `retrieval_top_k` and `retrieval_budget_chars` are settings-driven with the 2000-character final payload guard retained (D7).
- Untrusted-input discipline is preserved unchanged: retrieved text travels only as a labeled JSON user payload (the `corpus_excerpt` pattern, renamed for retrieval), never inside system prompts.
- Citations remain server-authoritative; each blueprint objective/lesson and each generated artifact cites the chunk set actually retrieved for that item (source id, chunk position, text hash) (D9).
- Honest degradation per D3/D4: excluded chunks disclosed per retrieval; zero-relevance proceeds with an explicit ungrounded state; never a silent full-injection fallback.
- The F009 pass-comparability signature includes retrieval mode; existing live passes are marked incomparable and a full owner-authorized live re-baseline executes at delivery (D5).
- F011 integration: new columns are covered by deletion-completeness verification; embedding compute stays within upload-processing bounds with no new quota dimension (D6).

## Edge Cases

- Embedding unavailable at parse time: chunk persists with `embedding_failed` + reason; retrieval excludes it with per-retrieval disclosure (D3).
- Chunks uploaded before the migration: embedded by the idempotent deploy-time backfill (D2); until backfill completes they are excluded-with-disclosure, never silently injected.
- Query with no chunks above the relevance threshold: explicit "no strongly related source content" state; generation proceeds honestly ungrounded (D4).
- Injection budget smaller than the top-k payload: deterministic rank-order trim with budget use recorded (D7).
- Superseded source between retrieval and citation injection: citations derive from the same captured retrieval set, so they cannot reference a chunk that was not retrieved.

## API / Data Changes

- One migration: `source_chunks.embedding vector(512)` (+ HNSW cosine index), `source_chunks.embedding_status`, `source_chunks.embedding_error`, `sources.content_sha256`, `source_chunks.text_sha256`.
- No new public endpoints expected; blueprint, artifact, and evidence payloads gain chunk-level citation and retrieval-disclosure fields (contract updates recorded in `docs/API.md` at SPEC READY).
- New settings: `embedding_model` (adapter-internal), `retrieval_top_k`, `retrieval_budget_chars` (D7).
- Deploy chain gains an idempotent backfill step after migrate (D2); `infra/scripts/deploy.sh` and `docs/TESTING.md` updated together.

## Acceptance Criteria

- [ ] AC-001 Every parsed chunk of a new source has a stored embedding or an explicit `embedding_failed` state with a recorded reason; never NULL-and-silent.
- [ ] AC-002 Grounding context for planning and for every generation family (plans, decks, exercises) is selected by vector-similarity top-k within budget, and each retrieval records query, hit chunk ids, similarity scores, budget use, and excluded-chunk disclosure in a trace event.
- [ ] AC-003 Blueprint objectives/lessons and generated artifacts of all three families cite source + chunk position + content hash, and every cited chunk belongs to the retrieved set for that item (server-injected, payload citations never trusted).
- [ ] AC-004 Deterministic tests prove ranking behavior (a relevant chunk outranks an irrelevant one on constructed corpora) and every degradation path: embedding failure exclusion, zero-relevance explicit state, budget trim, backfill idempotency.
- [ ] AC-005 The F009 comparability signature includes retrieval mode; existing live passes are marked incomparable; a complete owner-authorized live re-baseline under the new signature is recorded at delivery.
- [ ] AC-006 F011 deletion-completeness covers the new columns and data; embedding compute stays classified under upload processing with no silent quota change.
- [ ] AC-007 README, DATABASE, ARCHITECTURE, and TESTING describe the implemented pipeline (documentation and code agree).

## Incremental Development Roadmap

### Step 1: ADR + embedding adapter

- **Goal:** settle D1 and land the thin embedding adapter.
- **Scope:** ADR-0007 (Accepted), `adapters/embedding.py` (in-process fastembed + fixture fake for tests), settings keys, weights-in-image decision recorded.
- **Tests:** adapter contract tests with fixture vectors; fake-embedder determinism.
- **Verification:** suite green; ADR Accepted before Step 2.

### Step 2: Write path

- **Goal:** every chunk is embedded (or explicitly failed) at parse time; legacy chunks embedded by deploy-time backfill.
- **Scope:** migration (vector column, HNSW cosine index, embedding status/error, content/text hashes, `vector` extension), parse pipeline hook, idempotent backfill command wired into the deploy chain (D2).
- **Tests:** migration round-trip, embedding failure states, backfill idempotency (re-run embeds nothing new).
- **Verification:** a parsed source shows embeddings (or reasons) for all chunks; backfill re-run is a no-op.

### Step 3: Retrieval + call-site swap

- **Goal:** similarity top-k replaces truncation at planning and lands in all three generation families (D9).
- **Scope:** retrieval service in Sources and Grounding; planning (unit-level) and per-lesson generation queries; retrieval trace events with D3/D4 disclosure; `retrieval_top_k`/`retrieval_budget_chars` settings and rank-order trim (D7).
- **Tests:** ranking on constructed corpora, budget trim, exclusion disclosure, zero-relevance state, untrusted-payload discipline preserved; adversarial corpus-injection suite extends to retrieved chunks.
- **Verification:** trace shows per-retrieval hits; planning corpus comes from top-k; generation payloads carry retrieved chunks or the explicit ungrounded state.

### Step 4: Citations + hashes

- **Goal:** chunk-level, hash-bound, server-injected citations.
- **Scope:** `normalize_blueprint` citation construction from retrieved sets; artifact metadata citations per artifact's own retrieval; evidence/blueprint UI rendering of chunk-level citations (UI READY covers the surfaces).
- **Tests:** cited ⊆ retrieved per item; hash stability across re-render; payload-supplied citations rejected.
- **Verification:** a cited objective or artifact in the UI resolves to the exact chunk of the original file.

### Step 5: Evaluation, guardrails, docs

- **Goal:** comparability, quota/deletion verification, honest documentation, live re-baseline.
- **Scope:** F009 signature field + incomparability marking (D5); F011 deletion sweep for new columns + D6 classification check; README/DATABASE/ARCHITECTURE/TESTING sync; owner-authorized full live re-baseline at delivery.
- **Tests:** evaluation deterministic scenarios updated for the signature field; deletion sweep covers new columns.
- **Verification:** AC-005/AC-006/AC-007 satisfied with recorded evidence.

## Test Plan

Deterministic backend tests for the adapter (fixture vectors), migration round-trip, ranking on constructed corpora, citation binding, degradation paths (exclusion, zero-relevance, trim, backfill idempotency); the adversarial corpus-injection suite extends to retrieved chunks (retrieved text stays inert payload); F009 deterministic scenarios updated for the signature field; one owner-authorized full live re-baseline at delivery (D5). Commands: `uv run pytest`, `uv run ruff check src tests migrations`, plus web suites for the citation/evidence UI changes.

## Open Questions

All DRAFT questions are resolved in the Decision Log (D1–D9, owner-interactive unless noted as maintainer judgment); none remain `OPEN`. UI-level presentation details (citation chip content, disclosure placement) are routed to the UI READY gate.

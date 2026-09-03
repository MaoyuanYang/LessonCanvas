# F014: Semantic Source Retrieval

- Spec Status: `DRAFT`
- Roadmap Status: `NEXT`
- Priority: `P0`
- Owner: `YMY / Project Owner`
- Decision Authority: `YMY / Project Owner`
- Dependencies: None hard (Phase 1 complete); integrates with delivered F001 grounding, F003–F005 generation call sites, F006 evidence trace, F009 evaluation pinning, F011 quota/deletion guardrails
- Last Updated: 2026-09-03 (initial draft, Phase-2 planning)

## Goal

Replace full-corpus truncation injection with genuine semantic recall over teacher sources using pgvector, and make every generated citation traceable to the exact chunk — with content hashes — that grounded it.

## Business Value

Generation grounding stops degrading as source volume grows (today the corpus is hard-truncated at 2000 characters regardless of relevance), and the project's documented "PostgreSQL+pgvector bounded retrieval" claim becomes true and inspectable instead of aspirational.

## User Story

As a senior-high English teacher, I want the system to read the parts of my materials that actually matter for each lesson and cite exactly where each grounded item came from, so that I can check the generated teaching package against my own sources chunk by chunk.

## Background

Baseline observed on `main` (capability audit, 2026-09-03):

- `README.md`, `docs/DATABASE.md`, and `docs/ARCHITECTURE.md` document PostgreSQL/pgvector retrieval, but no embedding exists anywhere: `SourceChunk` (`apps/backend/src/lessoncanvas/models.py`) carries only `source_id/position/text`; there is no vector column, no embedding adapter, and git history (`-S "Vector("` / `-S "embedding"`) shows none was ever implemented and later removed.
- Current grounding is full injection with truncation: `modules/discovery_planning/planning.py` (`build_grounding`) and `discovery_planning/graph.py` (`build_corpus`) concatenate all ready chunks in position order, then `corpus_excerpt[:2000]` truncates.
- Curriculum-standards retrieval is deterministic keyword substring counting (`modules/sources_grounding/standards.py` `_score`), not similarity.
- Citations keep the right discipline (server-authoritative, never trusted from model payloads) but are coarse: `normalize_blueprint` attaches `grounding["sources"][0]` per objective/lesson; there is no chunk-level provenance, and `Source` carries no content hash.
- The generation provider (DeepSeek, `adapters/model.py`) has no embedding endpoint. AGENTS.md Phase-1 constraint: one hosted model behind a thin adapter; no second service without evidence and impact analysis — the embedding choice is therefore an L3 decision requiring an ADR before coding.

## User Flow

1. The teacher uploads a source; the existing parse pipeline chunks it (unchanged behavior).
2. A new embedding step computes one vector per chunk at write time; a chunk that cannot be embedded keeps an explicit `embedding_failed` state with a recorded reason — never a silent gap.
3. When discovery, planning, or artifact generation assembles grounding context, a query derived from the confirmed intent / lesson topic retrieves the top-k most similar chunks within the injection budget; the retrieved set (chunk ids, similarity, budget use) is recorded as a trace event.
4. Blueprint and artifact citations are injected server-side from the actually retrieved chunks, naming source, chunk position, and content hash.
5. The teacher sees retrieval-backed citations in the workspace and can trace any cited item back to the exact chunk of the original file.

## Requirements

- Embedding runs behind a thin adapter owned by Sources and Grounding; provider, model, and dimension are decided by ADR (Open Question D1) before coding starts.
- Migration adds `source_chunks.embedding vector(<dim>)` with a cosine ANN index (HNSW), plus `sources.content_sha256` and `source_chunks.text_sha256`; embeddings are computed once at write time, never per read.
- Vector retrieval replaces truncation assembly at every current grounding call site (discovery analysis, planning grounding, per-lesson generation); `k` and the injection budget are settings-driven and traced per retrieval.
- Untrusted-input discipline is preserved unchanged: retrieved text travels only as a labeled JSON user payload (the `corpus_excerpt` pattern), never inside system prompts.
- Citations remain server-authoritative; each objective/lesson citation binds to the chunk set actually retrieved for that item (source id, chunk position, text hash).
- Honest degradation: chunks without embeddings (failed or pre-migration) follow an explicit, trace-visible policy (Open Question D3) — no silent full-injection fallback.
- Retrieval mode joins the F009 pass-comparability signature so mixed-retrieval evaluation passes cannot compare silently (Open Question D5).
- F011 integration: new columns covered by the deletion-completeness verification; embedding compute classified against quotas per Open Question D6.

## Edge Cases

- Embedding unavailable at parse time: chunk persists with `embedding_failed` + reason; retrieval handles it per D3 with disclosure in trace and evidence.
- Chunks uploaded before the migration: backfill per D2 (batch task vs lazy on first retrieval).
- Query with no chunks above the relevance threshold: honest "no strongly related source content" state; generation proceeds or pauses per D4 — never fabricated grounding.
- Injection budget smaller than the top-k payload: deterministic trim by rank, with budget use recorded.
- Superseded source between retrieval and citation injection: citations derive from the same captured retrieval set, so they cannot reference a chunk that was not retrieved.

## API / Data Changes

- One migration: `source_chunks.embedding` (+ HNSW cosine index), `sources.content_sha256`, `source_chunks.text_sha256`.
- No new public endpoints expected; blueprint, artifact, and evidence payloads gain chunk-level citation fields (contract updates recorded in `docs/API.md` at SPEC READY).

## Acceptance Criteria

- [ ] AC-001 Every parsed chunk of a new source has a stored embedding or an explicit `embedding_failed` state with a recorded reason; never NULL-and-silent.
- [ ] AC-002 Grounding context for planning and generation is selected by vector-similarity top-k within budget, and each retrieval records query, hit chunk ids, similarity scores, and budget use in a trace event.
- [ ] AC-003 Blueprint objectives/lessons and generated artifacts cite source + chunk position + content hash, and every cited chunk belongs to the retrieved set for that item (server-injected, payload citations never trusted).
- [ ] AC-004 Deterministic tests prove ranking behavior (a relevant chunk outranks an irrelevant one on constructed corpora) and every degradation path.
- [ ] AC-005 The F009 comparability signature includes retrieval mode, and evaluation passes record which retrieval produced them.
- [ ] AC-006 README, DATABASE, ARCHITECTURE, and TESTING describe the implemented pipeline (documentation and code agree).

## Incremental Development Roadmap

### Step 1: ADR + embedding adapter

- **Goal:** settle D1 (provider/model/dimension) and land a thin embedding adapter.
- **Scope:** new ADR (Accepted), `adapters/` embedding adapter, settings keys.
- **Tests:** adapter contract tests with fixture vectors.
- **Verification:** suite green; ADR Accepted before Step 2.

### Step 2: Write path

- **Goal:** every new chunk is embedded (or explicitly failed) at parse time.
- **Scope:** migration (vector column, hashes, index), parse pipeline hook, legacy backfill per D2.
- **Tests:** migration round-trip, embedding failure states, backfill idempotency.
- **Verification:** a parsed source shows embeddings (or reasons) for all chunks in the database.

### Step 3: Retrieval + call-site swap

- **Goal:** similarity top-k replaces truncation assembly at all grounding call sites.
- **Scope:** retrieval service in Sources and Grounding, discovery/planning/generation call sites, retrieval trace events.
- **Tests:** ranking, budget trim, degradation paths, untrusted-payload discipline preserved.
- **Verification:** trace shows per-retrieval hits; planning corpus comes from top-k.

### Step 4: Citations + hashes

- **Goal:** chunk-level, hash-bound, server-injected citations.
- **Scope:** `normalize_blueprint` citation construction, artifact metadata, evidence rendering.
- **Tests:** cited ⊆ retrieved; hash stability across re-render.
- **Verification:** a cited objective in the UI resolves to the exact chunk.

### Step 5: Evaluation, guardrails, docs

- **Goal:** comparability, quota/deletion verification, honest documentation.
- **Scope:** F009 signature, F011 sweep/quota checks, README/DATABASE/ARCHITECTURE/TESTING sync.
- **Tests:** evaluation deterministic scenarios updated; deletion sweep covers new columns.
- **Verification:** AC-005/AC-006 satisfied; owner-authorized live evidence at delivery.

## Test Plan

Deterministic backend tests for the adapter, migration, ranking, citation binding, and degradation; the adversarial corpus-injection suite extends to retrieved chunks (retrieved text stays inert payload); F009 deterministic scenarios updated for the signature field; one owner-authorized live evidence pass at delivery. Commands: `uv run pytest`, `uv run ruff check src tests migrations`, plus web suites if evidence/citation surfaces change.

## Open Questions

- D1 Embedding provider/model/dimension (L3, ADR required). Leading option: a local in-process embedding model (e.g. fastembed + bge-small-zh-v1.5, 512-dim, zh/en bilingual, CPU) to keep the single-hosted-LLM constraint; a hosted embedding API would supersede the Phase-1 constraint and needs explicit owner approval in the ADR.
- D2 Backfill policy for pre-migration chunks: batch task vs lazy embedding on first retrieval.
- D3 Retrieval policy for `embedding_failed` chunks: exclude-with-disclosure vs bounded fallback injection.
- D4 Zero-relevance behavior: proceed honestly ungrounded vs pause for teacher attention.
- D5 F009 re-baselining: whether existing live evidence passes are re-run or marked incomparable with the new signature.
- D6 Deployment and quota impact of the embedding dependency (image size, offline deploy for local weights; whether embedding compute counts against any quota).
- D7 Defaults for `k` and budget; whether the 2000-character `corpus_excerpt` truncation remains as a final payload guard.
- D8 Whether curriculum-standards retrieval moves onto the same vector path or stays deterministic keyword scoring.

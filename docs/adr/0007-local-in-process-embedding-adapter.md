# Use a Local In-Process Embedding Model Behind a Thin Adapter for Semantic Source Retrieval

- Status: `Accepted`
- Date: 2026-09-03
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: None

## Context

F014 (Semantic Source Retrieval) makes the documented pgvector grounding real: chunk embeddings at write time, vector-similarity top-k retrieval, chunk-level citations. The delivered stack has exactly one hosted model (DeepSeek) behind a thin adapter (`adapters/model.py`), and DeepSeek offers no embedding endpoint. AGENTS.md therefore requires an L3 decision before coding: every option that adds a model or service must be weighed against the Phase-1 constraints — one hosted model, no second database/cache/queue/service without evidence and impact analysis, offline-capable local deployment (F012 deployed topology), and no training or cross-user reuse of teacher content.

## Decision

Embeddings are computed by a local in-process model behind a thin adapter owned by Sources and Grounding:

- Provider/runtime: `fastembed` (ONNX runtime, CPU inference, in-process — not a network service).
- Model: `BAAI/bge-small-zh-v1.5`, 512 dimensions (zh-primary with English support; the corpus is senior-high English teaching material with mixed Chinese/English teacher documents and queries derived from Chinese-language brief fields).
- Weights are baked into the deployed image so deployment stays offline-capable and deterministic; no runtime download.
- The adapter mirrors the model adapter's shape (`adapters/embedding.py`, settings-driven, contract-tested); deterministic tests use a fixture/fake embedder and never load real weights.
- The adapter is not model routing: one embedding model, one dimension, swapped only by a superseding ADR. A dimension change is a destructive migration (re-embed everything) and must be treated accordingly.
- Hosted embedding APIs remain excluded in Phase 2; adopting one would supersede this ADR and the Phase-1 single-hosted-model constraint.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Hosted embedding API (OpenAI/Jina/…) | Strongest multilingual quality; zero local compute | Supersedes the single-hosted-model constraint, adds an external dependency and per-call cost, breaks offline deployment, widens the untrusted-egress surface for teacher content |
| Local multilingual model (e.g. `multilingual-e5-small`, 384-dim) | More balanced zh/en recall on English-heavy corpora | ~5× larger weights (~470 MB) inflating the deployed image; senior-high English queries are predominantly Chinese-driven, making the zh-primary model the better size/quality fit; the thin adapter keeps a later swap cheap |
| Lexical-only retrieval (Postgres full-text / trigram), no embeddings | No new dependency at all | Fails the Phase-2 milestone's semantic-similarity goal and leaves the documented pgvector claim unimplemented; lexical recall also degrades on paraphrased teaching content |
| DeepSeek-adjacent embedding endpoint | No new vendor | Does not exist; DeepSeek exposes no embedding API |

## Reasoning

An in-process model keeps the deployed topology exactly as F012 verified it (single hosted LLM, no new service), respects the privacy constraint that teacher content never leaves the trust boundary except to the one approved LLM, and makes embedding compute free at the margin — which is what allows classifying it under upload processing (F014 D6) instead of inventing a new quota dimension. `bge-small-zh-v1.5` is the smallest credible bilingual option for a zh-query/en-corpus workload, and the adapter boundary means the model choice is a one-line settings change behind contract tests if live evidence (F014 delivery) shows weak recall.

## Consequences

- Positive: pgvector grounding becomes real with zero new network services; offline/local deployment preserved; deterministic test path via a fake embedder.
- Positive: embedding compute is bounded local CPU inside upload processing and deploy-time backfill — no new quota surface.
- Negative / tradeoff: image size grows (~100 MB weights plus ONNX runtime); CPU time is added to parsing and deploy backfill.
- Negative / tradeoff: zh-primary model may under-rank rare English-heavy corpora; mitigated by the adapter boundary and the delivery-time live re-baseline (F014 D5).
- Follow-up: retrieval quality is judged at F014 delivery evidence; swapping model or dimension requires a superseding ADR and a full re-embed migration.

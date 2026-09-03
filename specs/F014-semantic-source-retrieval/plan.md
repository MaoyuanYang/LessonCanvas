# F014 Implementation Plan — Semantic Source Retrieval

- Plan ID: `plan-f014-r1`
- Inputs (Gate-validated): Spec (SPEC READY PASS 2026-09-03), UX/UI @ `ux-ui-f014-r1` / `f913f17b7f41` (`UI READY`, 2026-09-03), Test Design @ `test-design-f014-r1` (TS-001..TS-027), ADR-0007 `Accepted`
- This Plan answers only how to implement; requirements live in the Spec. It adds no rule, no Scope, and no contract change.

## Architecture fit

- Thin embedding adapter `apps/backend/src/lessoncanvas/adapters/embedding.py` behind settings (`embedding_adapter: fake|fastembed`, model fixed by ADR-0007); consumed only by Sources and Grounding. Deterministic tests use the fake; real weights never load in CI.
- Retrieval service `modules/sources_grounding/retrieval.py`: query embedding via adapter → pgvector cosine top-k over `source_chunks.embedding` → exclusion aggregation (`embedding_failed`/not-embedded, D3) → rank-order budget trim (D7) → result structure with disclosure fields. Read-only; no workflow authority.
- Call sites (D9): planning `build_grounding` (unit-level query from confirmed brief fields) and the three artifact graphs' per-lesson context assembly (query from lesson title/objectives + confirmed plan). Discovery unchanged.
- Trace: `retrieval.semantic_search` events through the existing `record_trace`/`append_event` helpers (Run Orchestration boundary; no second authority).
- Citations: `normalize_blueprint` attaches citations from the captured planning retrieval set; artifact graphs attach citations from each artifact's own per-lesson retrieval set; payload-supplied citations stripped everywhere (server-authoritative).
- Backfill: management command (idempotent, batched, failure-isolated) wired into `infra/scripts/deploy.sh` after migrate; deploy smoke extended.
- F009: `_config_signature` gains retrieval mode; legacy live passes render marked incomparable.
- Web: shared citation-chip component (two documented variants) consumed by blueprint + three artifact panels; sources-panel chunk expansion; evidence label-table entry + summary chips; `lib/api.ts` types extended. No new endpoints; payload extensions only.

## Data and migration

- One Alembic migration (head after `f013b1d2e3f4`):
  - `CREATE EXTENSION IF NOT EXISTS vector`
  - `source_chunks.embedding vector(512)` nullable, HNSW index (`vector_cosine_ops`)
  - `source_chunks.embedding_status` (`ok|failed|pending` default `pending`), `source_chunks.embedding_error` text nullable
  - `source_chunks.text_sha256` char(64), `sources.content_sha256` char(64); backfilled in-migration for legacy rows (hash-only; embedding via deploy backfill D2)
- `tests/conftest.py` truncate list unchanged for new columns (same tables); F011 deletion sweep needs no new table but gains column-level assertions (TS-017).

## Settings

- `embedding_adapter: str = "fake"` default in code (safe), `"fastembed"` in deployed env; `embedding_model = "BAAI/bge-small-zh-v1.5"`, `retrieval_top_k = 6`, `retrieval_budget_chars = 2000`, `retrieval_similarity_threshold` (zero-relevance bound), `citation_excerpt_chars = 200` (D7/U1).

## Tasks (vertical slices)

- **T0 — Branch, adapter, settings**: branch `feature/F014-semantic-source-retrieval`; `adapters/embedding.py` (fake + fastembed behind settings, import-guarded) + settings keys; tests TS-001. Proof: adapter contract suite green; full suite still green.
- **T1 — Migration + write path**: migration (extension, vector column, HNSW, status/error, hashes, legacy hash backfill); parse-pipeline hook embeds each chunk (`ok` or `embedding_failed`+reason, re-parse heals); tests TS-002, TS-003. Proof: parsed source shows embeddings/reasons for all chunks.
- **T2 — Deploy backfill**: idempotent management command + `deploy.sh` step after migrate + smoke check; tests TS-004. Proof: backfill re-run is a no-op.
- **T3 — Retrieval service**: top-k + exclusion aggregation + budget trim + zero-relevance state + tie-breaking rule; service-level tests TS-005, TS-006, TS-009, TS-010. Proof: ranking/trim/degradation deterministic on constructed corpora.
- **T4 — Call-site swap + trace**: planning payload from retrieval (truncation removed); per-lesson retrieval wired into plan/deck/exercise graphs with `retrieval.semantic_search` events; injection discipline (labeled user payload); tests TS-007, TS-008, TS-009, TS-015. Proof: trace shows per-retrieval hits for all four surfaces.
- **T5 — Citations + hashes**: `normalize_blueprint` chunk citations (position, hash, excerpt) from captured set; per-family artifact citation injection; payload-citation stripping; tests TS-011..TS-014, TS-020. Proof: cited ⊆ retrieved everywhere; UI-resolvable citations in payloads.
- **T6 — Evaluation + guardrails**: F009 signature + legacy incomparability marking; F011 deletion-sweep column assertions; D6 quota-classification checks; sources/events contract surfaces; tests TS-016, TS-017, TS-018, TS-019. Proof: comparability and deletion evidence green.
- **T7 — Web surfaces**: shared citation chip (source-chunk expandable + standards variants), blueprint panel adoption, three artifact panels (chips + 无强相关来源语料 notice), sources chunk expansion (未嵌入 disclosure), evidence retrieval rows + label; tests TS-021..TS-024. Proof: web suite green.
- **T8 — E2E + a11y + responsive**: deterministic browser journey (upload → brief → planning citations → generation → evidence), keyboard pass, 420px spot; tests TS-025. Proof: journey green.
- **T9 — Live re-baseline (owner-authorized at execution)**: real fastembed stack; complete F009 live pass set under the new signature; per-pass retrieval-quality judgment; evidence files; tests TS-026.
- **T10 — Regression, review, docs sync**: TS-027 full sweep; Self Review (`review.md`); documentation sync — README (pgvector claim now true), DATABASE (columns/index/backfill), ARCHITECTURE (embedding adapter boundary), API (payload extensions, event type), UX/UI (new states), DESIGN_SYSTEM (shared citation-chip variant), TESTING (embedding fake convention, live re-baseline), AGENTS only if commands change; ROADMAP + Issue #28 status.

## Transaction / consistency notes

- Parse-time embedding runs inside the existing parse transaction (chunk rows + status written together); adapter failure records per-chunk reasons without aborting the source.
- Backfill batches chunks with per-chunk commits; re-entrancy via `embedding_status` (`pending` only).
- Retrieval is read-only; each call site captures its retrieval set once and citations derive from that captured set (supersession-safe by construction, TS-020).
- Run retries/idempotency unchanged: a retried run re-retrieves only within its own execution; settled artifacts and their citations stay immutable.

## Verification cadence

- Per task: focused `uv run pytest` slices (`-k` retrieval/embedding/citation) + `corepack pnpm web:test` for T7/T8; full sweep (TS-027) before review.
- Exit conditions: all TS rows evidence-backed (except TS-026 pending delivery-time authorization), suites green, review findings fixed or dispositioned, docs synced.

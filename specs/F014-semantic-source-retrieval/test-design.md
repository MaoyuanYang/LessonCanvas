# Feature Test Design: F014 Semantic Source Retrieval

## Metadata

- Spec/Issue: `specs/F014-semantic-source-retrieval/spec.md` / [GitHub Issue #28](https://github.com/MaoyuanYang/LessonCanvas/issues/28)
- Validated inputs: Spec (SPEC READY PASS 2026-09-03), UX/UI @ `ux-ui-f014-r1` / `f913f17b7f41` (`UI READY`, 2026-09-03), ADR-0007 `Accepted`
- Test Design revision: `test-design-f014-r1`
- Coverage scope: recommended risk-based scope (mirrors the owner-confirmed F013 scope class): functional happy/alternative/boundary/error-recovery, injection defense, idempotency/duplicate/concurrency, migration/backward compatibility, API contract, observability, UI interaction/state + accessibility + responsive spot, deterministic E2E, one owner-authorized live retrieval + full live re-baseline at delivery. Excluded with reasons: ANN index performance/load/stress `N/A - corpus bounded by upload caps and chunk limits; no perf infrastructure; correctness covered by ranking tests`; real-model semantic-quality variance in CI `N/A - deterministic fake embedder in CI; quality judged once in TS-026 live evidence (D5)`; fuzz/property-based `N/A - ranking and trim determinism covered by constructed corpora fixtures`; visual regression `N/A - no infrastructure; component + E2E cover UI acceptance`; cross-browser `N/A - repo convention chromium`; i18n `N/A - zh-Hans inline copy per repo convention`; deployment/rollback `covered operationally - backfill is an idempotent deploy step tested by TS-004; no topology change (ADR-0007)`.
- Environments: (a) deterministic developer stack (compose infra + process app + fake model adapter + fake/deterministic embedding adapter + eager tasks, existing `conftest.py` pattern) for backend; (b) deterministic browser stack for E2E; (c) live stack (real fastembed weights + real DeepSeek) only for TS-026 under separate owner authorization at delivery.
- `TEST DESIGN READY` Status: `PASS` (see Gate Record)

## Gate Record: TEST DESIGN READY

- Status: `PASS`
- Validation time: 2026-09-03
- Decision Authority: `YMY / Project Owner` — approved together with `plan-f014-r1` via interactive session on 2026-09-03 (explicit TEST DESIGN READY + Plan approval)
- Checklist: every AC mapped to ≥1 scenario; every Spec decision D1–D9 traced; degradation paths (D2/D3/D4) each covered; untrusted-input discipline covered; risk register complete; deterministic/live separation explicit; environments realistic; no Critical coverage gap

## Risk Register and Scenario Selection

| Risk / behavior | Impact | Scenario(s) |
| --- | --- | --- |
| Chunk silently lacks embedding (NULL-and-silent) | Silent grounding gap; AC-001 broken | TS-001, TS-002 |
| Backfill non-idempotent / never completes for legacy data | Degraded recall forever; D2 broken | TS-004 |
| Ranking wrong or nondeterministic | Retrieval claim false | TS-005 |
| Budget trim silent or wrong order | Unbounded payloads / dishonest trace | TS-006 |
| Call sites still truncate or miss a family (D9) | Grounding claim partially false | TS-007, TS-008 |
| Failed/unembedded chunks silently injected or silently dropped | D3 broken; silent degradation | TS-010 |
| Zero relevance hidden or blocking | D4 broken; fabricated grounding risk | TS-009 |
| Citations cite unretrieved chunks or trust payload citations | Server-authority violation | TS-011, TS-012, TS-013 |
| Hash unstable or computed over wrong content | Traceability claim false | TS-014 |
| Retrieved text escapes labeled-payload boundary | Injection breach | TS-015 |
| F009 passes compare across retrieval modes | Evaluation honesty broken | TS-016 |
| Deletion leaves embedding/hash data | Privacy violation | TS-017 |
| Embedding compute misclassified into quotas | Silent quota change | TS-018 |
| Contract drift (sources chunk list, event payloads, citation fields) | UI/evidence breakage | TS-019, TS-024 |
| Cited source deleted later; historical honesty | Stale/false provenance display | TS-020 |
| UI hides citations, exclusions, or ungrounded state | Teacher-visible honesty broken | TS-021..TS-025 |
| Retrieval quality unproven with real model | ADR-0007 follow-up unmet; claim unverified | TS-026 |
| Existing suites regress | Completed features broken | TS-027 |

Happy Path: TS-001/TS-002/TS-007/TS-008/TS-011/TS-012/TS-021; Alternative/boundary: TS-005/TS-006/TS-014; Error/security: TS-009/TS-010/TS-013/TS-015; Recovery: TS-004/TS-020; Concurrency/idempotency: TS-004/TS-018; Migration/compat: TS-003; Observability: TS-007/TS-008/TS-010/TS-016; UI: TS-021..TS-025; Live: TS-026; Regression: TS-027.

## Acceptance Traceability

| AC | Scenario(s) |
| --- | --- |
| AC-001 | TS-001, TS-002, TS-003, TS-004 |
| AC-002 | TS-006, TS-007, TS-008, TS-010, TS-019, TS-024 |
| AC-003 | TS-011, TS-012, TS-013, TS-014, TS-020, TS-021, TS-022 |
| AC-004 | TS-004, TS-005, TS-006, TS-009, TS-010 |
| AC-005 | TS-016, TS-026 |
| AC-006 | TS-017, TS-018 |
| AC-007 | TS-027 (documentation sync verified in review) |
| D1/ADR-0007 | TS-001, TS-026 |
| D9 (three families) | TS-008, TS-012, TS-022 |
| Injection discipline | TS-015 |
| Regression of completed features | TS-027 |

## Scenarios

### TS-001: Embedding adapter contract

- Protects: AC-001, ADR-0007 (thin adapter, deterministic test path)
- Risk/type: Functional / Happy path + boundary
- Steps: instantiate the adapter behind `embedding_adapter` settings; fake implementation returns stable 512-dim vectors for identical input and distinct vectors for distinct input; real implementation is import-guarded (weights absent → explicit error, not a crash); a raised provider error maps to a recorded reason.
- Expected: adapter returns dimension-consistent vectors deterministically; no test loads real weights; errors carry machine-readable reasons.

### TS-002: Parse-time embedding write path

- Protects: AC-001 (every new chunk embedded or explicitly failed)
- Risk/type: Functional / Happy + error path
- Steps: upload + parse a source with the fake adapter healthy → all chunks `embedding_status='ok'` with vectors; force adapter failure for one parse → affected chunks persist `embedding_failed` + reason, source still becomes ready; re-parse re-attempts embedding.
- Expected: never NULL-and-silent; failure never blocks source readiness; re-parse heals.

### TS-003: Migration round-trip

- Protects: AC-001/AC-004 (migration compat)
- Risk/type: Migration / backward compatibility
- Steps: run the migration on a database with pre-existing sources/chunks; inspect: `vector` extension created, `embedding vector(512)` column with HNSW cosine index, `embedding_status`/`embedding_error` defaults, `sources.content_sha256` and `source_chunks.text_sha256` populated for legacy rows.
- Expected: legacy rows get status default and hashes; index exists with cosine ops; round-trip read/write of a vector value works.

### TS-004: Deploy-time backfill idempotency

- Protects: AC-004, D2
- Risk/type: Idempotency / recovery
- Steps: run the backfill command on legacy chunks (fake adapter) → all embedded; run again → zero new embeddings, no writes; interrupt mid-run → re-run completes the remainder exactly once; chunks with permanent failure end `embedding_failed` + reason and are skipped on re-run without blocking others.
- Expected: idempotent, resumable, failure-isolated.

### TS-005: Ranking determinism on constructed corpora

- Protects: AC-004 (relevant outranks irrelevant)
- Risk/type: Functional / boundary
- Steps: construct a corpus where the fake adapter gives query-near vectors to relevant chunks and distant vectors to irrelevant ones; retrieve top-k; assert order by similarity descending and stable across repeated calls.
- Expected: deterministic rank order; equal-similarity ties broken by (position asc, chunk id) recorded rule.

### TS-006: Top-k selection and budget trim

- Protects: AC-002, D7
- Risk/type: Functional / boundary
- Steps: set `retrieval_top_k` and `retrieval_budget_chars` so the top-k payload exceeds budget; retrieve; assert rank-order trim (highest similarity kept first), `used_chars`/`budget_chars` recorded, trim disclosed in the result structure.
- Expected: deterministic trim by rank; budget use always recorded; no silent overflow.

### TS-007: Planning call-site swap

- Protects: AC-002 (planning grounding by retrieval, traced)
- Risk/type: Functional / happy path + observability
- Steps: ready sources with fake embeddings; run planning; assert the analyze/draft user payloads carry the retrieved top-k corpus (labeled retrieval payload) — not the full-corpus `[:2000]` concatenation; a `retrieval.semantic_search` trace event exists with query, hit chunk ids, similarities, budget use.
- Expected: truncation assembly gone from planning; retrieval event recorded once per planning retrieval.

### TS-008: Generation call-sites for all three families

- Protects: AC-002, D9
- Risk/type: Functional / coverage
- Steps: run plan, deck, and exercise generation for a multi-lesson blueprint; per lesson and per family assert: a retrieval event exists (family + lesson_index), the model user payload contains that lesson's retrieved chunks as labeled user data, and zero-relevance lessons carry the explicit ungrounded state instead of corpus text.
- Expected: three families, per-lesson retrieval, no family silently skipped.

### TS-009: Zero-relevance behavior

- Protects: AC-004, D4
- Risk/type: Error path / honesty
- Steps: construct a corpus whose embeddings are all distant from the query (fake adapter); run planning + one generation family; assert `grounding_state='none'`, payload carries the explicit no-strongly-related state, run proceeds to success, trace event shows 0 hits.
- Expected: honest ungrounded generation; no fabricated grounding; no run failure.

### TS-010: Exclusion disclosure

- Protects: AC-002, D3
- Risk/type: Error path / observability
- Steps: mix `embedding_failed` chunks into a corpus with healthy ones; retrieve; assert failed chunks never appear in hits, `excluded_count` and reasons recorded in the event, and evidence row can render them.
- Expected: exclude-with-disclosure; no fallback injection of unranked text.

### TS-011: Blueprint citations bind to retrieved chunks

- Protects: AC-003
- Risk/type: Functional / happy path
- Steps: run planning with retrieval; inspect normalized blueprint: objective/lesson citations carry `source_id`, `chunk_position`, `text_sha256`, `excerpt`; every cited chunk id belongs to the captured planning retrieval set; no citation references an unretrieved chunk.
- Expected: cited ⊆ retrieved; citation objects complete and stable.

### TS-012: Artifact citations per family

- Protects: AC-003, D9
- Risk/type: Functional / coverage
- Steps: generate plans, decks, exercises; per artifact assert citations bind to that family's own per-lesson retrieval set; decks/exercises do not copy the plan's citation set verbatim (each has its own event to cite from).
- Expected: per-family, per-lesson citation provenance.

### TS-013: Payload citations never trusted

- Protects: AC-003 (server-authoritative)
- Risk/type: Security
- Steps: make the fake model adapter return crafted `citations` inside blueprint/artifact responses; assert normalization strips them and only server-injected citations reach stored payloads and UI models.
- Expected: model-supplied citations dropped; server-injected only.

### TS-014: Hash correctness and stability

- Protects: AC-003/AC-004
- Risk/type: Boundary / consistency
- Steps: compute `content_sha256`/`text_sha256` for known inputs and compare against expected digests; re-render/re-read artifacts and blueprints; hashes unchanged; identical text in two chunks of different sources yields identical `text_sha256` but distinct chunk identities.
- Expected: stable, content-addressed hashes.

### TS-015: Retrieved text stays inert payload (injection defense)

- Protects: Untrusted-input discipline; extends the existing adversarial suite
- Risk/type: Security
- Steps: plant prompt-injection payloads inside chunk text (fake-embedded); run planning + generation; assert retrieved text appears only inside the labeled user payload, never in system prompts, and crafted instructions do not alter output contracts (JSON shape still validated, tools unchanged).
- Expected: retrieval changes the transport, not the trust boundary.

### TS-016: F009 comparability signature

- Protects: AC-005
- Risk/type: Observability / evaluation honesty
- Steps: create evaluation entries under two retrieval modes (legacy marker vs semantic) via the deterministic harness; assert the signature includes retrieval mode and mixed-mode entries are not comparable; existing live passes render marked incomparable with the legacy mode visible.
- Expected: no silent cross-mode comparison; legacy marking visible.

### TS-017: F011 deletion completeness

- Protects: AC-006
- Risk/type: Privacy / recovery
- Steps: embed chunks for a project/workspace; delete project then workspace; assert embeddings, hashes, statuses are gone with all other source data (sweep extension), and the retained ledger stays content-free.
- Expected: no embedding remnants.

### TS-018: Quota classification

- Protects: AC-006, D6
- Risk/type: Idempotency / cost honesty
- Steps: parse and backfill many chunks; assert `model_calls` on runs and expensive-write counters are unchanged by embedding compute; embedding happens inside upload processing bounded by existing caps; no new rate-limit dimension introduced.
- Expected: no silent quota change; embedding cost visible only as processing facts.

### TS-019: API/evidence contract

- Protects: AC-002/AC-003 contract surfaces
- Risk/type: API contract
- Steps: exercise the sources listing payload (chunk list with embedding status), blueprint/artifact payload citation fields, and the events endpoint for `retrieval.semantic_search`; assert shapes match `docs/API.md` updates and authorization boundaries unchanged (owner-only writes, sample-read rules intact).
- Expected: contract tests green; no new endpoints.

### TS-020: Cited source deleted later

- Protects: Edge case (supersession/deletion honesty)
- Risk/type: Recovery / honesty
- Steps: complete a run with citations; delete the cited source; assert stored citations remain historical (filename + hash still render, UI shows 已删除 state), no dangling hard-reference breaks blueprint/artifact reads, and deletion sweep removes live chunk data.
- Expected: historical citations honest; reads stable.

### TS-021: Citation chip expand (web)

- Protects: U1/U3 (AC-003 visibility)
- Risk/type: UI interaction
- Steps: render the shared citation chip with a source-chunk citation: label `来源：文件名 · 第N段`; keyboard-activate; expanded region shows excerpt, hash prefix; standards variant renders static; collapsed/expanded states have `aria-expanded`.
- Expected: one component, two variants, keyboard operable.

### TS-022: Artifact citations and ungrounded notice (web)

- Protects: U2 (AC-003/D4 visibility)
- Risk/type: UI state
- Steps: render artifact detail for each family with `citations` present and with `grounding_state='none'`; assert chips render per lesson and 无强相关来源语料 notice appears only for none-state lessons.
- Expected: honest per-lesson states in all three family views.

### TS-023: Sources chunk expansion (web)

- Protects: U1/U5 (AC-001 visibility)
- Risk/type: UI interaction/state
- Steps: expand a source row; chunk list renders positions, text, and 未嵌入（原因） for failed chunks; healthy sources show all chunks embedded.
- Expected: full-fidelity chunk view with failure disclosure.

### TS-024: Evidence retrieval rows (web)

- Protects: U4 (AC-002 visibility)
- Risk/type: UI observability
- Steps: render evidence events including `retrieval.semantic_search`; collapsed row shows 命中 N · 排除 M · 预算 x/y 字 chips; expanded shows raw payload; label table entry renders zh-Hans label.
- Expected: progressive disclosure intact.

### TS-025: Deterministic E2E journey

- Protects: end-to-end integration (AC-002/AC-003/D9/D4)
- Risk/type: E2E / accessibility + responsive spot
- Steps: browser journey on the deterministic stack (fake adapters): upload source → confirm brief → planning completes with retrieval-backed blueprint citations visible and expandable → generate plans (at least) → per-lesson citations and one forced zero-relevance lesson notice visible → evidence tab shows retrieval rows; keyboard-only pass through citation expansion; 420px spot check.
- Expected: full journey green on fake adapters; a11y assertions pass.

### TS-026: Live retrieval evidence and full re-baseline (owner-authorized)

- Protects: AC-005, D5, ADR-0007 follow-up
- Risk/type: Live evidence
- Steps: under explicit owner authorization at delivery: run the real fastembed + bge-small-zh-v1.5 stack; execute the complete F009 live pass set (all representative units) under the new signature; judge retrieval quality per pass (cited chunks plausibly related to lesson topics); record evidence files.
- Expected: full re-baseline recorded; retrieval quality judged honestly; legacy passes marked incomparable.

### TS-027: Full regression sweep

- Protects: completed features
- Risk/type: Regression
- Steps: `uv run pytest`, `uv run ruff check src tests migrations`, `corepack pnpm web:test`, `web:lint`, `web:typecheck`, existing E2E journeys.
- Expected: all green; F009/F011/F012 surfaces unaffected except documented signature marking.

## Execution Evidence Snapshot (2026-09-03)

- TS-001..TS-019, TS-021..TS-024: GREEN — `apps/backend/tests/test_embedding.py` (7) + `tests/test_retrieval.py` (23) + `__tests__/retrieval-surfaces.test.tsx` (5) inside full suites: backend 547 passed + 4 skipped + ruff clean; web 113/113 + tsc clean + eslint 0 errors (3 pre-existing warnings). Deck/exercise injection journeys updated to the new event contract (review SF-2) and green.
- TS-020: GREEN (subset) — blueprint history immutability covered by the captured-set design and blueprint citation tests; the deleted-cited-source UI rendering is covered by component/state-matrix fixtures rather than a live deletion journey (substitute coverage; recorded).
- TS-025: GREEN — `E2E_RETRIEVAL=1` journey on the deterministic stack (fake embedding + fake model, serial worker, 35.8s): upload→parse+embed→planning citations (keyboard expansion)→per-lesson plan citations→evidence retrieval chips→sources chunk view→420px spot. Fixture constraint recorded (review SF-3).
- TS-026: NOT RUN — owner-authorized full live re-baseline under the `retrieval_mode` signature executes at delivery (Spec D5); existing live passes render incomparable by signature difference.
- TS-027: GREEN — full deterministic sweep above; deployed-stack regression executes with the delivery redeploy.

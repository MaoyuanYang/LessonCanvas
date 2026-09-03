# F014 Self Review — Semantic Source Retrieval

- Review ID: `review-f014-r1`
- Scope: full working-tree diff on `feature/F014-semantic-source-retrieval` vs `main` (272b4f7)
- Reviewed: 2026-09-03, implementation T0–T8 complete per `plan-f014-r1`; T9 (owner-authorized live re-baseline) and delivery are delivery-time steps.

## Verification summary

- Backend: `uv run pytest` — 547 passed + 4 skipped (baseline 515+4 → +32 F014 tests in `tests/test_embedding.py` + `tests/test_retrieval.py`); `uv run ruff check src tests migrations scripts` clean.
- Web: `corepack pnpm web:test` 113/113 (baseline 108 → +5 in `__tests__/retrieval-surfaces.test.tsx`); `web:typecheck` clean; `web:lint` 0 errors (3 pre-existing warnings on main).
- E2E: `E2E_RETRIEVAL=1` journey TS-025 green on the deterministic stack (fake embedding + fake model, eager tasks): upload→parse+embed→planning with expandable chunk citations (keyboard path)→per-lesson plan citations→evidence retrieval rows with 命中/预算 chips→sources chunk view→420px spot.
- Structural spot-checks in review: planning retry resumes from the checkpointed state (retrieval executes once per run, never re-bills); zero-source projects degrade to the honest ungrounded state end to end; duplicate run submissions reuse per-lesson checkpoints (unchanged F003 contract); superseded sources cannot leak into citations (citations derive from each item's captured hit list); deletion cascades remove embeddings/hashes/citations with the owning rows (TS-017).

## Findings

### SF-1 (design correction, resolved during refinement): generation was never source-grounded

`main` injects no source text into plan/deck/exercise payloads; the DRAFT spec's "replace truncation at every grounding call site" would have silently meant "no change" for generation. Surfaced to the owner as D9; resolution (all three families retrieve per lesson) is implemented and tested (TS-008/TS-012). The spec, plan, and this review agree on the corrected scope.

### SF-2 (test-contract update): injection tests assumed carried corpus text

`test_guardrails_injection` asserted injection text appears inside trace payloads. Under retrieval, lexically unrelated adversarial files are honestly excluded from payloads, so the assertion could no longer hold. The test now additionally uploads a theme-related injection document (retrieved and carried) so inertness of *carried* injection text stays proven (TS-015); the original adversarial fixtures are unchanged (checksummed dataset untouched). Deck/exercise injection journeys gained the new `retrieval.semantic_search` event kind and payload keys in their event whitelists — contract updates, not relaxations.

### SF-3 (E2E fixture constraint): uploaded source must not contain `课时分配`

With that marker in the retrieved corpus the fake planner skips its gap questions, leaving a second waivable finding (`period_warning`) that the shared `confirmedBlueprint` helper does not decide (single decision click). The journey's source fixture omits the line (comment in `retrieval-journey.spec.ts`). Backend suites cover the with-marker path explicitly.

### M-1 (residual, owner-visible): fake embedding quality is lexical, not semantic

The deterministic fake embedder ranks by hashed character-n-gram overlap. It proves ranking/budget/degradation mechanics (TS-005/006/009/010) but not real semantic quality; that judgment belongs to the TS-026 live re-baseline on the deployed stack (ADR-0007 follow-up), which requires owner authorization at delivery (Spec D5).

### M-2 (residual): HNSW index behavior at corpus scale untested

Corpora are bounded by upload caps (200 MB/day, 10 sources/project) and correctness is query-result-based, so ANN index performance was excluded by the Test Design scope. If corpora grow by orders of magnitude, revisit with load evidence.

### L-1 (environment note): deployed stack owns the shared ports

Local verification ran against `lessoncanvas_test` on the F012 deployed PostgreSQL/MinIO via env overrides (established machine pattern since F012); a stale `next dev` from a prior session was restarted fresh against the fake API instance. No repo state depends on this.

## AC → evidence

| AC | Evidence |
| --- | --- |
| AC-001 | `test_embedding.py` (adapter contract), `test_retrieval.py` write-path tests (ok/failed states, re-parse heal), migration structure test, TS-002/TS-003 |
| AC-002 | planning trace assertions (TS-007), three-family generation tests (TS-008), service-level ranking/budget/exclusion tests (TS-005/006/010), contract test (TS-019), E2E evidence rows |
| AC-003 | blueprint citation binding (TS-011), per-family artifact citations (TS-012), payload-citation stripping (TS-013), hash stability (TS-002/TS-011), stale-citation honesty (TS-020 blueprint history; artifact citations immutable per run), E2E chip expansion |
| AC-004 | ranking determinism, budget trim, zero-relevance service + integration (TS-009), exclusion disclosure (TS-010), backfill idempotency + failure isolation + healing (TS-004) |
| AC-005 | signature test (TS-016); legacy passes incomparable by construction (stored `model_config` lacks `retrieval_mode`); full live re-baseline = TS-026 at delivery (owner-authorized) |
| AC-006 | deletion completeness (TS-017), quota-classification invariants (TS-018) |
| AC-007 | documentation sync in this delivery (README, DATABASE, ARCHITECTURE, API, UX/UI, DESIGN_SYSTEM, TESTING, AGENTS unchanged — no command changes) |

## Verdict

No Critical or unfixed High findings. Implementation matches the SPEC-READY revision (decision log D1–D9) and `plan-f014-r1`; ready for REVIEW → delivery steps (owner-authorized commit/push/PR, deploy-chain verification with backfill, TS-026 live re-baseline).

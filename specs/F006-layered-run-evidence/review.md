# Review: F006 Layered Run Evidence

- Work item: [GitHub Issue #12](https://github.com/MaoyuanYang/LessonCanvas/issues/12)
- Reviewed branch: `feature/F006-layered-run-evidence` (working tree @ review time)
- Reviewed inputs: Spec @ `b43922d2cc17`, UX/UI @ `ux-ui-f006-r1` / `4bff46959bb0`, Test Design @ `test-design-f006-r1` / `e2e261591bd8`, Plan (T0–T7)
- Review date: 2026-08-31 · Reviewer: ZCode feature-dev session (YMY / Project Owner driving)

## Verification Summary

- Backend: full suite green (`uv run pytest`, exit 0; includes 20-test `tests/test_evidence.py` replacing `tests/test_trace.py`; `ruff check src tests migrations` clean; migration `f006a1c9e221` applied to dev + test DBs with downgrade path).
- Web: 47 tests green (8 new `evidence-panel.test.tsx`; all pre-existing suites unchanged and green), `eslint`/`tsc --noEmit`/`next build` clean.
- E2E (Playwright, production `next start` build): fault stack TS-020a (empty state), TS-020 (inventory/summary/expansion/narration), TS-022 (keyboard-only pass, B-001); live stack TS-021 (real DeepSeek + real Worker: token/cost/model evidence + real explanation narration). All green. Environment notes: one TS-020 stall class re-run clean after quota-orphan cleanup (F005 M-1/L-1 pattern); one strict-mode selector fix in the spec itself before passage.
- TS-023 (F003 residual, Bug branch): root cause identified and fixed — see Findings.
- TS-024 (F004 M-2 residual, Bug branch): reproduced with evidence; self-healing verified; hardening routed to F011 — see Findings.

## Spec Compliance

- AC-001..AC-015 implemented and verified: traceability maintained in `test-design.md`; every AC maps to automated or E2E evidence (AC-013 via TS-022 scripted keyboard pass incl. the B-001 close-out).
- Spec decisions honored: D1 two-layer disclosure (summary endpoint never returns prompt text; events endpoint carries payloads for owner-initiated expansion only); D2 estimated cost (write-time price-table computation, tokens persisted, `未记录` for pre-F006 rows, never zero-masked); D3 all five run kinds (discovery/planning aggregated with interview rounds in the same event stream); D4 evidence API replaces the legacy metadata-only trace endpoint; D5 read-only guarantee (invariance test TS-007; UI issues no non-GET except narration); D6 inert rendering (React text nodes, pre-wrap payloads, clipboard-only copy, no browser persistence); D7 cursor pagination (URL-safe fixed-width microsecond cursors; stable under concurrent append); D8 workspace-quota narration (QuotaCounter upsert, one active narration per run, complete text recorded as `model.evidence_narration`); D9 model identifier per model event, gaps explicit, no operator path added.

## Findings

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| H-1 | High (fixed) | TS-023 investigation root-caused the F003 "SSE early-drop" residual: during per-lesson model calls the generation/deck/exercise event streams emitted nothing on the wire; any intermediary or client with an idle read timeout shorter than the silent gap (reproduced deterministically with a 15 s probe read timeout against a live DeepSeek run) dropped the connection mid-run. The 3 s snapshot-poll + `Last-Event-ID` reconnect masked it in the UI but the drop itself remained. | Fixed in F006: SSE comment keepalives (`: keepalive`, every `STREAM_KEEPALIVE_SECONDS = 5.0` of silence) added to the three generation streams and the evidence narration stream; comment frames are ignored by EventSource, the project's browser parsers, and the replay tests. Regression test `test_generation_stream_emits_keepalive_during_idle_gaps` (comment frames never carry id/data). End-to-end verification: the identical disconnect probe that previously died in the silent gap now completes a live 6-lesson run with 0 silent ends, 4 keepalives bridging idle periods, and a clean `end` (evidence: `/tmp/f006_ts023_verify.log` transcript recorded in delivery notes; test-design Execution Evidence Snapshot updated). |
| M-1 | Medium (environment residual) | TS-020 first executions stalled twice in the shared blueprint stage and once at project-link creation: one Clerk dev-instance session degradation (FAPI PATCH failure, F004/F005 M-1 class) and one workspace project-quota exhaustion from orphaned timed-out journey projects (F005 recorded the same trap). | Re-run passed after cascade-deleting the orphaned `生成旅程` projects (17.9 s clean pass); TS-020a/TS-022/TS-021 passed unaffected. Owner-visible environment note; no product change. |
| M-2 | Medium (reproduced, routed to F011) | TS-024 reproduced F004 M-2's `StaleDataError` class exactly: deleting a project mid-run (observed at `generating` 4/6 with live model) races the Worker's in-flight lesson update (`UPDATE lesson_plan_artifacts ... 0 were matched`). Verified end state: deletion wins atomically for readers (concurrent evidence observers saw only 200 before and clean 404 after deletion — never a 5xx, never cross-content), the Worker settles via bounded Celery retry as missing_run, and no orphan rows remain. | No data-consistency product defect (matches F004's assessment). Worker-side graceful fast-fail on vanished runs (catch the stale-update race and settle immediately instead of two 180 s-delayed retries) is run-teardown hardening inside F011's deletion-verification scope — re-routed there with this reproduction evidence, pending owner confirmation at F011 refinement. |
| M-3 | Medium (scope deviation, recorded) | UX/UI UIQ-001 said DTOs would be frozen schema-first with Zod; the established codebase convention (`lib/api.ts`) is hand-written TypeScript interfaces with the shared `ApiClientError` normalizer. | Followed the codebase convention (interfaces) for consistency with F001–F005; contract still type-checked by `tsc` and behavior-tested. Recorded here rather than silently diverging; a Zod migration would be a cross-feature decision (F008+ candidate), not an F006 change. |
| L-1 | Low | The evidence narration stream does not capture provider token usage (the adapter's `stream()` yields tokens only), so narration events show `未记录` for tokens/cost. | Explicit-gap behavior is Spec-conformant (D2/D9: absence is shown, never zeroed). Capturing stream usage (`stream_options.include_usage`) changes the adapter contract and is deferred with F009's cost-evidence work. |
| L-2 | Low (hygiene) | Probe-environment lesson recorded during TS-023/TS-024: running two stacks against different databases behind one shared Redis queue lets workers swallow each other's tasks (symptom: runs stuck `queued`, `Received unregistered task` noise). Not a product defect — single-stack operation is the documented deployment shape. | Documented here for reproducibility; future multi-DB probing must use separate Redis DBs or queues. |

No Critical findings. All High findings fixed and re-verified.

## Architecture / Boundary Notes

- Evidence reads live in `modules/run_orchestration/evidence.py` as a derived projection; no new table, service, cache, or queue was introduced (AGENTS module rules respected; Run Orchestration owns progress/cost/trace observability).
- `record_trace` (write path) extended in place with usage/model parameters; all six model-event call sites (discovery, planning, three artifact graphs) pass the adapter response; tool events legitimately keep null tokens (`未记录`).
- The evidence narration sibling (`run_orchestration/narration.py` internal to `evidence.py`) duplicates ~60 lines of the discovery narration registry pattern; consolidation is deferred until a third consumer or F008 needs it (recorded, not silently diverged).
- The `TraceEvent.run_id` ORM declaration now matches the already-applied free-`run_id` migration (drift removed); migration `f006a1c9e221` is purely additive.

## Residuals

- M-1 environment class (Clerk dev-instance session instability): substitute automated coverage green regardless; re-run affected journeys when stable, per the F004/F005 pattern.
- M-2 run-teardown hardening: routed to F011 with reproduction evidence.
- L-1 narration stream token capture: deferred to F009.

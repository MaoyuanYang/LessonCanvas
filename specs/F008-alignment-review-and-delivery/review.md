# F008 Review Record

- Work item: [GitHub Issue #16](https://github.com/MaoyuanYang/LessonCanvas/issues/16)
- Spec: `specs/F008-alignment-review-and-delivery/spec.md` @ `dc301bba1a83` (`SPEC READY` PASS)
- UX/UI: `ux-ui-f008-r1` @ `6bca800ac896` (`UI READY` PASS); Test Design: `test-design-f008-r1` @ `6d7979391f92` (evidence snapshot appended)
- Branch: `feature/F008-alignment-review-and-delivery` (base `main @ 2b36d73`)
- Review date: 2026-09-01; Reviewer: ZCode feature-dev session (self review; owner approval at delivery)

## Changed Surfaces

- Backend: new module `modules/alignment_evaluation/` (`service.py` deterministic coverage/findings/status derivation; `delivery.py` manifest/ZIP/report-snapshot export lifecycle); new routers `api/alignment.py` and `api/delivery.py` (registered in `main.py`); models + migration `f008c3e7a9b1` (`alignment_overrides`, `delivery_exports`); deletion cascade extended (rows + package/report objects); `tests/conftest.py` truncate list; `tests/test_alignment.py` (17 tests).
- Web: `lib/api.ts` F008 client block; `components/alignment-panel.tsx` (status pair, coverage matrix, findings with recovery actions, override/withdraw dialogs, delivery region, history); print route `app/(authed)/projects/[projectId]/report/` + shared print stylesheet; workspace tenth tab 对齐与交付; `RunOutcomeBanners` optional `viewAlignment` link consumed by all three family panels.
- Docs: API/DATABASE/TESTING/UX/UI/DESIGN_SYSTEM updated (see Documentation Sync).

## Self-Review Findings

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| SF-1 | High (fixed) | A failed export with an unchanged manifest could never be retried: the unique identity includes failed rows, so a re-create raised IntegrityError (500) instead of rebuilding | Fixed during review: failed records are retried in place (one row per identity, status reset to building); regression test `test_failed_export_retry_reuses_record_and_recovers` added (Spec D8 honored: no duplicate record, no rebuild of ready exports) |
| SF-2 | Low | `metadata.json` inside the ZIP repeats the full manifest that also lives in `delivery_exports.manifest_json` | Accepted: the in-archive copy is the teacher-visible truth for the downloaded file; DB copy drives idempotency. No action |
| SF-3 | Low | Objective-exercise-coverage warning keys are not overridable (by design per D2 scope: overrides are for severe disputed conflicts) | Confirmed intended; recorded as a Spec deferred revisit item |
| SF-4 | Low | E2E `alignment-journeys` test timeout set to 900s because the shared planning-interview stage intermittently stalls under environment load | Recorded as M-1/M-2 residuals in the Test Design evidence snapshot; not an F008 defect |

No Critical findings. No High findings remain unfixed.

## Checklist Results

- Spec/Scope compliance: all 13 ACs satisfied with evidence (see test-design Execution Evidence Snapshot); no Scope creep; no architectural addition (no new infra product, queue, cache, model call).
- Architecture boundaries: new module owns findings/status/override/export per ARCHITECTURE module table; depends only on existing models, ownership, storage adapter, and F007 transition reads; no ownership violations.
- Data/transactions: additive migration only; idempotency DB-enforced (`uq_alignment_override_active`, `uq_delivery_export_identity`); concurrency covered (duplicate override, concurrent export create); version-switch-during-build settles failed.
- Security/privacy: all endpoints owner-authorized; cross-workspace sweep green; deletion cascade removes rows and objects; no storage-path exposure in responses; teacher content stays in workspace boundaries.
- Errors: taxonomy-compliant (REQUIREMENT with named blockers/gates, STALE_VERSION, PROVIDER_TRANSIENT for build failure, 404-without-disclosure for downloads); frontend maps each to a designed state.
- UI: matches `ux-ui-f008-r1` (status pair, findings/recovery, override dialog with required reason, gated validated export, history with truthful labels, print route, 1024px boundary, Design System reuse + one recorded shared print-pattern extension).
- Docs/code drift: API/DATABASE/TESTING/UX/UI/DESIGN_SYSTEM synchronized; README updated at delivery; AGENTS unchanged (no new durable rule adopted).

## Verification Evidence

- Backend: `uv run pytest` exit-0 (197 tests incl. 17 alignment) — see final run note below; `uv run ruff check src tests migrations` clean.
- Web: Vitest 57/57; eslint 0 errors (7 pre-existing e2e warnings unchanged); `tsc --noEmit` clean; `next build` clean.
- E2E (fault stack, production web build + eager fake-adapter backend): TS-016 validated-path journey green (alignment view → status pair → validated export → keyboard ZIP download → print report); TS-017 family-banner link green.
- Residuals: M-1 (scripted-override browser journey environment-blocked; substitute coverage green), M-2 (`next dev` client-side SyntaxError reproduced on baseline), L-1 (print paper output relies on browser engine) — all recorded in the Test Design evidence snapshot for owner visibility.

## Delivery

- Status: `READY FOR PR` (2026-09-01) — commit, push, and PR creation each await separate explicit user authorization; `Roadmap Status: REVIEW`, `DONE Status: NOT_READY`.
- PR-ready summary: F008 adds deterministic unit-level alignment review (objective coverage, gap/conflict findings with evidence and recovery actions, teacher reasoned overrides for disputed severe findings with audit and withdrawal) and version-bound labelled delivery (draft always available; validated requires all three artifact families complete with zero unresolved severe findings; byte-identical ZIP + printable web report; idempotent per version pair + label + manifest digest with failed-retry-in-place). Changed surfaces: backend `modules/alignment_evaluation/` + `api/alignment.py` + `api/delivery.py` + migration `f008c3e7a9b1` + 17 tests; web 对齐与交付 tab, override/withdraw dialogs, delivery region, print report route, family-panel alignment links. Verification: backend 197/197 exit-0 + ruff clean; web 57/57 + eslint/tsc/build clean; E2E TS-016/TS-017 green on the fault stack; residuals M-1/M-2/L-1 recorded in the Test Design evidence snapshot. Suggested title: `feat: add alignment review and delivery with overrides and labelled exports (F008 T0-T7)`.

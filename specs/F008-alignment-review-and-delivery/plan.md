# Implementation Plan: F008 Alignment Review and Delivery

## Inputs and Validated Revisions

- Spec: `specs/F008-alignment-review-and-delivery/spec.md` @ `dc301bba1a83` (`SPEC READY` PASS)
- UX/UI: `ux-ui-f008-r1` @ `6bca800ac896` (`UI READY` PASS)
- Test Design: `test-design-f008-r1` @ `6d7979391f92` (`TEST DESIGN READY` PASS)
- Base: `main @ 2b36d73`; branch `feature/F008-alignment-review-and-delivery`
- This Plan adds no requirement and changes no approved contract; deviations return to Design Change.

## Architecture Placement

- New backend module `apps/backend/src/lessoncanvas/modules/alignment_evaluation/` (owner of findings computation, status derivation, override persistence, export lifecycle) depending only on existing models, `identity_workspace` ownership, `adapters/storage`, and F007 retention reads (`run_orchestration.transition`). No dependency direction violation; no new infrastructure product, queue, cache, or model call.
- New routers `api/alignment.py` (`/projects/{id}/alignment...`) and `api/delivery.py` (`/projects/{id}/delivery/exports...`), registered in `main.py`; error mapping via existing `api/errors.py` classes.
- Migration `f008<hash>`: additive tables `alignment_overrides` (id, project_id, brief_version_id, blueprint_version_id, finding_key, reason, status recorded|withdrawn, created_by, created_at, withdrawn_at; uq (project, versions, finding_key, status recorded)) and `delivery_exports` (id, project_id, brief_version_id, blueprint_version_id, label draft|validated, manifest_json, package_object_key, report_object_key, status building|ready|failed, failure_reason, created_at, ready_at; uq (project, versions, label, manifest digest)). Audit via existing `audit_events` pattern. Deletion cascades from `projects`.
- Findings/status are pure derived reads (no persistence); recomputation function is deterministic and side-effect free (no trace/model writes).
- Export build is a synchronous, transactional creation in the POST handler (bounded artifact counts/sizes): fetch current members → verify label eligibility + manifest → build ZIP (artifact bytes + metadata.json: label, bound versions, manifest with checksums) → write package + report-snapshot JSON to artifacts bucket → persist `ready`. Any failure settles `failed` with the provider/requirement class and no partial download.
- Web: typed client additions in `lib/api.ts`; new `alignment-panel.tsx` (+ override dialog, findings list, coverage matrix, delivery region) wired as the tenth workspace tab; print report at `app/(authed)/projects/[projectId]/report/page.tsx` (query: current or export id) with a shared print stylesheet (`print.css`, app-chrome hidden); family-panel completion banners gain the passive 查看对齐情况 link.

## Task Breakdown (interleaved code + tests)

- T0 — Migration + models + ownership proof: add tables/columns, register routers stubs, deletion cascade test (TS-012 deletion half). Exit: migration applies; cascade test green.
- T1 — Alignment computation service: deterministic rule set (objective coverage, per-lesson family completeness incl. retained members, validation/pairing conflicts, severity + recovery + override-eligibility flags, status derivation, product status constant 未评估). Tests TS-001, TS-002, TS-003, TS-009. Exit: new tests green in `tests/test_alignment.py`.
- T2 — Alignment + override API: `GET /alignment`, `POST/DELETE /alignment/overrides`, requirement/stale error paths. Tests TS-004, TS-005, TS-006, TS-007, TS-008, TS-014. Exit: API tests green.
- T3 — Export/delivery service + API: manifest assembly, ZIP build with byte-identical members + metadata, report snapshot, idempotent/convergent create, download endpoints, failure settling. Tests TS-010, TS-011 (backend half), TS-013. Exit: tests green incl. concurrency duplicate create.
- T4 — Security/non-disclosure: cross-workspace and unauthenticated sweeps over all F008 endpoints (TS-012); full backend suite + ruff. Exit: suite exit-0, ruff clean.
- T5 — Web client + 对齐与交付 panel: api.ts interfaces (schema-first), panel with status pair header, coverage matrix, findings list with recovery actions, override dialog (validation + duplicate protection), delivery region + history, error mapping; component tests TS-015. Exit: Vitest green, eslint/tsc clean.
- T6 — Print report route + small-screen: report page (current/snapshot), print stylesheet, 1024px boundary, a11y semantics; component/route tests. Exit: TS-011 (web half), TS-015/016 a11y parts green.
- T7 — E2E + regression + docs sync: Playwright journey TS-016 (keyboard pass, ZIP download, print route), regression TS-017 over existing journeys, full web suite + build; documentation sync (API/DATABASE/TESTING/UX/UI/DESIGN_SYSTEM/FRONTEND/README) and Gate/Roadmap/Stage/Issue updates. Exit: all suites green; docs synchronized.

## Verification Commands

- Backend: `uv run pytest` (incl. `tests/test_alignment.py`), `uv run ruff check src tests migrations`
- Web: `corepack pnpm web:test`, `web:lint`, `web:typecheck`, `web:build`
- E2E: existing Playwright config, new F008 journey on the deterministic/fault stack (no live model required by design)

## Risks / Exit Conditions

- Risk: retention/current-member resolution subtle mismatch with F007 read model → mitigate by reusing `run_orchestration.transition` helpers rather than re-deriving (T1 pairs with F007 tests).
- Risk: ZIP memory footprint for large units → bounded by existing artifact sizes; streamed member writes; acceptable at Phase-1 scale.
- Risk: print stylesheet leakage into app chrome → scoped print rules + route isolation test (T6).
- Exit: all TS-001..TS-017 recorded PASS in the Execution Evidence Snapshot; full suites green; docs synced; review and delivery follow.

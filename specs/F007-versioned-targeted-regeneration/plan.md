# Implementation Plan: F007 Versioned Targeted Regeneration

## Inputs (validated revisions)

- Spec: `specs/F007-versioned-targeted-regeneration/spec.md` @ `fb351456a2ee` (`SPEC READY` PASS)
- UX/UI: `specs/F007-versioned-targeted-regeneration/ux-ui.md` @ `ux-ui-f007-r1` / `97597ad3c608` (`UI READY` PASS)
- Test Design: `specs/F007-versioned-targeted-regeneration/test-design.md` @ `test-design-f007-r1` / `69c9d0532f7a` (`TEST DESIGN READY` PASS)
- This Plan adds no requirement; any contract deviation returns to the Spec through Design Change.

## Module Mapping (per AGENTS Module Rules)

| Change | Owner module | Notes |
| --- | --- | --- |
| Impact matrix + preview computation | `modules/run_orchestration/impact.py` | Pure function of (old confirmed pair, new pair/drafts); reads version/draft state via discovery_planning accessors (allowed direction) |
| Transition + retention reads | `modules/run_orchestration/transition.py` | Read-time joins over prior runs' complete artifacts; no copied truth |
| Scoped run creation + coverage gates | `run_orchestration/service.py` extensions | Scope fixed at creation inside the existing idempotent creation transaction; artifact rows only for scoped lessons |
| Version/impact API | `api/versions.py` (new router: `GET /projects/{id}/impact`, `GET /projects/{id}/versions/current-transition`) | Owner-authorized reads; family starts become transition-aware in place |
| Frontend | `lib/api.ts`, `blueprint-panel.tsx` (revision seed + preview + confirm modal), family panels + shared `artifact-run.tsx` retained variant, new `version-compare-panel.tsx`, ninth tab | Reuses all established patterns |

## Data / Settings Changes

- Migration (additive): `generation_runs.scope_json TEXT NULL` — JSON integer array of affected lesson indexes (null = full scope: pre-F007 rows and ordinary first-generation starts). ORM follows; no backfill.
- No new settings (matrix is reviewed code constants; existing caps unchanged).
- Retention and verdicts are computed at read time; nothing persisted beyond `scope_json`.

## Core Algorithms

- **Impact matrix (D1)**: classify each changed field into brief-unit / blueprint-unit / blueprint-lesson / structural / unclassifiable; union scopes per family (plans affected lessons; decks/exercises follow plans transitively); widen-on-uncertainty with flag; every verdict carries its trigger field.
- **Scoped start**: on family start for a confirmed pair with no existing run, if a prior run of that family exists for an older pair, compute scope = matrix(family, old pair → new pair) and persist in `scope_json` inside the creation transaction; artifact rows only for scoped lessons; duplicate/concurrent starts converge on the existing unique run (scope never recomputed).
- **Coverage (D2)**: lesson is plan-covered iff the bound plan run has a complete artifact for it OR retention yields a complete prior plan (transition lookup). Deck/exercise starts enforce coverage over their scope.
- **Retention read**: for (project, family, lesson) find the newest complete artifact across runs of older pairs under the current transition; expose id, source versions, run id, checksum, download.

## API Flow (target)

- `GET /projects/{id}/impact` → `{brief_diff, unit_changes[], lesson_changes[{lesson_index, fields[], families[], reason}], structural{added[], removed[]}, scope{affected_lessons[], families[]}, uncertain, no_delta}`.
- `GET /projects/{id}/versions/current-transition` → `{from{brief_version, blueprint_version}, to{...}|null, intent_diff, verdicts[{lesson_index, family, verdict(affected|retained|historical), reason}], artifacts[{lesson_index, family, old{status, download}|null, new{status, download}|null}], first_version: bool}`.
- Family starts/snapshots: snapshot gains `scope_lesson_indexes: number[]|null` and `retained_artifacts: [{id, lesson_index, source_brief_version, source_blueprint_version, source_run_id, checksum, download_url}]`; prerequisite failures detail uncovered lessons.
- Confirm endpoints unchanged (conflict + checkpoint supersession already contractual).

## Tasks

### T0 — Scope persistence + impact matrix
- Migration `scope_json`; ORM; `impact.py` matrix with per-class unit tests (all D1 classes incl. unclassifiable widening and no-delta).
- Tests: TS-001 (unit level).
- Exit: matrix suite green; migration up/down proven.

### T1 — Revision seeding assertions + impact/transition API
- Verify/complete version-seeded draft behavior; `api/versions.py` with `GET /impact` (+ `GET /versions/current-transition` stub reading real transition data); stale-conflict assertions.
- Tests: TS-001 (API), TS-002, TS-009 (payload shape).
- Exit: API suite green in `tests/test_regeneration.py`.

### T2 — Transition-aware run services + retention + coverage
- Scoped creation in the three start services (single transaction, scope-once, artifact rows scoped); retention reads; snapshot extensions; generalized coverage gates.
- Tests: TS-004, TS-005, TS-007, TS-008, TS-017.
- Exit: service suite green incl. concurrency.

### T3 — Supersession integration + comparison + security + deletion
- Confirm-time supersession across families under transitions; full `current-transition` payload; authorization non-disclosure; read-only + deletion cascade checks.
- Tests: TS-003, TS-009 (full), TS-010, TS-011.
- Exit: full backend suite green; ruff clean.

### T4 — Frontend
- `lib/api.ts` types/functions; blueprint-panel revision seed + 预览影响 region + confirm-modal embedding; shared `artifact-run.tsx` retained variant; three family panels transition-aware (scoped count, retained rows, uncovered guidance); `version-compare-panel.tsx` + ninth tab.
- Tests: TS-012, TS-013 (Vitest).
- Exit: `web:test / web:lint / web:typecheck / web:build` green.

### T5 — E2E + accessibility
- `e2e/regeneration-journeys.spec.ts`: fault journey TS-014, live journey TS-015 (TQ-002 profiles), scripted keyboard/a11y pass TS-016.
- Exit: journeys green (or owner-approved residual per the established pattern); evidence recorded.

### T6 — Full verification, review, docs sync, delivery prep
- Full stack verification; `review.md`; docs sync (`API.md` F007 endpoints, `DATABASE.md` scope column, `UX.md`/`UI.md`/`DESIGN_SYSTEM.md` retained-variant note, `TESTING.md` scope, README stage); ROADMAP/STAGE/Issue sync; PR prep.
- Exit: all suites green; docs synced; delivery record ready for authorization.

## Verification Commands

```text
Backend:  cd apps/backend && uv run pytest && uv run ruff check src tests migrations
Web:      corepack pnpm web:test && corepack pnpm web:lint && corepack pnpm web:typecheck && corepack pnpm web:build
E2E:      per TQ-002 profiles (fault: fake adapter; live: real DeepSeek + real Worker)
```

## Risks / Unknowns / Exit Conditions

- Coverage-gate generalization must not weaken the F004/F005 prerequisite semantics — regression suites (unchanged) plus TS-008 guard it.
- Retention joins add reads to snapshots; bounded by lessons × prior runs per project (Phase-1 scale; revisit with evidence only).
- Live E2E cost: one scoped regeneration journey (single-family) rather than all three.
- Any contract need emerging during coding returns to the Spec (Design Change); the Plan never redefines requirements.
- Branch: `feature/F007-versioned-targeted-regeneration` (commit/push/PR each separately authorized at delivery).

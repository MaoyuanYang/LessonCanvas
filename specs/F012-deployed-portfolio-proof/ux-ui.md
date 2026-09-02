# F012 UX/UI Design — Deployed Portfolio Proof

- Artifact ID: `ux-ui-f012-r2` (r1 marked STALE by the 2026-09-02 ADR-0006 Design Change; this revision removes the sign-in flow)
- Bound Spec: `specs/F012-deployed-portfolio-proof/spec.md` @ `8c033df6a4e6` (SPEC READY, 2026-09-02)
- Product Content Language: `zh-Hans` (per `AGENTS.md` Language Policy; existing UI copy convention)
- Last Updated: 2026-09-02

## Gate Record: UI READY

- Status: `PASS` (revalidated)
- Revalidation: 2026-09-02, `YMY / Project Owner` approved via interactive session together with ADR-0006 (question-form "批准，开始实施"); revision @ `ux-ui-f012-r2` / `8ddb95ac7315`; checklist re-run 10/10 YES on the revised revision
- Prior record (STALE):
- Validation time: 2026-09-02
- Decision Authority: `YMY / Project Owner` — approved via interactive session on 2026-09-02 (question-form approval "批准 UI READY" covering U1 dedicated read-only `/sample` route reusing workspace panels, U2 landing portfolio-review section, U3 reuse of F009/F010 status regions, U4 per-panel write suppression with a persistent read-only notice), scope: `ux-ui-f012-r1`
- Checklist: 10/10 YES (Goal/Entry/Exit/Flow, page responsibilities incl. sample shell, state matrix incl. loading/stale/missing/unavailable/auth, permission/validation with N/A reasons on the formless sample path, contract/error mapping via existing taxonomy, verifiable responsive behavior, verifiable accessibility behavior, Design System reuse with explicit no-extension decision, UI acceptance linked to AC-002/AC-005/AC-007/AC-001, no Critical UI Open Question)
- Input manifest: `specs/F012-deployed-portfolio-proof/spec.md` @ `8c033df6a4e6`; `AGENTS.md` @ `f68a2ee15654`; `docs/UX.md` @ `abd0ced09605`; `docs/UI.md`; `docs/DESIGN_SYSTEM.md`; `apps/web/` route/component inventory (OBSERVED 2026-09-02, `main @ 6cf265a`)

## UI Impact Detection (all answered against the SPEC READY revision)

- Changes the user's task path/entry: YES — the public landing entry gains the product/evidence boundary and sample links; a new read-only sample path enters the authenticated app.
- Adds/changes pages, components, navigation, visible states: YES — new sample route; landing copy; service-unavailable presentation.
- Changes Loading/Empty/Error/Success/permission feedback: YES — sample loading/stale/unavailable states; deployed-instance error honesty.
- Changes responsive behavior, accessibility, copy, tokens, Design System components: PARTIAL — new compositions only; no token or primitive changes planned.
- Backend change altering frontend error mapping: NO — no new API surface; existing error taxonomy reused.

Conclusion: `UI Impact: YES`; this document is required.

## UX Decisions

| ID | Decision | Resolution | Authority / Date |
| --- | --- | --- | --- |
| U1 | Sample presentation model | A dedicated read-only route (`/sample`) owned by the app shell, rendering the existing workspace panels in read-only mode: the same 来源/访谈/简报/蓝图/生成/课件/练习/证据/版本对比/对齐与交付 information without write affordances. Reviewers do not join or copy the demo workspace; the sample is never mixed into their project list. Reuses the established "只读" copy pattern (version-compare/evidence panels). [REVISED r2] No auth middleware or redirect: access requires only the browser's guest workspace token (auto-issued); token failures show the in-app AUTH_REQUIRED state. | Owner-ratified 2026-09-02 (r1); revised with ADR-0006 approval |
| U2 | Landing entry composition | [REVISED r2, ADR-0006] The landing keeps its single-hero editorial form: the primary CTA links directly to `/projects` (no sign-in; a guest workspace token is issued automatically on first API use), and the compact "作品集评审" section below it states what the demo is (synthetic sample + bounded real generation), the product/evidence boundary sentence (Spec D7), an unconditional link to `/sample`, the repository verification link, and the honest availability sentence (no SLA, Spec D6). No marketing grid, no new visual language, no identity UI. | Owner-ratified 2026-09-02 (r1); revised with ADR-0006 approval |
| U3 | Status display | No new status surface: technical and product-validation outcomes stay in the existing evidence-panel regions (`TechnicalEvaluationRegion`, `ProductValidationRegion`) and are reachable from the sample path; the landing/review section links to them via `/sample`, not to private runs. Statuses render passed/failed/not-complete independently exactly as today. | Resolved from evidence; owner-ratified 2026-09-02 |
| U4 | Write suppression in sample view | The sample view reuses existing panels with actions disabled/hidden per panel (confirm, generate, upload, narrate, export-write) while data states (stale banners, version bindings, run outcomes) render as-is; a persistent top notice states "示例项目为只读演示，不影响任何任务状态". Degraded interactions use existing disabled-button patterns, never removed-but-implied behavior. | Resolved from evidence; owner-ratified 2026-09-02 |

## User Flow (portfolio reviewer)

- Goal: independently inspect the protected representative workflow and its evidence on the LAN deployment, or run bounded real generation.
- Entry: LAN URL → landing page → primary CTA directly opens `/projects`, or the review-section link opens `/sample` (read-only inspection); a guest workspace token is issued automatically on first API use (ADR-0006, Spec D11); no sign-in screen exists.
- Steps: landing review section → sample tabs (sources → … → evidence → versions → alignment) → observe recovery/status evidence → optionally own-project path (bounded real generation, existing journey).
- Success exit: reviewer has seen brief/blueprint/artifacts/evidence/validation statuses with version bindings; sign out.
- Cancel/Back: standard nav; sample route returns to landing via header brand link.
- Missing/invalid guest token: in-app `AUTH_REQUIRED` honest states with automatic token re-issue on next use; no redirect, no login.
- Failure recovery: API unavailable → honest error states below; no fabricated readiness.

## Page / Screen Responsibilities

| Surface | Responsibility | Data / API | Notes |
| --- | --- | --- | --- |
| `(public)` landing | Explain product, portfolio-review boundary, sample entry, availability honesty; direct entry CTA | static copy | extends existing hero; token issuance happens lazily on first API call |
| `/sample` shell | Present the designated demo project read-only with all workspace tabs and the persistent read-only notice | existing project-detail endpoints against the sample project id (resolved server-side; never from query params) | new thin shell reusing panel components; owns no business logic |
| Sample panels (reused) | Same rendering responsibilities as today (sources, discovery, brief, blueprint, generation, decks, exercises, evidence, versions, alignment) with write actions suppressed (U4) | existing APIs | evidence panel carries the F009/F010 status regions (U3) |
| Account/usage page | Unchanged (F011) — reviewers see the same limits and deletion surfaces | existing | — |

## UI State Matrix (sample path)

| State | Trigger | Visible UI | Allowed Action | Recovery/Next |
| --- | --- | --- | --- | --- |
| Loading | `/sample` entry/refresh | existing `SkeletonRows` | wait | loaded or error |
| Loaded (fresh) | sample fetch success | full read-only tabs | browse, sign out | — |
| Stale/superseded sample | version-bound stale states in seeded data | existing stale banners rendered as-is | browse | honest staleness; no refresh action (Spec D10) |
| Sample missing/seed failure | sample endpoint 404/error | `EmptyState` "示例项目暂不可用" + retry link (reload) | reload; contact owner via documented channel | operator re-seeds (documented) |
| Service unavailable | API down / stack starting | honest `Alert` error state with "服务暂不可用，请稍后重试" (no fabricated readiness) | retry | deployment healthcheck recovery |
| Auth required | guest token missing/expired | honest in-app AUTH_REQUIRED alert; web auto-issues a fresh token and refetches | automatic | returns to `/sample` |
| Provider failure evidence | seeded run outcomes include failure/recovery traces | existing run/error rendering in evidence panel | inspect | honest technical history display |

Quota-denied and validation states apply only to the self-service generation path and reuse the F011 surfaces unchanged (account usage, 429 `retry_after` strings, run admission errors).

## Contract and Error Mapping

No new API contract. Frontend behavior for existing codes on the sample path follows the established `formatError` map: `AUTH_REQUIRED` → in-app honest state with automatic guest-token re-issue; `NOT_FOUND` (sample) → sample-missing EmptyState; `PROVIDER_TRANSIENT`/network failure → honest unavailable Alert with retry; `QUOTA_EXCEEDED`/`RUN_ADMISSION` → unchanged F011 strings (self-service path only). No sensitive internal detail is shown; correlation id display follows the existing pattern.

## Permission and Validation

- `/sample` is protected exactly like `/projects` (middleware + server layout auth); every underlying request still enforces server-side authorization — the sample workspace is read via normal ownership-respecting endpoints under the hood only if the reviewer is granted a read path; otherwise the backend exposes the sample through its existing project-surface with the demo workspace's designated access rule defined in the Implementation Plan (server-enforced; never client-side).
- No forms or submits exist on the sample path; duplicate-submit, validation, and focus management concerns do not apply (N/A with reason). Existing panels keep their own handling where inputs exist but are suppressed.

## Responsive and Accessibility

- Desktop (≥1024px): full tabbed sample experience; canonical layout identical to workspace view.
- Reduced small-screen: the existing canonical reduced experience applies; sample browsing remains read-only so no desktop-gate is needed for destructive operations; navigation remains keyboard operable.
- Accessibility: reuse existing focus-visible outlines, aria labels, semantic headings; the read-only notice is a regular landmark-level text (no alert role needed); landing additions keep heading order and contrast tokens; reduced-motion respected globally as today. Verifiable behavior: keyboard-only tab navigation across landing → `/sample` tabs works; AC-010 records the deployed spot check.

## Design System Reuse

Reuses: `Button` (quiet/secondary for links), `EmptyState`, `Alert`, `SkeletonRows`, `StatusBadge`, tabs pattern, card borders/typography, semantic tokens from `app/globals.css`. No new primitives, tokens, or variants planned; the "作品集评审" landing section is composed from existing text/typography utilities. If the sample shell needs a read-only notice banner, it composes `Alert tone="info"` (existing) rather than a new component.

## UI Acceptance (linked to Spec ACs)

- Sample read-only journey renders all ten tabs with write affordances suppressed and honest stale states (AC-002, U1, U4).
- Landing review section states the boundary, sample entry, repository-verification link, and availability honestly (AC-005, AC-007; U2).
- Existing F009/F010 status regions are reachable from the sample path and remain independent (AC-005; U3).
- Unavailable/sample-missing states are honest and recoverable (AC-001 observable surface; state matrix).

## UI Open Questions

- None Critical. `NON-CRITICAL` exact sample access mechanism (dedicated read endpoint vs. demo-workspace membership) is an Implementation Plan choice bounded by server-enforced authorization (recorded above); `NON-CRITICAL` copy polish of the landing review section.

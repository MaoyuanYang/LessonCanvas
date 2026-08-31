# Design System

## Purpose and Direction

LessonCanvas needs a shared visual and interaction system because project navigation, structured decisions, long-running status, artifacts, evidence, findings, and traces recur across multiple Features. The system should make state and authority legible without collapsing into a generic admin theme.

- Visual direction: modern curriculum-design desk with editorial hierarchy, paper-like reading surfaces, clear ink/evidence contrast, and restrained annotation cues.
- Existing brand / Figma / library source: none. Accessible unstyled primitives may supply behavior but not the visual identity.
- Extension rule: reuse before extending; extend only for an explicit unmet cross-Feature need.

## Token Direction

Record semantic systems, not an exhaustive premature token dump.

| Token group | Direction / source | Status |
| --- | --- | --- |
| Typography | A highly legible interface family plus an optional editorial reading voice for document-like content; hierarchy follows task and evidence importance | `RECOMMENDED` |
| Color | Light paper/surface neutrals, strong ink text, one restrained planning/action accent, and separate semantic colors for evidence, warning, severe finding, success, stale, and focus | `CONFIRMED` |
| Spacing | A small coherent scale that supports dense review and clear grouping; no Feature invents arbitrary local rhythm | `CONFIRMED` |
| Radius | Restrained by default; interactive surfaces may be softened without making every region a floating card | `RECOMMENDED` |
| Shadow / elevation | Rare and functional for overlays or temporary layering; structure relies primarily on hierarchy, rules, and surface contrast | `CONFIRMED` |
| Breakpoints | Driven by the desktop workspace and the canonical reduced small-screen task boundary in `docs/UX.md` | `CONFIRMED` |
| Motion | Short, purposeful state transitions only; progress meaning never depends on motion and reduced-motion preference is honored | `CONFIRMED` |

Exact families, values, and breakpoint numbers are selected and visually validated with the first UI Feature rather than frozen during macro design.

### Implemented initial values (F001, 2026-08-24)

Semantic color values first implemented in `apps/web/app/globals.css` (Tailwind `@theme`), per the UX/UI refinement of F001:

| Token | Value | Use |
| --- | --- | --- |
| surface.paper | `#FBFAF7` | Reading surfaces |
| surface.alt | `#F4F2EC` | Grouping surfaces |
| border (line) | `#E3E0D8` | Rules and outlines |
| ink | `#1C1B18` | Body text |
| ink.secondary | `#55534C` | Supporting text |
| accent (action) | `#345C74` | Primary action (white text, >=4.5:1) |
| evidence | `#4A6741` | Source support markers |
| warning | `#8A6D1F` | Warnings (text-safe) |
| severe | `#A33B2E` | Rejection / severe findings |
| success | `#2F6B45` | Confirmed / ready |
| stale | `#6E6A5E` | Stale / superseded |
| focus | `#2F5D8A` | Shared focus ring |

Typography: system sans stack with zh-Hans faces for interface; system serif stack for the editorial reading voice; no web-font downloads. Breakpoint: 1024px separates the full desktop workspace from the canonical reduced small-screen experience. Contrast validation for these values is performed with the F001 accessibility pass; revisit with measured evidence.

### Shared interaction patterns

- Streaming conversation region (`apps/web/components/conversation-region.tsx`, promoted from an F001 Feature-local pattern during F002 on 2026-08-28): narrate/stop/re-ask controls plus a politely announced incremental text region over the project-scoped SSE stream. Consumers: discovery interview panel and planning interview panel. The pattern composes the foundational Button; it carries no Feature-specific copy beyond the narrate prompt passed by the caller.

## Foundational Components

| Component | Required variants / states | Accessibility rule |
| --- | --- | --- |
| Button / action | Primary, secondary, quiet, destructive, loading, disabled | Accessible name, visible focus, keyboard activation, and disabled reason outside the control |
| Input / structured form | Default, optional, required, valid, error, disabled, read-only confirmed | Persistent label, associated description/error, and error-summary focus behavior |
| Navigation item | Global, project-context, current, unavailable | Current location exposed semantically; unavailable reason does not rely on color |
| Status marker | Draft, waiting, active, partial failure, stale, superseded, technically validated, product validated/failed | Text label accompanies visual treatment; distinct statuses are not merged by color alone |
| Progress / phase tracker | Queued, active phase, completed scope, paused, failed, superseded | Announces meaningful changes without overwhelming assistive technology |
| Artifact run surfaces (shared) | Per-lesson artifact progress list and run outcome banners, promoted from F003 feature-local compositions with F004 as the recorded trigger (F004 D-DECKDS); consumed by 教案生成, 课件生成, and 练习与答案 (F005 the recorded third consumer, `noun` parameterized) | Same status language and semantics across artifact kinds; no Feature-local visual variants |
| List / table | Project, version, run, artifact, finding, and trace density modes | Correct headings, reading order, keyboard access to interactive rows, responsive alternative |
| Disclosure / evidence panel | Teacher summary, expanded sources, technical details | Programmatic expanded state, named trigger, preserved focus and reading context |
| Modal / drawer | Confirmation, destructive action, focused evidence | Focus containment and return, Escape when safe, labelled title and consequence |
| Alert / inline message | Information, warning, severe, success, permission, provider/limit | Appropriate announcement priority and persistent recovery guidance where action is required |
| Skeleton / empty state | Known structure, no project, no source, no run, no finding | Does not masquerade as real content; empty state includes a meaningful next action |

## Shared States

`docs/UX.md` owns user behavior for shared states, and `docs/API.md` owns the error taxonomy. The Design System owns reusable presentation contracts:

- Loading / Skeleton: structure and phase-progress variants with non-animated reduced-motion behavior.
- Empty: content-region and first-project variants with a reserved action location.
- Error: inline, alert, and page-level severity variants that never expose private internals.
- Success: semantic variants that keep generated, technically validated, and product-validated status visually distinct.
- Focus: a high-contrast shared treatment that survives every surface and overlay.
- Disabled: a consistent unavailable treatment paired with an external explanation slot.
- Stale / superseded: shared labels and treatments across briefs, blueprints, runs, artifacts, and evaluations.

## Usage and Governance

1. Feature development first reuses existing tokens and components.
2. A Feature may not create a separate visual language.
3. A missing capability must be demonstrated before extending the system.
4. Shared changes require impact analysis across affected Features and UI tests.
5. Every newly confirmed L3 change to Design System core requires documentation sync and an ADR.
6. Accessible behavior from a Headless primitive is preserved or replaced with equivalent verified behavior.
7. Default library themes, arbitrary utility values, and decorative school/robot motifs are not accepted substitutes for project design decisions.

## Open Items

- [RECOMMENDED] Select interface and editorial type families only after testing Simplified Chinese, English teaching content, equations/phonetics, and Office-preview fallback. Revisit in the first visual foundation Feature.
- [RECOMMENDED] Define exact semantic color values through contrast tests and representative states, not aesthetic preference alone. Revisit before `UI READY` for the first authenticated Feature.
- [RESOLVED, 2026-08-24] Headless primitive package and icon set selected for F001 (`YMY / Project Owner`): Radix UI primitives, lucide-react icons. Accessibility and bundle review happen during F001 implementation.
- [RESOLVED, 2026-08-24] Font strategy (`YMY / Project Owner`): system font stacks only, no web-font downloads; interface stack includes zh-Hans faces, editorial reading voice uses a serif stack. Revisit only with measured cross-platform readability evidence.

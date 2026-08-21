# User Interface

## Interface Direction

LessonCanvas should feel like a modern curriculum-design desk: editorial, precise, calm, and evidence-aware. It may borrow the clarity of annotated paper, lesson planning, and an editor's review table, but it must avoid classroom cartoons, ornamental school motifs, a generic SaaS dashboard, and a developer console as the default teacher experience.

## Layout Principles

- Global layout: use a stable project shell with global identity/navigation and a project-scoped working surface. Preserve orientation across discovery, planning, generation, and review.
- Content hierarchy: current teacher decision and project phase come before Agent narration. Sources, version, validation status, and available action remain legible near the content they govern.
- Density and whitespace: support serious document review with moderate information density. Use whitespace to group reasoning and evidence, not to turn each fact into an isolated oversized card.
- Responsive layout: desktop may hold related context side by side. Smaller widths collapse to one reading sequence and follow the canonical supported/deferred task boundary in `docs/UX.md`.

## Global Regions

| Region | Responsibility | Behavior |
| --- | --- | --- |
| Header | Project identity, current version/status, account and usage entry | Remains concise; never becomes a second workflow toolbar |
| Primary navigation | Project list and global account boundary | Stable across projects and clearly separate from project-context navigation |
| Project context navigation | Move among source, brief, blueprint, generation, artifacts, alignment, versions, and trace | Shows current phase and unavailable-state reason without implying every area is a separate product |
| Main work surface | Present the current teacher task and structured content | Prioritizes one decision or review responsibility at a time |
| Context / evidence region | Hold Agent questions, source support, findings, and expandable technical details | Progressive disclosure; does not compete with the teacher task by default |

## Page Patterns

### Forms

- Keep labels persistent, explain why high-impact information is requested, validate close to the input, and summarize distributed errors after submission.
- Distinguish a saved draft from an authoritative confirmation. Confirmation actions state the downstream generation or invalidation consequence.
- Source-rights and sensitive-data rules appear before upload, not only after rejection.

### Lists and Tables

- Project, run, version, artifact, and finding lists emphasize status, ownership context, recency, and next action over raw database attributes.
- Filtering and sorting are introduced only when list scale requires them. Empty states explain how to create the first meaningful item.
- Dense trace or evaluation data may use tables, but teacher-facing summaries use plain language and clear evidence links.

### Detail Views

- A detail view identifies project, immutable version, validation status, source relationship, and whether content is current, draft, stale, or superseded.
- Keep primary teacher actions near the decision they affect. Separate safe review, revision, severe override, export, and destructive deletion visually and semantically.
- Compare versions around changed intent and impacted outputs rather than presenting an undifferentiated text diff.

### Modal and Drawer

- Use a modal only for short blocking confirmation or focused input. Use a drawer or contextual region for optional evidence that should preserve the main teaching context.
- Manage focus, provide a clear accessible name, support Escape when safe, return focus to the trigger, and do not hide irreversible consequences behind generic labels.

## Feedback and UI States

`docs/UX.md` owns state behavior and recovery, while `docs/API.md` owns error classes. This document defines their interface treatment:

- Loading and progress use stable layout, the shared phase tracker, and a visual distinction between a short fetch and Agent work.
- Empty states use the shared empty pattern inside the responsible content region rather than a generic full-page illustration.
- Errors map canonical severity and recovery actions to shared inline, alert, or page-level treatments without exposing private internals.
- Success labels state the exact achieved status; a generic success color cannot collapse saved, confirmed, generated, technically validated, and product-validated meanings.
- Disabled, permission, offline, stale, and superseded treatments use shared status language and preserve the navigation/recovery behavior defined by UX.
- A severe finding may coexist with draft export, but validated-completion treatment remains blocked until correction or an explicit teacher-recorded override.

## Content and Iconography

- Language / tone: Simplified Chinese UI copy is direct, calm, specific, and non-anthropomorphic. Explain what the system knows, what it inferred, and what requires teacher authority.
- Labels and calls to action: name the result, such as "Confirm requirements" or "Resume failed lesson generation," rather than generic "Continue" or "Try again."
- Icons: use a consistent accessible icon source as support, never as the sole label. Avoid decorative education clip art and robot imagery as the primary Agent metaphor.

## Boundary with Design System

This document defines page structure and interface behavior. `docs/DESIGN_SYSTEM.md` owns semantic tokens, foundational components, shared states, and extension governance.

## Feature-level Detail

Concrete screens, interactions, and states are refined by the owning Feature after `SPEC READY`; this document does not freeze a component tree or pixel design.

# Frontend Architecture

## Scope and Platforms

- Platforms: authenticated Web application and public portfolio entry
- Primary device: desktop
- Responsive / adaptive direction: the complete creation, planning, review, and revision workflow is desktop-first. `docs/UX.md` is the canonical source for supported and deferred small-screen tasks; the frontend must not silently broaden that boundary.

## Technology

| Concern | Choice | Status | Rationale / revisit trigger |
| --- | --- | --- | --- |
| Framework | Next.js, React, TypeScript | `CONFIRMED` | Supports routing, authenticated shells, public deployment, and a rich workspace |
| Rendering | Server-capable application shell with client interaction where the workspace needs it | `RECOMMENDED` | Keep content and auth entry efficient without forcing every screen into one rendering mode; revisit per measured route need |
| Build | Next.js toolchain; exact package manager and commands not established | `CONFIRMED` | No scaffold exists, so commands must not be invented |
| UI primitives | Unstyled accessible primitives | `CONFIRMED` | Preserve interaction quality while allowing a distinct teaching-workbench visual language |
| Styling | Semantic Design Tokens and project-owned styles | `CONFIRMED` | `docs/DESIGN_SYSTEM.md` owns shared visual decisions |
| Server state | Query/cache layer around the generated API client | `RECOMMENDED` | Keep server truth distinct from local editing state; select the library during the first frontend Feature |

## Application Structure

The frontend is organized around product boundaries rather than API resources or a component catalogue:

- A public/auth boundary introduces the project and delegates identity to the managed provider.
- An authenticated project shell owns global navigation, teacher identity, usage, and route guards.
- A preparation-project workspace coordinates source, confirmed intent, generation, review, and trace experiences without duplicating backend workflow truth.
- Shared UI foundations own accessible primitives, status language, tokens, error presentation, and responsive rules.
- API access normalizes transport, authentication, errors, versions, and progress events; pages do not implement ad hoc request behavior.

Concrete directories and components are decided by the owning Features, not by this macro document.

## Routing and Navigation Integration

- Routing strategy: use framework routing with stable URLs for the project list and owner-authorized project workspace states. Deep links must resolve ownership before rendering private data.
- Route ownership / guards: public, authenticated, and workspace-owned routes are distinct. Client hiding is never authorization.
- Navigation source: product information architecture from `docs/UX.md` is authoritative; routes project it rather than creating a second navigation model.
- Not found and unauthorized behavior: do not reveal whether another user's resource exists. Present a safe not-found/permission state with a route back to the user's projects.

## State and Data Access

- Local UI state: transient disclosure, draft input, selection, and unsaved structured edits remain local to the owning interaction.
- Shared client state: keep only cross-route UI concerns that are not authoritative business facts. Do not mirror the complete project or Agent graph into an independent global store.
- Server state / cache: backend project versions, runs, artifacts, quotas, and evaluations remain server truth. Cache keys and invalidation follow owner and version boundaries and are refined with Features.
- API client and error normalization: one typed boundary attaches identity, correlation context, and version preconditions and maps API error classes to project UI states.
- Authentication state: derive identity from the managed provider and backend authorization result. Never persist credentials in application storage.
- Persistence / local storage: do not store private source text, full traces, generated content, or identity tokens in browser storage. Any safe preference persistence needs an explicit threat review.
- Streaming responses: consume SSE token streams for interview, explanation, and generation narration; render incremental text without persisting private content to browser storage; reconnect through the authoritative API rather than local replay.

## Forms and Validation

- Form handling: structured briefs, blueprints, and revision requests use explicit draft, validation, and confirmation states rather than auto-saving an ambiguous final decision.
- Client/server validation split: client validation provides timely guidance; the server revalidates ownership, version, source policy, quotas, and all business rules.
- Error display and focus behavior: errors are associated with their field or decision, summarized when distributed, announced accessibly, and focused at the first actionable problem after submission.

## Components and Styling

- Page vs shared component responsibilities: routes compose user tasks; shared components own reusable interaction and status contracts; neither owns backend business state transitions.
- Component reuse: prefer established project primitives and patterns before adding variants.
- Styling strategy: use semantic tokens and project-owned compositions. Avoid a default component-library theme, arbitrary Feature-local visual languages, and generic dashboard card grids when the content hierarchy calls for an editorial workspace.
- Design token source: `docs/DESIGN_SYSTEM.md`.

## Error, Loading and Recovery

- Error Boundary direction: separate unrecoverable shell/render failures from recoverable source, workflow, provider, quota, and artifact-step failures.
- Loading / suspense direction: preserve known structure, show meaningful phase progress, and do not use an indefinite spinner for a long-running unit job.
- API error to UI state mapping: use the canonical project-level error classes in `docs/API.md` and the user behavior/recovery rules in `docs/UX.md`; frontend code normalizes them rather than inventing a second taxonomy.
- Retry, offline and recovery: UI retry reuses the authoritative run when idempotent. Network loss does not imply job failure. On return, query current state and reconnect progress rather than start new work.

## Accessibility

- Keyboard and focus: all core flows are operable by keyboard; confirmation, dialogs, errors, disclosure, progress, and version changes manage focus intentionally.
- Semantics and labels: use native semantics where possible, label controls by purpose, expose phase/status changes, and keep visual Agent graphs understandable without color alone.
- Contrast and motion: meet WCAG 2.2 AA for core flows, preserve visible focus, and honor reduced-motion preferences.

## Testing and Build

- Component / interaction and E2E: follow the project risk map and canonical coverage in `docs/TESTING.md`; frontend tests own browser-observable interaction rather than duplicating the complete test plan here.
- Accessibility / visual checks: implement the accessibility and focused visual-regression directions owned by `docs/TESTING.md` for frontend behavior.
- Build and test commands: not yet established because no scaffold exists.

## Constraints and Revisit Triggers

- [CONFIRMED] Follow the locale and theme Scope in `docs/PRODUCT.md` and the experience behavior in `docs/UX.md`; frontend implementation may not introduce another locale or theme implicitly.
- [CONFIRMED] Small-screen use is intentionally reduced. Revisit if teacher evidence shows substantial preparation work occurs away from desktop.
- [UNKNOWN, NON_BLOCKING] The query, form, schema-validation, and styling libraries are not selected. Resolve in the first frontend Feature before `UI READY`.
- [RECOMMENDED] Code-split heavy trace visualization and document previews. Revisit after bundle measurement shows where the cost actually occurs.

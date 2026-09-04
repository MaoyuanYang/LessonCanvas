# User Experience

## User Goals

| User / role | Goal | Success signal |
| --- | --- | --- |
| Individual senior-high English teacher | Turn a unit goal and owned materials into a coherent, reviewable teaching package | Can explain the confirmed intent, see progress and evidence, revise affected work, and export the complete version |
| Individual senior-high English teacher | Recover from missing input, provider failure, or an upstream change without losing unrelated work | Understands what happened, what remains valid, and the next safe action |
| Portfolio reviewer | Inspect how the Agent system reasoned, used sources and tools, evaluated quality, and recovered | Can expand a representative run and connect the technical evidence to the user outcome |

## Primary User Flows

### Prepare and Validate a Unit

```text
Sign in and enter project list
-> create a unit-preparation project and add allowed sources
-> answer Agent questions and inspect the structured requirements brief
-> confirm the brief
-> inspect and confirm the unit blueprint
-> start complete-unit generation and leave or monitor progress
-> review artifacts, alignment findings, and supporting evidence
-> revise, document an override, or export the selected version
```

- Failure path: missing or rejected material returns the teacher to a specific source or question. Partial generation preserves successful work and offers a scoped resume action. Provider or quota failure is named rather than presented as a generic error.
- Interruption / return: the job continues independently of the browser when allowed. Returning opens the authoritative current version and reconnects to its progress; it never starts a replacement run implicitly.
- Permission boundary: an unauthorized or deleted project is not disclosed. The teacher returns to their own project list with a safe explanation.

### Revise Confirmed Intent

```text
Open a confirmed project version
-> edit the structured brief or blueprint
-> inspect the predicted impact
-> confirm a new immutable version
-> old active run stops at a safe checkpoint
-> regenerate only affected work
-> compare and select the current result
```

- Failure path: a stale browser edit cannot overwrite a newer version; the teacher must review the conflict before continuing.
- Interruption / return: drafts remain visibly distinct from confirmed versions, and existing validated output remains available until a replacement is ready.
- Permission boundary: only the workspace owner can confirm intent, start generation, override findings, export private files, or delete the project.

### Inspect Technical Evidence

```text
Open a run or artifact
-> view teacher-readable sources, decisions, status, and findings
-> expand technical details
-> inspect specialist steps, tools, latency, cost, retries, and evaluations
-> return to the teaching decision without losing context
```

- Failure path: unavailable low-level details do not hide the user-visible run state; the UI explains the telemetry gap and correlation reference.
- Interruption / return: expanded technical views are optional and do not change project state.
- Permission boundary: a teacher sees only traces for their own project. Portfolio sample runs use synthetic data; private teacher runs are never republished as portfolio samples under the current privacy decision.

### Review Alignment and Deliver

```text
Open the current confirmed version in the unit workspace
-> inspect objective coverage and per-lesson completeness across all artifact families
-> inspect severity-grouped findings with evidence and recovery actions
-> correct intent, regenerate targeted work, or record a reasoned override for a disputed finding
-> watch the technical package status recalculate; product validation stays a separate not-evaluated status
-> export the labelled draft package at any time, or deliver the validated package once severe findings are resolved
-> print the alignment report (current state or an export-time snapshot)
```

- Failure path: unresolved severe findings keep the validated delivery blocked with the blockers named; a build failure or a version switch during export settles the export failed instead of delivering a partial or mixed package.
- Interruption / return: findings and statuses recompute deterministically from recorded state; overrides and export history stay bound to their versions and are never presented as current after a newer version.
- Permission boundary: only the workspace owner sees alignment results, records overrides, exports, or downloads the package.

### Manage Teaching Preferences

```text
Confirm a brief or complete a run
-> Agent proposes preference candidates with evidence
-> teacher confirms, edits, or rejects each proposal
-> confirmed records apply as visible subordinate context to future work
```

- Failure path: rejected proposals never apply and are not re-proposed identically; a conflict with confirmed intent surfaces with the confirmed version winning.
- Interruption / return: proposals persist as pending until addressed or dismissed.
- Permission boundary: only the workspace owner can confirm, edit, or delete memory records.

## Information Architecture

| Area | Responsibility | Primary users | Entry / relation |
| --- | --- | --- | --- |
| Public entry and sign-in | Explain the project boundary and establish identity | Teacher, portfolio reviewer | Public entry |
| Project list | Find, create, resume, or delete preparation projects | Teacher | Authenticated home |
| New preparation flow | Establish the unit context and source readiness | Teacher | From project list |
| Unit workspace | Hold the current source, intent, generation, review, and version context | Teacher | From a project |
| Evidence layer | Explain sources, specialist activity, evaluations, and recovery for the current context | Teacher, portfolio reviewer | Contextual within the unit workspace |
| Account and usage | Show identity, private-data controls, quotas, and deletion | Teacher | Authenticated global navigation |
| Memory and preferences | Manage teacher-confirmed workspace memory and proposals | Teacher | Account / workspace area |

## Page / Screen Map

| Screen | User task | Key information / action | Related flow |
| --- | --- | --- | --- |
| Public entry | Understand the demo and enter directly (no login, ADR-0006) | Product boundary, portfolio-review section (synthetic sample entry, repository-verification link, availability honesty), privacy warning, direct-entry CTA | All flows |
| Synthetic sample view (`/sample`) | Inspect a complete read-only synthetic unit (portfolio reviewers) | All unit-workspace information with write actions suppressed, read-only notice, sample-missing/unavailable states, independent technical/product status regions; access needs only the browser's guest workspace token | Inspect evidence |
| Project list | Resume or start work | Project identity, current phase, validation status, last activity, create action | Prepare a unit |
| New preparation | Supply unit context and allowed evidence | Source readiness, rights acknowledgement, output language, missing-input guidance | Prepare a unit |
| Unit workspace | Move through discovery, planning, generation, review, and revision | Current immutable version, confirmation state, phase progress, artifacts, findings, actions | Prepare and revise |
| Run evidence view | Understand one run without leaving its teaching context | Sources, decisions, specialist steps, tools, metrics, evaluations, retries | Inspect evidence |
| Account and usage | Control identity-linked data and resource use | Quotas, privacy and deletion actions | Support and safety |
| Memory management | Manage teacher-confirmed preferences and proposals | Proposal list, confirm/edit/delete actions, applied-context indicator | Manage preferences |

Feature refinement may split or combine these responsibilities, but it must preserve the information architecture and flow. This map does not define a component tree.

## Navigation

- Primary navigation: project list and account/usage are global. A selected project opens a stable project-scoped workspace rather than becoming another top-level application.
- Secondary / contextual navigation: source, brief, blueprint, generation, artifacts, alignment, versions, and trace are contextual views of the selected unit and current version.
- Back, cancel and deep-link behavior: deep links preserve project and version identity; back never discards a confirmed decision; cancel explains whether a draft, active run, or completed result is affected.

## Interaction Principles

- Put teacher decisions in structured, confirmable state; use chat for questions and explanation, not as the only record.
- Reveal technical depth progressively. The default view answers "what happened and what can I do" before "which node and token cost produced it."
- Separate current, draft, stale, superseded, validated, and product-validation states in language as well as appearance.
- Grounding honesty (F014): retrieved, per-item citations are traceable to the exact source chunk (expandable filename/position/excerpt/hash chips); zero-relevance lessons show an explicit 无强相关来源语料 notice at the artifact; excluded/unembedded chunks are disclosed (未嵌入 with reason in the sources view, 排除 counts on evidence retrieval rows) — never silent omission or silent fallback.
- Tool-use honesty (F015): when a specialist calls tools itself, every round is visible in the evidence stream with teacher-readable chips (第 N 轮 · 工具名 / 返回 M 条 / 拒绝：原因 / 回退：原因); refusals and the deterministic fallback are shown as recorded states, never hidden, and a run that answers without tool use shows no fabricated tool activity.
- Stage and review honesty (F016): design, review, and revise stages render as their own statuses and event rows with per-stage cost; review findings keep their severity and round (第 1 轮 / 修订后第 2 轮), a clean re-review after revise is disclosed as 修订后评审通过 with the empty findings state, failed-after-revise names the review stage, and source analyses show their own state, cost line, and gated retry — no stage is ever reported as another.
- Preserve valid work. A local error or revision does not erase unrelated successful artifacts.
- Show source and version context at the moment a teacher confirms or overrides a significant finding.
- Dangerous actions: project/account deletion, supersession, and severe-finding override require explicit consequence text and confirmation; use undo only when the backend semantics truly support it.
- Long-running actions: acknowledge quickly, show named phases and completed scope, allow safe departure, and provide a precise resume path.
- Streaming responses: streamed Agent text can be stopped; stopping narration never silently cancels the underlying run, and the authoritative content remains the complete trace record.

## State and Feedback Principles

| State | Project-level behavior |
| --- | --- |
| Loading | Preserve known page structure and distinguish short data fetches from long Agent work |
| Empty | Explain why the area is empty and offer the one next action that advances the workflow |
| Error | Name the failure class, preserve valid work, link a correlation/run reference, and offer only safe recovery actions |
| Success | State what became authoritative, what remains draft or unvalidated, and the next optional action |
| Disabled | Explain the unmet requirement, permission, stale version, active transition, or quota reason |
| Permission denied | Do not reveal another resource; return to the user's project boundary |
| Offline / network failure | Explain that the remote job may continue, reconnect to authoritative state, and never create a duplicate implicitly |
| Waiting for teacher | Keep the unanswered gap and effect of the decision visible |
| Queued / generating | Show phase, completed scope, cost/limit context where useful, and safe-leave guidance |
| Partial failure | Identify the failed scope and preserved results and offer a checkpoint-aware resume action |
| Stale / superseded | Identify the newer version and prevent stale output from appearing current |
| Provider / quota failure | Distinguish outage, timeout, rate limit, and user quota with an appropriate retry or wait path |
| Streaming / partial response | Present incremental Agent text with stable completion semantics; stop is available and does not cancel underlying work unless requested |
| Proposed memory pending | Show the proposal with evidence and accept/edit/reject actions; it never applies before confirmation |

## Accessibility

- Core-flow target: WCAG 2.2 AA, including contrast and non-color communication as well as the interaction requirements below.
- Keyboard path: every confirmation, disclosure, revision, finding, version choice, recovery, download, and deletion action is keyboard reachable.
- Focus management: move focus to validation summaries, changed workflow phases, opened dialogs, and the restored trigger after close; do not move focus for passive progress noise.
- Screen reader / semantics: expose page landmarks, current phase, progress, status, source relationships, and evaluation outcomes with text semantics independent of visual diagrams.
- Labels and errors: use specific action language and associate errors with affected controls and recovery guidance.
- Contrast: text, controls, focus, status, findings, and evidence relationships meet AA contrast and do not depend on color alone.
- Reduced motion: progress and transition meaning cannot depend on animation; honor user motion preferences.
- Streaming announcements: present streamed text in throttled semantic batches so assistive technology receives meaningful chunks rather than per-token noise.

## Responsive UX

Desktop presents conversation, structured decisions, artifacts, and evidence with enough simultaneous context for review. At smaller widths, preserve task status, alignment summary, failure/recovery information, and downloads; defer complex source comparison, structured editing, and trace exploration with a clear desktop-required message. Do not simulate a complete mobile preparation product.

## Internationalization and Theme

- Locale / RTL / time / currency: Phase-1 UI is Simplified Chinese. Generated teaching content may be Chinese, English, or bilingual. Store time consistently and present it in the user's context; no RTL or currency behavior is required.
- Light / dark / system theme: one light visual system only. Dark Mode is out of scope.

## Open UX Questions

- [UNKNOWN, NON_BLOCKING] The exact boundary between compact-desktop and reduced small-screen tasks is not selected. Resolve during the authenticated workspace shell Feature through content and keyboard testing.
- [UNKNOWN, NON_BLOCKING] The participating teacher has not yet validated the proposed project-centered information architecture. Validate the clickable or implemented flow before the first UI Feature reaches `UI READY`.

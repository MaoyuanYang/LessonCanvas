# Retain Complete Run Traces Inside User-Owned Workspaces

- Status: `Accepted`
- Date: 2026-08-21
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: None

## Context

Complete prompts, source excerpts, model outputs, tool calls, specialist transitions, costs, latency, evaluations, retries, and failures provide strong portfolio evidence and support debugging. They can also contain private teacher material and copyrighted excerpts. LessonCanvas has multiple personal teacher accounts and explicitly excludes identifiable student data.

A redacted-only telemetry policy was proposed and rejected. Permanent platform ownership of traces would conflict with teacher ownership and deletion.

## Decision

Persist a complete trace for every run, scoped to the owning teacher workspace. A trace is part of the teacher's project data, follows the same authorization boundary as sources and artifacts, and is deleted with the project or account.

Traces are never reused across users and are never used for model training. Operational troubleshooting access must be disclosed, controlled, and auditable. Source data remains untrusted and cannot use trace or tool execution to bypass workspace policy. Public-demo quotas and retention costs are monitored as operational risks.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Redacted structural telemetry for user runs, full synthetic evaluation traces only | Lower privacy exposure and simpler operations | Rejected because the Project Owner prioritized complete per-run explainability |
| Permanent centralized platform trace corpus | Easiest cross-run analysis and debugging | Violates deletion, ownership, material-rights, and isolation boundaries |
| No trace persistence | Lowest content exposure | Cannot meet observability, recovery, evaluation, or portfolio evidence requirements |
| Complete traces only in development | Safer public deployment | Fails the confirmed requirement for inspectable public-demo runs |

## Reasoning

User-scoped complete traces satisfy the chosen portfolio evidence goal while preserving a clear ownership and deletion rule. The decision accepts higher storage, security, and operational cost rather than hiding it behind a claim that telemetry is harmless.

## Consequences

- Positive: every user-visible outcome can be tied to sources, workflow decisions, tools, versions, cost, and evaluation.
- Positive: recovery and regression evidence can inspect real run state.
- Negative / tradeoff: private-content exposure and storage cost are higher than with redacted telemetry.
- Negative / tradeoff: project/account deletion and operator access require cross-system verification and audit.
- Follow-up: revisit if any selected provider cannot guarantee required isolation, deletion, access control, or regional operation.

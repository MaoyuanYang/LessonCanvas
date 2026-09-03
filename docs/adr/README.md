# Architecture Decision Records

ADRs record why significant architecture or technology decisions were made. They are not used for routine implementation details.

## Naming

```text
NNNN-short-decision-title.md
```

## Status

`Proposed | Accepted | Superseded | Deprecated`

A confirmed L3 decision must have an Accepted ADR before implementation relies on it. A later change updates or supersedes the decision rather than silently rewriting history.

## Index

| ADR | Decision | Status | Date |
| --- | --- | --- | --- |
| `0001-portfolio-first-multi-agent-architecture.md` | Keep explicitly orchestrated Multi-Agent as a portfolio requirement and separate technical from product validation | `Accepted` | 2026-08-21 |
| `0002-stateful-agent-and-async-execution.md` | Adopt the Phase-1 application, data, API, identity, model, and durable Agent runtime architecture | `Accepted` | 2026-08-21 |
| `0003-user-owned-complete-run-traces.md` | Retain complete traces inside the owning, deletable teacher workspace | `Accepted` | 2026-08-21 |
| `0004-mcp-tool-and-source-protocol.md` | Adopt MCP for external source consumption and internal tool definitions without exposing a public server | `Accepted` | 2026-08-23 |
| `0005-workspace-scoped-teacher-memory.md` | Persist teacher memory only as workspace-scoped, teacher-confirmed, subordinate context | `Accepted` | 2026-08-23 |
| `0006-remove-managed-identity-for-mvp.md` | Remove Clerk for the MVP; application-issued anonymous workspace tokens without login | `Accepted` | 2026-09-02 |
| `0007-local-in-process-embedding-adapter.md` | Use a local in-process embedding model (fastembed + bge-small-zh-v1.5) behind a thin adapter for semantic source retrieval | `Accepted` | 2026-09-03 |

## When to Create an ADR

Create an ADR for significant module boundaries, technology choices, Source of Truth, messaging, cache, authentication, database strategy, frontend architecture, global navigation, Design System core, API style, trace ownership, or consistency-model decisions.

Do not create one for ordinary functions, DTOs, Feature-local components, endpoint payload details, or visual spacing.

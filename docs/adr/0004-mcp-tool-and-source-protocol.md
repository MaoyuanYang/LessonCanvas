# Adopt MCP for Source Consumption and Tool Definitions

- Status: `Accepted`
- Date: 2026-08-23
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: None

## Context

LessonCanvas integrates controlled official curriculum sources and a growing set of internal tools (retrieval, document generation, validation). The project is also a portfolio for Agent application development, where standardized tool integration is a recognized capability signal; ADR-0001 already established that portfolio coverage is a legitimate justification when recorded honestly. Without a shared protocol, tool definitions risk fragmenting between workflow code and integration code, and official-source access remains ad hoc.

At the same time, exposing any new public protocol surface to a multi-account public demo increases security and abuse risk, and project rules forbid adding frameworks without evidence and impact analysis.

## Decision

Adopt MCP as the project's tool and controlled-source protocol boundary:

- Consume controlled official sources through MCP servers. Sources and Grounding operates the MCP clients and remains the owner of source lifecycle and citation evidence.
- Register internal retrieval, document-generation, and validation tools with MCP-compatible definitions so the LangGraph tool layer and integration code consume one tool schema source.
- Do not expose a public MCP server in Phase 1. Authorization, quotas, and workspace isolation remain application-owned; MCP does not bypass them.
- Treat MCP server content, tool metadata, and schemas as untrusted input under the existing injection and policy rules.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Proprietary internal tool layer only | Fewest moving parts | Fragments tool definitions; weaker standardization and portfolio evidence |
| Expose a read-only evidence MCP server | Strong external reviewer integration story | Adds public attack surface and security verification load before evidence justifies it |
| Consume external MCP only | Minimal internal change | Misses the tool-definition standardization benefit |
| Defer MCP entirely | Less Phase-1 surface | Leaves a confirmed portfolio coverage gap open |

## Reasoning

Consumption plus internal registration demonstrates real standardized protocol usage while keeping every security boundary in application code. It adds portfolio-differentiating capability without a second workflow authority, a new data store, or a public attack surface.

## Consequences

- Positive: portable tool definitions, standards-based official-source integration, and inspectable protocol adoption for reviewers.
- Positive: one tool schema source shared by workflow and integration code.
- Negative / tradeoff: dependency on the MCP ecosystem and its LangGraph integration.
- Negative / tradeoff: additional untrusted-input surface in server metadata and tool descriptions.
- Follow-up: revisit exposing a read-only evidence MCP server only when reviewer need and a completed security review justify it; cover MCP-derived data in F011 injection cases.

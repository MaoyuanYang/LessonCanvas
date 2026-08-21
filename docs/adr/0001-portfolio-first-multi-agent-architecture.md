# Adopt a Portfolio-First, Explicitly Orchestrated Multi-Agent Architecture

- Status: `Accepted`
- Date: 2026-08-21
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: None

## Context

LessonCanvas is primarily a job-search portfolio for Agent application development. A real teacher problem supplies credible constraints, but Phase-1 technical success and teacher product validation are intentionally separate. Multi-Agent breadth is a required portfolio signal even if a simpler baseline is not proven inferior.

At the same time, unconstrained Agent-to-Agent conversation would make the system harder to evaluate, recover, secure, and explain. The complete-unit scope also requires human confirmation and deterministic ownership of teaching intent.

## Decision

Phase 1 will use specialized Agents coordinated by an explicit workflow. A specialist exists only around a named responsibility, context, tool, or evaluation concern. Confirmed requirements and unit-blueprint versions constrain all specialists. Human confirmation gates precede expensive full-unit generation.

Multi-Agent remains in Phase 1 even if an ablation does not prove better quality or cost than a single Agent. The project will describe this honestly as a portfolio coverage decision, not an evidence-backed claim that Multi-Agent is the best production architecture.

Technical Phase-1 success and product validation are separate statuses. A technically complete portfolio may coexist with failed teacher validation, but it may not claim teacher usability.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Single Agent with tools | Smaller state and evaluation surface | Does not meet the confirmed portfolio coverage objective |
| Autonomous peer-Agent group | Visually demonstrates autonomy and delegation | Poor reproducibility, unclear authority, higher cost, and difficult failure recovery |
| Product-first architecture selected only by teacher metrics | Stronger production discipline | Conflicts with the confirmed job-search priority for Phase 1 |
| Treat teacher quality as a hard technical completion gate | One simple release status | Hides the approved distinction between engineering evidence and product validation |

## Reasoning

Explicit orchestration preserves the requested technical breadth while keeping state, authority, traces, and failure behavior inspectable. Separate success statuses prevent the portfolio goal from turning failed teacher evidence into a misleading product claim.

## Consequences

- Positive: the project visibly covers specialist orchestration, human-in-the-loop control, tracing, evaluation, and recovery.
- Positive: teacher intent remains a stable workflow input instead of emerging from Agent negotiation.
- Negative / tradeoff: Phase 1 carries complexity that may not be production-optimal or empirically superior.
- Negative / tradeoff: documentation and interviews must distinguish technical completion from product validation.
- Follow-up: reassess Multi-Agent roles, cost, and necessity before positioning LessonCanvas as a production teacher product.

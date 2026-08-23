# Persist Teacher Memory Only as Workspace-Scoped, Teacher-Confirmed, Subordinate Context

- Status: `Accepted`
- Date: 2026-08-23
- Owners: `YMY / Project Owner`
- Supersedes / Superseded by: None

## Context

Teachers prepare repeatedly, and stable preferences recur: output language tendencies, exercise formats, unit pacing habits, recurring assessment styles. Without memory, every unit starts from zero and teachers re-explain their style. With naive personalization, LessonCanvas would violate its confirmed privacy and authority model: user-owned isolated data (ADR-0003), teacher-confirmed intent as the only Source of Truth for teaching intent, and no cross-user reuse or training use.

Implicit automatic extraction additionally creates contamination and self-injection risk: poisoned or mistaken memory could silently steer later runs.

## Decision

Introduce teacher memory under strict constraints:

- Memory is workspace-scoped. Records live inside the owning teacher workspace, follow its authorization, and are deleted with the project or account.
- Memory forms by Agent proposal plus explicit teacher confirmation. The Agent may propose candidates derived from confirmed briefs, blueprints, and completed runs; nothing persists without confirmation; every record is viewable, editable, and deletable by the owner.
- Memory is subordinate context. It may personalize future discovery and generation but can never override, rewrite, or invalidate a confirmed brief or blueprint version. Conflicts surface to the teacher instead of being resolved silently.
- Memory content is untrusted input when re-injected into prompts and is covered by injection defenses.
- Memory is never shared across users and never used for training.

## Alternatives

| Alternative | Benefits | Costs / reason not chosen |
| --- | --- | --- |
| Implicit auto-extraction | Feels more intelligent; no confirmation friction | Contamination and self-injection risk, weak auditability, conflicts with teacher authority |
| Fully manual preference list | Simplest and safest | Provides no Agent capability evidence and weak portfolio value |
| Cross-user personalization model | Stronger recommendation signal | Violates confirmed isolation, deletion, and no-training rules |

## Reasoning

Proposal plus confirmation keeps personalization useful while preserving the two pillars of the project: teacher authority over intent and user-owned, deletable data. It also turns memory governance itself into portfolio evidence, which most Agent demos omit.

## Consequences

- Positive: faster repeat preparation and visible teacher control over what is remembered.
- Positive: demonstrates governed memory — proposal, confirmation, application, audit, and deletion.
- Negative / tradeoff: a new data category with UI, deletion, and injection surface.
- Negative / tradeoff: applied memory can bias generation and complicate evaluation comparability.
- Follow-up: F009 must pin or empty memory state for comparable technical evaluation; revisit implicit extraction only if confirmation burden proves excessive and contamination defenses are demonstrated.

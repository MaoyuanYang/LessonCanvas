# F011: Public Multi-Account Guardrails

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Verify and harden the complete application so multiple individual teachers can use the public demo without cross-account disclosure, uncontrolled model cost, unsafe source behavior, unauthorized files, or undeletable private traces.

## Business Value

Public multi-account use becomes defensible engineering evidence rather than an unsafe demo. Teachers receive explicit privacy, quota, denial, deletion, and recovery behavior across every completed resource.

## User Story

As an individual teacher, I want my sources, intent, runs, traces, evaluations, and files isolated and controllable, so that I can use the demo without exposing my work or incurring ambiguous limits.

## Scope

- Verify managed sign-in and application-owned authorization across every project, source, intent version, run, trace, finding, evaluation, artifact, export, and download.
- Enforce visible per-user quotas, request rates, concurrent work limits, and complete-unit generation limits before expensive operations.
- Exercise malicious document and prompt-injection boundaries so source content cannot grant tools, change policy, or cross workspaces.
- Validate controlled file type/size behavior, private object access, credential handling, and dependency security.
- Disclose and audit operator troubleshooting access without creating a shared content corpus.
- Delete project/account sources, vectors, versions, runs, complete traces, artifacts, exports, and owned records across systems, with visible progress and repair when cleanup is incomplete.
- Verify non-disclosing permission, limit, provider, and deletion failure UX, including the reduced small-screen boundary.

## Out of Scope

- Enterprise compliance certification, school tenancy, RBAC administration, SSO, collaboration, or support-ticket operations.
- Anonymous unrestricted model use or user billing/payment.
- Replacing managed provider security responsibilities with application-owned password handling.
- Treating this late Feature as permission to defer basic ownership, input safety, or accessibility from earlier Features.

## Main Flow

1. A verified teacher uses every completed project capability within visible ownership and usage limits.
2. The system rejects cross-owner, over-limit, unsafe-source, unauthorized-download, and injection attempts without leaking content.
3. Authorized operational access is disclosed and audited.
4. The teacher deletes a project or account and can observe completion or a safe recovery path across all owned systems.

## Core Business Rules

- Managed identity proves who the caller is; LessonCanvas ownership records decide what they may access.
- Authorization applies at every API, Worker, trace, evaluation, object, and export boundary; a client-side hidden control is never enforcement.
- PostgreSQL is authoritative for quota and ownership decisions; gateway/provider limits are defense in depth.
- Source data cannot override system policy, tool permission, source scope, confirmation, or validation gates.
- Complete traces and private objects have the same owner and deletion boundary as the project.
- Permission denial does not reveal that another user's resource exists.
- Account/project deletion is not complete while owned private content remains in any governed store.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Workspace ownership | Authorizes every private resource | Identity and Workspace in PostgreSQL |
| Quota / concurrency decision | Controls expensive public-demo use | Identity and Workspace in PostgreSQL |
| Security audit event | Evidence for sensitive access and action | Governed audit boundary without a second content corpus |
| Deletion operation | Coordinates removal and recovery across stores | Identity and Workspace / owning modules |
| Untrusted-source decision | Rejects or constrains unsafe content | Sources and Grounding plus system policy |

## Major API / Integration Impact

- Every existing application and Worker contract gains system-wide adversarial ownership, quota, injection, object, audit, and deletion evidence.
- Managed identity, PostgreSQL, Redis/Celery, object storage, model provider, and official-source boundaries participate without becoming competing authorization truth.
- Exact limits, audit retention, malware/tooling choices, and provider deletion mechanics wait for refinement.

## UI Impact

- UI involved: `YES`
- Affected screens: sign-in, project list/workspace, source states, progress, evidence, account/usage, permission, quota, provider, and deletion experiences
- Primary user flow: use protected workflow -> understand limit/denial -> recover safely -> inspect privacy/usage -> delete project/account
- Major UI states: verification required, permission denied/not found, quota/rate/concurrency limit, source rejected, injection blocked, provider outage, deletion pending/partial/failed/complete, operator access disclosure

## Dependencies

- Feature dependencies: `F009`, which transitively supplies every core resource, complete trace, evaluation, export, and failure path for system-wide verification
- External dependencies: selected identity, model, object-storage, cloud, security-scanning, and dependency-audit capabilities must meet documented isolation/deletion constraints

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given two teacher accounts, when either attempts every direct and indirect access path to the other's resources, then no private content, metadata, signed object, trace, or resource existence is disclosed.
- [ ] Given duplicate, excessive, concurrent, or over-quota requests, when they reach the application, then authoritative limits prevent uncontrolled model work and the owner sees an accurate recovery path.
- [ ] Given an adversarial source attempts to change policy, invoke unauthorized tools, or exfiltrate another workspace, when processed, then the attempt is contained and auditable.
- [ ] Given project or account deletion, when cleanup completes, then all governed owned content and complete traces are removed; partial cleanup remains visible and repairable until complete.

## Risks and Assumptions

- [CONFIRMED] Public demo access requires verified login and per-user cost controls.
- [CONFIRMED] Full traces increase security and deletion risk but remain required and user-owned.
- [RECOMMENDED] Use managed-service security controls as defense in depth while keeping application authorization and quota truth explicit. Revisit only if provider constraints cannot be independently verified.
- [UNKNOWN, NON_BLOCKING] Exact public limits, non-content audit retention, and provider deletion guarantees are not selected. Resolve during Feature refinement before public deployment.

## Open Questions

- [ ] Which quotas, request rates, concurrency limits, and reset behavior make the public demo useful and bounded?
- [ ] What operator access is strictly necessary, how is consent/disclosure shown, and what audit evidence remains after content deletion?
- [ ] Which file scanning and prompt/document injection scenarios are required for release evidence?
- [ ] How are failed cross-system deletions reconciled without retaining a second private-content copy?
- [ ] Which managed providers satisfy identity, object, model, and deletion requirements in the deployment region?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

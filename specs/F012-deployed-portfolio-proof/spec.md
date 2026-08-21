# F012: Deployed Portfolio Proof

- Spec Status: `DRAFT`
- Roadmap Status: `DRAFT`
- Priority: `P0`
- Owner: Unassigned until Feature development starts
- Last Updated: 2026-08-21

> This is a macro-level DRAFT created during `coding-start`. It is not `SPEC READY`, does not authorize Coding, and must be refined by `feature-dev`.

## Goal

Make the complete protected LessonCanvas workflow and its technical evidence independently inspectable in a real public cloud environment using safe synthetic portfolio material.

## Business Value

The portfolio demonstrates operational reality: a reviewer can run the core journey, inspect evidence, observe recovery and validation status, and compare the deployment claim with reproducible project verification.

## User Story

As a portfolio reviewer, I want to access a protected live demonstration and its reproducible evidence, so that I can evaluate the Agent application beyond screenshots, code descriptions, or a prerecorded happy path.

## Scope

- Deploy the confirmed Next.js Web, FastAPI application, Celery Worker/Redis transport, PostgreSQL/pgvector, private object storage, managed identity, and single model-adapter boundaries.
- Provide a public project entry and verified authenticated experience protected by `F011` guardrails.
- Offer synthetic sample units/runs and allow bounded reviewer-generated work without republishing private teacher traces.
- Demonstrate the complete brief, blueprint, all-artifact, evidence, revision, alignment, export, and recovery journey in the deployed environment.
- Record real Start, Build, Test, migration, deployment, smoke, rollback/recovery, and operational evidence once tooling exists and synchronize project documents.
- Verify core WCAG 2.2 AA behavior, desktop and reduced small-screen experience, authorized delivery, provider-failure presentation, and safe return to long-running work.
- Display technical Phase-1 status and product validation as independent passed, failed, or not-complete outcomes.

## Out of Scope

- Multi-region, active-active, Kubernetes, enterprise SLA, or production school rollout.
- Anonymous unlimited generation, payment, subscription, or user billing.
- Republishing a real teacher's private run as a portfolio sample.
- Claiming teacher usability when the independent product-validation threshold fails or is incomplete.

## Main Flow

1. A reviewer opens the public entry, understands the product/evidence boundary, and signs in through the managed identity flow.
2. The reviewer explores a synthetic complete run or performs a bounded private preparation flow.
3. The reviewer inspects sources, Agent work, artifacts, evaluation, cost, failure, and recovery evidence.
4. The release view reports technical and product-validation outcomes honestly and links to reproducible project verification.

## Core Business Rules

- Technical Phase 1 is complete only if the deployed representative workflow proves all approved core technical evidence and passes public guardrail, accessibility, and recovery checks.
- Missing evidence, cross-account isolation failure, duplicate model work on retry, or failed injected recovery prevents technical completion.
- Product validation may be failed or not complete without blocking an honest technical release, but teacher-usability claims remain prohibited.
- Portfolio samples are synthetic under the current privacy decision; private teacher projects remain owner-only and deletable.
- Deployment automation and infrastructure cannot become a new business Source of Truth.
- Real commands and operational claims are documented only after they execute successfully; placeholders are never replaced with invented commands.

## Main Entities / Concepts

| Concept | Role in this Feature | Source of Truth / owner |
| --- | --- | --- |
| Public portfolio entry | Explains and links to the protected experience | Web application / product documentation |
| Synthetic sample project/run | Safe inspectable demonstration evidence | Seed/evaluation process under application ownership |
| Deployment/release evidence | Proves the application and checks actually ran | Delivery record / verification artifacts, not business truth |
| Technical Phase-1 status | Reports whether all technical criteria are proven | Alignment and Evaluation from approved evidence |
| Product-validation status | Reports independent teacher evidence | Alignment and Evaluation; never inferred from deployment |

## Major API / Integration Impact

- All confirmed Web, API, Worker, database, queue, object, identity, model, and official-source boundaries must operate in the selected public environment.
- Health, smoke, operational correlation, and deployment verification are exposed only to the extent needed without leaking private or secret information.
- Exact cloud provider, topology, CI/CD product, domain, and command set wait for refinement and must be recorded after real execution.

## UI Impact

- UI involved: `YES`
- Affected screens: public entry/sign-in, complete authenticated application, synthetic sample path, account/usage, technical/product status and evidence
- Primary user flow: open public entry -> authenticate -> inspect or run bounded sample -> observe recovery/evidence -> understand separate validation statuses
- Major UI states: service starting/unavailable, verification required, quota reached, provider failure, long task active/return, synthetic sample ready/stale, technical pass/fail/missing, product pass/fail/not-complete

## Dependencies

- Feature dependencies: `F009` for reproducible technical evidence and `F011` for complete public multi-account guardrails
- External dependencies: selected cloud, identity, model, database, Redis, and object-storage providers plus an established build/test/deployment toolchain

## Initial Acceptance Criteria

These are refinement inputs, not a complete Test Design.

- [ ] Given a reviewer with a verified account, when they use the public environment, then they can independently complete or inspect the protected representative workflow and its version-bound technical evidence.
- [ ] Given a provider or Worker failure during a representative run, when the reviewer leaves and returns, then the deployed system shows accurate progress and resumes without duplicate model work or lost valid artifacts.
- [ ] Given the release status view, when technical and product evidence differ, then both outcomes remain explicit and no teacher-usability claim is made without a product-validation pass.
- [ ] Given project/account deletion in the public environment, when cleanup completes, then governed private data and complete traces are removed across selected services.
- [ ] Given the repository documentation, when a reviewer follows established commands and evidence, then commands are real, synchronized, and sufficient to verify the documented stage.

## Risks and Assumptions

- [CONFIRMED] A public cloud demo is required for the portfolio outcome.
- [CONFIRMED] Correctness and recoverability take priority over a fixed full-unit latency promise.
- [RECOMMENDED] Prefer the smallest provider topology that supports the confirmed runtime boundaries and evidence. Revisit only when measured reliability, cost, or provider limits require change.
- [UNKNOWN, NON_BLOCKING] Exact cloud providers, public limits, domain, and operational budget are not selected. Resolve during Feature refinement before implementation planning.

## Open Questions

- [ ] Which provider set satisfies deletion, private object, managed identity, Worker, Redis, database, and model requirements at acceptable cost?
- [ ] What bounded reviewer generation experience complements synthetic samples without creating abuse or unpredictable expense?
- [ ] Which release, smoke, rollback, backup, and failure-recovery evidence is required for a credible portfolio claim?
- [ ] What availability and startup behavior is acceptable without claiming a production SLA?
- [ ] How are technical and product-validation statuses published without exposing private evaluation or trace data?

## Deliberately Deferred Detail

- DTOs and concrete request/response schemas
- Database fields, indexes and migrations
- Classes, packages, components and internal functions
- Cache keys, message topics and deployment minutiae
- Pixel-level UI and complete Test Design

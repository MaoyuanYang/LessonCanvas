# Testing

## Testing Philosophy

- Define correct behavior and observable evidence before implementation.
- Test behavior and contracts, not private implementation structure.
- Choose depth by risk; do not optimize for test count.
- Bug fixes should include a regression test when practical.
- Keep technical Phase-1 success and teacher product validation as separate, visible outcomes.
- Model-based evaluation may contribute evidence but may never be the only authority for product validation.

## Risk Map

| Risk / behavior | Impact | Preferred evidence |
| --- | --- | --- |
| Cross-account access | Private teacher material or traces leak | Authorization integration tests, adversarial API tests, and critical-path E2E |
| Duplicate submission or retry | Duplicate model cost, artifacts, or inconsistent status | Deterministic state tests plus database/queue concurrency integration tests |
| Worker or provider failure | Long unit generation is lost or restarts from zero | Injected-failure integration and E2E recovery tests |
| Upstream revision during generation | Stale output overwrites current intent | Version-state tests and supersession integration tests |
| Hallucinated or ungrounded content | Teacher cannot explain or trust artifacts | Citation checks, retrieval evaluation, model-assisted review, and teacher rubric |
| Cross-artifact misalignment | Lessons, slides, and exercises contradict objectives | Deterministic coverage checks, evaluation set, and teacher review |
| Incorrect English, answers, or pedagogy | Product claim is misleading | External teacher rubric with a zero-severe-error gate |
| Prompt or document injection | Source data changes policy or leaks tools/data | Adversarial source corpus, tool-authorization tests, and security review |
| Broken Office exports | Claimed deliverable cannot be edited or opened | File-structure validation and open/render smoke checks |
| Long-task UI ambiguity | User retries, leaves, or cannot recover safely | Component interaction tests and critical E2E flows |
| Accessibility regression | Core flow excludes keyboard or assistive-technology users | Automated checks plus manual keyboard/focus review against WCAG 2.2 AA |
| Model cost or latency regression | Public demo becomes unusable or unaffordable | Per-stage telemetry assertions, evaluation reports, and bounded performance runs |
| Streaming interruption or reconnect | Partial responses duplicate work or lose authoritative content | API/SSE integration tests for reconnect, stop semantics, and trace completeness |
| Malicious MCP server or tool metadata | Tool authorization, policy, or data boundaries are bypassed | Adversarial MCP integration cases inside injection and security tests |
| Memory contamination or self-injection | Confirmed memory poisons later runs or overrides intent | Memory injection cases, authority-rule tests, and teacher-management flows |

## Test Layers

| Layer | Use for | Avoid |
| --- | --- | --- |
| Unit | State transitions, impact rules, source policy, quota rules, status derivation, and evaluation calculations | Framework internals and prompt snapshots as sole evidence |
| Integration | PostgreSQL transactions, pgvector retrieval, Celery/Redis delivery, checkpoints, object lifecycle, identity verification, provider adapters, Office rendering, MCP client/tool boundaries, and SSE streaming | Duplicating all pure rule cases |
| API / Contract | Ownership, errors, stale-version conflicts, idempotency, upload/download authorization, and SSE behavior | Private functions or incidental serialization |
| Component / Interaction | Confirmation gates, structured revisions, progress, stale state, partial failure, recovery, and layered trace disclosure | Pixel assertions without regression value |
| E2E | Login-to-private-project, brief and blueprint confirmation, representative generation (lesson plans, slide decks, and exercise/answer pairs across live and fault stacks), layered run-evidence inspection, revision impact and targeted regeneration across fault and live stacks, alignment review with reasoned override and validated package delivery (deterministic stack), failure recovery, review, override, export, and deletion | Every content permutation or low-level edge case |
| Accessibility | Keyboard path, focus restoration, labels, announcements, contrast, and reduced motion | Treating automated scans as complete WCAG proof |
| Visual regression | Shared workspace foundations, status distinctions, responsive modes, and high-risk document/evidence layouts | Broad screenshot churn or pixel-perfect assertions without user risk |
| Security | Isolation, untrusted files, prompt injection, authorized objects, secrets, audit, and dependency risk | Enterprise compliance claims outside Phase 1 |
| Concurrency / Recovery | Duplicate requests, retries, Worker restart, supersession, quota races, and cleanup reconciliation | Synthetic load with no business invariant |
| Evaluation | Grounding, alignment, language, answer quality, specialist behavior, cost, and recovery evidence | A single LLM judge as release authority |

## Environments and Test Data

- Environments: local, CI, and a public-demo-like staging environment once scaffolding exists. Provider-live evaluations run separately from deterministic CI unless cost and stability permit otherwise.
- Isolation: every test creates explicit workspace ownership and cleans all database, vector, object, and trace state. Cross-owner negative cases are mandatory.
- Test data: use synthetic, public, or explicitly licensed senior-high English samples. Never use identifiable student information or a teacher's private material as an ungoverned fixture.
- External services: use fakes for deterministic rule tests, contract tests or sandboxes for provider boundaries, and a controlled live suite for model and rendering evidence.

## Content and Agent Evaluation

- The automated evaluation set contains at least three representative complete units covering Chinese, English, and bilingual output modes.
- [RESOLVED, 2026-09-01] The F009 technical-evaluation dataset ships in-repo under `apps/backend/src/lessoncanvas/evaluation_datasets/` (units `travelling-around` English, `natural-disasters` Chinese, `cultural-heritage` bilingual; CC0-1.0 dedicated self-authored synthetic content; SHA-256 manifest with dataset revision `eval-datasets-r1`; loading fails closed on any governance violation). Deterministic evaluation scenarios run in the standard pytest stack against the fake adapter; injected faults are armed only through eval fault profiles honored when `LESSONCANVAS_MODEL_ADAPTER=fake` and `LESSONCANVAS_EVAL_FAULT_PROFILE` is set — production configurations can never inject faults. The controlled live-model protocol (two full passes per unit plus one real-worker stop/restart recovery demonstration) executes separately from deterministic suites with owner authorization and is recorded in the owning Feature's Test Design execution snapshot, never as a CI gate.
- One external senior-high English teacher fully reviews at least two representative complete units with a consistent rubric.
- Product validation requires zero severe knowledge, language, answer, or objective-alignment errors; a core-rubric mean of at least 4/5; and no structural rework.
- Technical Phase 1 can pass while product validation fails, but the release must show the failed product status and must not claim teacher usability.
- Complete run traces bind evaluation results to source, intent, workflow, model configuration, artifacts, and versions so regressions are comparable.

## Commands

```text
Backend unit/integration:  cd apps/backend && uv run pytest
Backend lint:              uv run ruff check src tests migrations
Frontend component tests:  corepack pnpm web:test          (Vitest + Testing Library)
Frontend lint/typecheck:   corepack pnpm web:lint / web:typecheck
E2E:                       corepack pnpm --filter web test:e2e   (Playwright; authenticated spec gated by CLERK_E2E=1)
Services:                  docker compose -f infra/docker-compose.yml up -d
Dev DB migration:          cd apps/backend && uv run alembic upgrade head   (run after pulling new migrations; the test DB upgrades automatically)
```

Deterministic suites replace DeepSeek and Clerk with scripted fakes; live-provider evidence runs separately (F001 Test Design TQ-001). Integration tests that require local services skip automatically when a service is unreachable.

When commands change, update this file, `README.md`, and `AGENTS.md` in the same change.

## Feature Test Design Rule

Each Feature must progress from Acceptance Criteria to Test Scenarios before Coding. DRAFT Specs contain only initial acceptance direction; detailed Test Design belongs to `feature-dev`.

## Definition of Done

- Required behavior and important failure paths are verified at the risk-appropriate layers.
- Relevant regression, integration, UI, accessibility, security, recovery, and evaluation checks pass.
- Build, lint, type, and static checks required by the established toolchain pass.
- Technical and product-validation outcomes are reported separately and without inflated claims.
- Documentation, Spec, work item, and the adopted PR/MR or no-PR Delivery Record are synchronized.

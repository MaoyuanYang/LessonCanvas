# Product

## Vision

LessonCanvas should demonstrate production-minded Agent application engineering through a credible teacher workflow. Its primary Phase-1 outcome is an inspectable technical portfolio; teacher-facing usefulness is evaluated independently and must never be overstated when the product evidence fails.

## Problem

- [CONFIRMED] A participating senior-high English teacher confirmed that keeping objectives, source material, lesson plans, slides, and exercises aligned is a real preparation problem. Misalignment creates avoidable rework and teaching-quality risk.
- [CONFIRMED] Existing generative tools can produce isolated content, but a teacher still has to discover missing requirements, reconcile conflicting outputs, and reconstruct why a result was produced.

## Target Users

| User / role | Need | Relevant permissions or boundary |
| --- | --- | --- |
| Individual senior-high English teacher | Plan a complete unit from owned materials and inspect or revise the result | Can access only their own workspace, sources, runs, traces, and artifacts |
| `YMY / Project Owner` | Approve product, roadmap, and architecture decisions and operate the portfolio demo | Operational access must be disclosed, controlled, and audited; it is not a teacher-content ownership claim |
| Participating English teacher evaluator | Validate the problem and review representative generated units | Provides domain evidence but does not approve project architecture or roadmap |

## Primary Scenarios

1. A teacher creates a unit-preparation project, supplies goals and legally usable materials, answers targeted questions, and confirms a structured requirements brief.
2. The Agent proposes a unit blueprint, the teacher confirms it, and the system asynchronously generates every lesson's plan, editable slides, exercises, answers, and an alignment review.
3. The teacher sees progress and evidence, reviews findings, makes a structured upstream correction or targeted revision request, and regenerates only affected work.
4. A failed or superseded run resumes or stops at a safe checkpoint without duplicating model cost, losing completed work, or overwriting a newer version.
5. A reviewer inspects complete traces, sources, specialist-Agent decisions, cost, latency, evaluations, and injected-failure recovery as portfolio evidence.

## Core Value

The differentiator is not one-shot content generation. LessonCanvas turns teacher-confirmed intent into a traceable, versioned, recoverable multi-artifact workflow and makes both its technical evidence and its product-validation status visible.

## MVP

- Complete one senior-high English unit, including every lesson, through two teacher confirmation gates.
- Generate a structured DOCX lesson plan, editable PPTX deck, and DOCX exercises and answers for every lesson, plus a unit-level Web alignment report.
- Support task-level Chinese, English, or bilingual output.
- Persist complete run traces and show sources, decisions, specialist steps, tools, latency, cost, evaluation, and recovery.
- Support versioned targeted regeneration, idempotent retry, and safe supersession of an active older version.

## Phase-1 Scope

- Multiple individual teacher accounts with strict owner isolation and managed authentication.
- Teacher-owned private source materials and a controlled set of official public sources.
- Stateful needs discovery, a confirmed requirements brief, and a confirmed unit blueprint.
- Explicitly orchestrated specialist Agents; unconstrained peer-Agent negotiation is excluded.
- Long-running asynchronous generation with progress, partial failure, safe retry, and checkpoint recovery.
- Structured Web revision and version comparison; final formatting remains editable in exported Office files.
- A public cloud demo protected by verified login, per-user quotas, rate limits, and concurrency limits.
- Layered teacher-friendly explanations with expandable technical run details.
- Token-level streaming for interview, explanation, and generation narration over the confirmed SSE boundary, with complete responses still captured in full traces.
- Workspace-scoped teacher memory: the Agent proposes preferences from confirmed outcomes; only teacher-confirmed records persist, personalize future work as subordinate context, and are inspectable, editable, and deleted with the workspace.

## Out of Scope

- Student-facing experiences, automatic grading, real student answers, or grade analytics.
- Any identifiable student information, real student submissions, or individual grade records.
- School organizations, tenancy hierarchies, collaboration, approval workflows, or a custom business admin console.
- LMS, school information system, timetable, identity-directory, or third-party document-suite integration.
- Foundation-model training, fine-tuning, or multi-model routing.
- Open-ended Web search or a bundled corpus of unlicensed complete textbooks.
- An in-browser Office-class editor; teachers refine final layout in exported DOCX or PPTX files.
- Full mobile preparation, native mobile or desktop clients, UI internationalization, and Dark Mode.

## Product Principles

- Technical evidence comes first, but product evidence is reported honestly and separately.
- Teacher-confirmed briefs and blueprints govern intent; an Agent may surface conflicts but may not silently replace teacher decisions.
- Important decisions belong in structured state, not only in chat history.
- Generated artifacts are rebuildable derivatives; sources, confirmed intent, versions, and run history remain traceable.
- Long work must be resumable, and retries must be idempotent.
- Private material stays private, user-owned, and deletable; it is never reused across users or for training.
- A draft may be exported, but a package cannot be marked validated while a severe finding remains unresolved or lacks a teacher-recorded override reason.
- Memory is subordinate context: it may personalize future discovery and generation but can never override or rewrite a confirmed intent version.

## Success Criteria

| Criterion | Signal / measure | Evaluation point |
| --- | --- | --- |
| Technical Phase 1 | A representative complete-unit run publicly demonstrates stateful discovery, grounding, orchestrated specialists, editable artifact generation, full traces, evaluation, idempotency, and injected-failure recovery | Before the portfolio release is called technically complete |
| Technical failure | Any core technical evidence is missing, cross-account isolation fails, a retry duplicates work or model cost, or an injected failure cannot resume safely | Every release candidate |
| Product validation | Automated evaluation covers three representative units across Chinese, English, and bilingual modes; one external teacher fully reviews at least two units; severe knowledge, language, answer, and alignment errors are zero; core rubric mean is at least 4/5; no structural rework is required | Before claiming teacher usability |
| Product-validation failure | Any product threshold fails | Record `Product validation failed` or `not complete`; technical completion may remain true, but teacher-usability claims are prohibited |
| Accessibility | Core teacher journeys meet the documented WCAG 2.2 AA baseline | Before public UI release |
| Security | Owner isolation, upload boundaries, prompt/document injection controls, authorized downloads, secret handling, audit, and dependency checks pass | Before public deployment |

## Validated Assumptions

| Assumption | Challenge / counterexample | Resolution | Status | Revisit trigger |
| --- | --- | --- | --- | --- |
| Cross-artifact alignment is a real problem | The domain might have been selected only to host an Agent demo | `RETAINED`: a target teacher confirmed the pain and cost | `CONFIRMED` | Revisit if further teachers identify a different dominant problem |
| Phase 1 needs every lesson's complete artifact set | A unit blueprint plus one anchor lesson could validate most of the direction at lower cost | `RETAINED`: the Project Owner explicitly accepted the larger scope | `CONFIRMED` | Reopen if delivery repeatedly stalls before an end-to-end technical proof |
| Teacher quality is a prerequisite for technical portfolio success | The selected project priority is technical evidence first | `REVISED`: technical success and product validation are independent statuses | `CONFIRMED` | Revisit if the project changes from a portfolio into a production product |
| Multi-Agent must earn its complexity through a simpler baseline | Multi-Agent may not improve quality, cost, or recovery | `REVISED`: it remains a portfolio coverage constraint, not a claim of production optimality | `CONFIRMED` | Re-evaluate before production positioning or material operating scale |
| Repeated and concurrent generation is harmless | Duplicate submissions, retries, and upstream edits can race and overwrite work | `REVISED`: bind runs to immutable versions, deduplicate retries, and safely supersede old runs | `CONFIRMED` | Revisit if deliberate parallel branches become a product need |

## Rejected Scope

| Item / assumption | Why rejected | Reconsider when |
| --- | --- | --- |
| Unit blueprint plus one complete anchor lesson | The Project Owner chose full-unit coverage despite delivery cost | Only through a new Scope decision |
| Unconstrained peer-Agent collaboration | Hard to reproduce, evaluate, secure, and recover | A measured use case requires negotiation that explicit orchestration cannot express |
| Self-built password authentication | Security responsibility distracts from Agent evidence | Authentication itself becomes a separately justified product objective |
| Fully open anonymous generation | Public model abuse and cost are unacceptable | A safe sponsor-funded environment can absorb abuse and moderation costs |
| Teacher data as a shared evaluation or training corpus | Conflicts with owner isolation, deletion, and material rights | Never in Phase 1; any future change requires explicit consent and a new privacy decision |

## Open Items

- [PARTIALLY RESOLVED, 2026-08-24] Initial controlled official source selected for F001: curated curriculum-standards snapshot via internal MCP-compatible tool (`YMY / Project Owner`, F001 refinement D5). Participating-teacher validation of the evidence set remains open.
- [RESOLVED, 2026-09-03] Exact rubric wording and representative unit topics were selected interactively during the evaluation Features: F009 confirmed the three representative units (`travelling-around`, `natural-disasters`, `cultural-heritage`; Spec D6) and F009/F010 refined and shipped the external-teacher rubric as `rubric-r1` with the five-dimension rubric and blocking severe-error classes (F010 Spec D1). Recorded at Phase-1 close-out (`specs/PHASE1-retrospective.md`).
- [PARTIALLY RESOLVED, 2026-09-02] Deployed portfolio environment: F012 selects local full-stack containerization with LAN access and a synthetic sample plus reviewer self-service bounded generation (`YMY / Project Owner`, F012 Spec D1–D3). Public cloud provider, region, domain, and internet exposure remain open for a follow-up deployment Feature; no availability/SLA claim is made.
- [RECOMMENDED] Use existing provider or managed-service administration rather than build a custom operations console. Revisit when sustained non-demo operations require productized support workflows.

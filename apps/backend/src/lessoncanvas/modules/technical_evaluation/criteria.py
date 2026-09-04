"""F009 deterministic technical-evaluation criteria engine (Spec D2/D6).

Zero model calls: every outcome is computed from recorded project state
(versions, runs, artifacts, trace/run events) plus the harness observation
for fault scenarios, which the engine re-verifies against the database
rather than trusting. Blocking criteria yield pass/fail/missing_evidence;
diagnostic metrics record measured values without pass/fail semantics.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from lessoncanvas.models import (
    DiscoveryRun,
    GenerationRun,
    LessonPlanArtifact,
    RunEvent,
    Source,
    TechnicalEvaluation,
    TraceEvent,
)

BLOCKING = "blocking"
DIAGNOSTIC = "diagnostic"

SCENARIO_CRITERIA: dict[str, list[str]] = {
    "full_pipeline": ["C-TRACE-1", "C-GROUND-1", "C-ART-1", "C-STAGE-1", "C-MEM-1"],
    "fault:duplicate_submission": ["C-IDEM-1"],
    "fault:stale_version": ["C-SUPER-1"],
    "fault:worker_provider_failure": ["C-RECOV-1"],
    "fault:partial_render": ["C-RENDER-1"],
    "fault:tool_loop": ["C-TOOL-1"],
    "fault:design_invalid": ["C-DESIGN-1"],
    "fault:review_fail": ["C-REVIEW-1"],
}
FULL_PIPELINE_DIAGNOSTICS = ["M-LAT", "M-COST", "M-COVER"]

CRITERION_LABELS = {
    "C-TRACE-1": "Trace completeness",
    "C-GROUND-1": "Citation resolvability",
    "C-ART-1": "Artifact family completeness",
    "C-IDEM-1": "Duplicate-submission idempotency",
    "C-SUPER-1": "Supersession safety",
    "C-RECOV-1": "Injected-failure recovery",
    "C-RENDER-1": "Partial-render explicitness",
    "C-TOOL-1": "Governed tool-loop fault handling",
    "C-STAGE-1": "Specialist stage execution and trace",
    "C-DESIGN-1": "Design-stage failure honesty",
    "C-REVIEW-1": "Review revise-round honesty",
    "C-MEM-1": "Memory pinning recorded",
    "M-LAT": "Latency distribution (diagnostic)",
    "M-COST": "Cost estimate (diagnostic)",
    "M-VAR": "Cross-pass variance (diagnostic)",
    "M-COVER": "Alignment coverage depth (diagnostic)",
    "M-JUDGE": "Model-assisted opinion (diagnostic)",
}

# F013 D6: the empty-memory label once F013 is implemented; pre-F013 rows
# recorded the legacy "empty (F013 not implemented)" placeholder and remain
# historical.
MEMORY_STATE_EMPTY = "empty"


class CriterionError(Exception):
    """Raised when a criterion cannot even be evaluated structurally."""


@dataclass
class CriterionResult:
    criterion_key: str
    classification: str
    outcome: str | None = None
    measured: dict | None = None
    evidence: dict = field(default_factory=dict)


def _run_ids(evaluation: TechnicalEvaluation) -> list[uuid.UUID]:
    return [uuid.UUID(value) for value in json.loads(evaluation.run_ids_json)]


def _evaluation_citations(payload: dict) -> list[dict]:
    citations: list[dict] = []
    unit = payload.get("unit") or {}
    for objective in unit.get("objectives") or []:
        for citation in objective.get("citations") or []:
            citations.append(citation)
    for lesson in payload.get("lessons") or []:
        for citation in lesson.get("citations") or []:
            citations.append(citation)
    return [item for item in citations if isinstance(item, dict)]


def evaluate_trace_completeness(
    session: Session, evaluation: TechnicalEvaluation
) -> CriterionResult:
    run_ids = _run_ids(evaluation)
    evidence: dict = {"runs": []}
    violations: list[str] = []
    for run_id in run_ids:
        generation = session.get(GenerationRun, run_id)
        discovery = None if generation is not None else session.get(DiscoveryRun, run_id)
        if generation is None and discovery is None:
            violations.append(f"run:{run_id}:missing")
            continue
        model_calls = (
            generation.model_calls if generation is not None else (discovery.model_calls or 0)
        )
        # F015: every billed model call must be traced with usage. Tool-loop
        # rounds bill as model calls and trace as `tool.request` events
        # (request + usage), so both event kinds count toward the
        # trace-completeness ledger.
        traced = len(
            session.scalars(
                select(TraceEvent.id).where(
                    TraceEvent.run_id == run_id,
                    TraceEvent.event_type.startswith("model.")
                    | (TraceEvent.event_type == "tool.request"),
                )
            ).all()
        )
        entry = {"run_id": str(run_id), "model_calls": model_calls, "traced_model_calls": traced}
        if generation is not None:
            entry["run_events"] = len(
                session.scalars(
                    select(RunEvent.id).where(RunEvent.run_id == run_id)
                ).all()
            )
            if entry["run_events"] == 0:
                violations.append(f"run:{run_id}:no_run_events")
        if model_calls > 0 and traced != model_calls:
            violations.append(f"run:{run_id}:model_call_trace_mismatch({traced}/{model_calls})")
        if model_calls == 0 and traced == 0:
            violations.append(f"run:{run_id}:no_model_evidence")
        evidence["runs"].append(entry)
    evidence["violations"] = violations
    return CriterionResult(
        criterion_key="C-TRACE-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence=evidence,
    )


def evaluate_citation_resolvability(
    session: Session, evaluation: TechnicalEvaluation
) -> CriterionResult:
    if evaluation.blueprint_version_id is None:
        return CriterionResult(
            criterion_key="C-GROUND-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no bound blueprint version"},
        )
    from lessoncanvas.models import BlueprintVersion

    version = session.get(BlueprintVersion, evaluation.blueprint_version_id)
    payload = json.loads(version.payload_json) if version else {}
    citations = _evaluation_citations(payload)
    if not citations:
        return CriterionResult(
            criterion_key="C-GROUND-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "blueprint carries no citations to verify"},
        )
    known_sources = {
        str(row.id): row.filename
        for row in session.scalars(
            select(Source).where(Source.project_id == evaluation.project_id)
        ).all()
    }
    unresolved: list[dict] = []
    for citation in citations:
        if citation.get("type") == "source":
            source_id = str(citation.get("source_id") or "")
            if source_id not in known_sources:
                unresolved.append({"citation": citation, "reason": "source not found in project"})
        elif citation.get("type") == "standards":
            if not citation.get("section_id") or not citation.get("snapshot_version"):
                unresolved.append({"citation": citation, "reason": "incomplete standards citation"})
        else:
            unresolved.append({"citation": citation, "reason": "unknown citation type"})
    return CriterionResult(
        criterion_key="C-GROUND-1",
        classification=BLOCKING,
        outcome="pass" if not unresolved else "fail",
        evidence={
            "citation_count": len(citations),
            "unresolved": unresolved,
            "checked_against_sources": sorted(known_sources),
        },
    )


def evaluate_artifact_completeness(
    session: Session, evaluation: TechnicalEvaluation
) -> CriterionResult:
    from lessoncanvas.modules.alignment_evaluation.service import compute_alignment

    alignment = compute_alignment(session, evaluation.project_id)
    findings = alignment.get("findings") or []
    severe = [f for f in findings if f.get("severity") == "severe"]
    blocking_gaps = [
        f for f in severe if str(f.get("key", "")).startswith(("gap:", "conflict:"))
    ]
    by_key = {str(f.get("key")): f for f in blocking_gaps}
    return CriterionResult(
        criterion_key="C-ART-1",
        classification=BLOCKING,
        outcome="pass" if not blocking_gaps else "fail",
        evidence={
            "severe_finding_keys": sorted(by_key),
            "technical_package_status": alignment.get("package_status"),
            "note": "reuses the F008 deterministic alignment read model",
        },
    )


def evaluate_memory_pinning(evaluation: TechnicalEvaluation) -> CriterionResult:
    try:
        memory = json.loads(evaluation.memory_state_json)
    except json.JSONDecodeError:
        memory = None
    # F013 D6: a recorded pinning is the structured revision-list snapshot
    # (memory_state label plus the record id list); the pre-F013 bare-label
    # placeholder no longer satisfies the criterion for new passes.
    recorded = (
        isinstance(memory, dict)
        and bool(str(memory.get("memory_state") or "").strip())
        and isinstance(memory.get("record_ids"), list)
    )
    record_ids = memory.get("record_ids") if isinstance(memory, dict) else None
    return CriterionResult(
        criterion_key="C-MEM-1",
        classification=BLOCKING,
        outcome="pass" if recorded else "fail",
        evidence={
            "memory_state": (memory or {}).get("memory_state") if memory else None,
            "record_count": len(record_ids) if isinstance(record_ids, list) else None,
        },
    )


def evaluate_duplicate_submission(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    if not observation:
        return CriterionResult(
            criterion_key="C-IDEM-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no duplicate-submission observation recorded"},
        )
    returned = [str(value) for value in observation.get("returned_run_ids") or []]
    submissions = observation.get("submissions") or []
    runs_for_pair = session.scalars(
        select(GenerationRun).where(
            GenerationRun.project_id == evaluation.project_id,
            GenerationRun.artifact_kind == str(observation.get("artifact_kind") or "lesson_plan"),
            GenerationRun.brief_version_id == evaluation.brief_version_id,
            GenerationRun.blueprint_version_id == evaluation.blueprint_version_id,
        )
    ).all()
    distinct_runs = {str(run.id) for run in runs_for_pair}
    single_run = len(distinct_runs) == 1
    converged = len(returned) >= 2 and len(set(returned)) == 1
    outcome = (
        "pass"
        if (single_run and converged and len(submissions) >= 2)
        else ("fail" if submissions else "missing_evidence")
    )
    return CriterionResult(
        criterion_key="C-IDEM-1",
        classification=BLOCKING,
        outcome=outcome,
        evidence={
            "submissions": submissions,
            "returned_run_ids": returned,
            "distinct_runs_for_kind": sorted(distinct_runs),
        },
    )


def evaluate_supersession_safety(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    if not observation:
        return CriterionResult(
            criterion_key="C-SUPER-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no supersession observation recorded"},
        )
    stale_id = str(observation.get("stale_run_id") or "")
    stale = session.get(GenerationRun, uuid.UUID(stale_id)) if stale_id else None
    violations: list[str] = []
    if stale is None:
        violations.append("stale run missing")
    else:
        if stale.status != "superseded":
            violations.append(f"stale run status is {stale.status}, expected superseded")
        if observation.get("newer_run_id"):
            newer = session.get(GenerationRun, uuid.UUID(str(observation["newer_run_id"])))
            if newer is None or newer.status != "complete":
                violations.append("newer-version run did not complete")
        if observation.get("stale_artifacts_published_after_supersession"):
            violations.append("stale run published artifacts after supersession")
    return CriterionResult(
        criterion_key="C-SUPER-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence={"observation": observation, "violations": violations},
    )


def evaluate_recovery(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    if not observation:
        return CriterionResult(
            criterion_key="C-RECOV-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no recovery observation recorded"},
        )
    run_id = str(observation.get("run_id") or "")
    run = session.get(GenerationRun, uuid.UUID(run_id)) if run_id else None
    violations: list[str] = []
    if run is None:
        violations.append("run missing")
    else:
        if run.status != "complete":
            violations.append(f"run status is {run.status}, expected complete after recovery")
        preserved = observation.get("preserved_lessons") or []
        if preserved:
            rows = session.scalars(
                select(LessonPlanArtifact).where(
                    LessonPlanArtifact.run_id == run.id,
                    LessonPlanArtifact.lesson_index.in_(preserved),
                    LessonPlanArtifact.status == "complete",
                )
            ).all()
            if len(rows) != len(set(preserved)):
                violations.append("pre-failure completed scope not preserved")
        expected_calls = observation.get("expected_model_calls")
        if isinstance(expected_calls, int) and run.model_calls != expected_calls:
            violations.append(
                f"duplicate billing suspected: model_calls {run.model_calls}"
                f" != expected {expected_calls}"
            )
    return CriterionResult(
        criterion_key="C-RECOV-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence={"observation": observation, "violations": violations},
    )


def evaluate_partial_render(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    if not observation:
        return CriterionResult(
            criterion_key="C-RENDER-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no partial-render observation recorded"},
        )
    run_id = str(observation.get("run_id") or "")
    lesson_index = observation.get("lesson_index")
    run = session.get(GenerationRun, uuid.UUID(run_id)) if run_id else None
    violations: list[str] = []
    if run is None or lesson_index is None:
        violations.append("run or lesson missing from observation")
    else:
        events = session.scalars(
            select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.id)
        ).all()

        def event_payload(event) -> dict:
            try:
                return json.loads(event.payload_json) if event.payload_json else {}
            except json.JSONDecodeError:
                return {}

        failed_marker = any(
            event.event_type == "lesson"
            and event_payload(event).get("lesson_index") == lesson_index
            and event_payload(event).get("status") == "failed"
            for event in events
        )
        if not failed_marker:
            violations.append("no explicit validation-failure event recorded for the lesson")
        artifact = session.scalars(
            select(LessonPlanArtifact).where(
                LessonPlanArtifact.run_id == run.id,
                LessonPlanArtifact.lesson_index == lesson_index,
            )
        ).first()
        if artifact is not None and observation.get("fabricated_success_detected"):
            violations.append("fabricated success recorded for truncated content")
    return CriterionResult(
        criterion_key="C-RENDER-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence={"observation": observation, "violations": violations},
    )


def measure_latency(session: Session, evaluation: TechnicalEvaluation) -> CriterionResult:
    run_ids = _run_ids(evaluation)
    rows = session.scalars(
        select(TraceEvent).where(
            TraceEvent.run_id.in_(run_ids or [uuid.uuid4()]),
            TraceEvent.latency_ms.is_not(None),
        )
    ).all()
    by_stage: dict[str, list[int]] = {}
    for row in rows:
        by_stage.setdefault(row.event_type, []).append(int(row.latency_ms or 0))
    measured = {
        stage: {
            "count": len(values),
            "p50_ms": sorted(values)[len(values) // 2],
            "max_ms": max(values),
        }
        for stage, values in sorted(by_stage.items())
    }
    return CriterionResult(
        criterion_key="M-LAT",
        classification=DIAGNOSTIC,
        measured=measured,
        evidence={"run_ids": [str(value) for value in run_ids]},
    )


def measure_cost(session: Session, evaluation: TechnicalEvaluation) -> CriterionResult:
    run_ids = _run_ids(evaluation)
    rows = session.scalars(
        select(TraceEvent).where(TraceEvent.run_id.in_(run_ids or [uuid.uuid4()]))
    ).all()
    cost_values = [row.cost_usd for row in rows]
    known = [value for value in cost_values if value is not None]
    token_rows = [
        row
        for row in rows
        if row.event_type.startswith("model.")
    ]
    missing_usage = sum(
        1 for row in token_rows if row.prompt_tokens is None and row.completion_tokens is None
    )
    measured = {
        "estimated_cost_usd": round(sum(known), 6) if known else None,
        "events_with_cost": len(known),
        "events_total": len(rows),
        "model_events_missing_usage": missing_usage,
        "narration_events_missing_usage": sum(
            1
            for row in token_rows
            if row.event_type == "model.narration"
            and row.prompt_tokens is None
            and row.completion_tokens is None
        ),
    }
    return CriterionResult(
        criterion_key="M-COST",
        classification=DIAGNOSTIC,
        measured=measured,
        evidence={"run_ids": [str(value) for value in run_ids]},
    )


def measure_coverage(session: Session, evaluation: TechnicalEvaluation) -> CriterionResult:
    from lessoncanvas.modules.alignment_evaluation.service import compute_alignment

    alignment = compute_alignment(session, evaluation.project_id)
    findings = alignment.get("findings") or []
    distribution: dict[str, int] = {"severe": 0, "warning": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity") or "info")
        distribution[severity] = distribution.get(severity, 0) + 1
    return CriterionResult(
        criterion_key="M-COVER",
        classification=DIAGNOSTIC,
        measured={
            "finding_severity_distribution": distribution,
            "package_status": alignment.get("package_status"),
        },
        evidence={"source": "F008 alignment read model"},
    )


def evaluate_tool_loop_governance(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    """F015 C-TOOL-1: every fault variant ends in an honest, governed state —
    refusals traced and never dispatched, the cap never over-billed, the
    deterministic fallback completing the stage. Judged from recorded state;
    the harness observation is only a pointer set."""

    from lessoncanvas.settings import get_settings

    variants = (observation or {}).get("variants") or []
    evidence: dict = {"variants": []}
    violations: list[str] = []
    if not variants:
        return CriterionResult(
            criterion_key="C-TOOL-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no tool-loop variants recorded"},
        )

    max_rounds = get_settings().tool_loop_max_rounds
    for variant in variants:
        run = session.get(DiscoveryRun, uuid.UUID(variant["planning_run_id"]))
        if run is None:
            violations.append(f"{variant['variant']}:run_missing")
            continue
        events = session.scalars(
            select(TraceEvent).where(TraceEvent.run_id == run.id)
        ).all()

        def payloads_of(source_events, event_type: str) -> list[dict]:
            return [
                json.loads(event.payload_json)
                for event in source_events
                if event.event_type == event_type
            ]

        requests = payloads_of(events, "tool.request")
        refused = payloads_of(events, "tool.refused")
        results = payloads_of(events, "tool.result")
        fallback = payloads_of(events, "tool.fallback")
        entry = {
            "variant": variant["variant"],
            "run_id": str(run.id),
            "model_calls": run.model_calls,
            "requests": len(requests),
            "refusals": len(refused),
            "dispatched": len([p for p in results if p.get("outcome") == "dispatched"]),
            "failed_rounds": len([p for p in results if p.get("outcome") == "failed"]),
            "fallback": bool(fallback),
            "draft_persisted": bool(run.draft_json),
        }
        evidence["variants"].append(entry)
        if not run.draft_json:
            violations.append(f"{variant['variant']}:no_draft")
        kind = variant["variant"]
        # The loop is bounded per invocation regardless of interview rounds:
        # at most max_rounds traced requests (each one billed model call).
        if len(requests) > max_rounds:
            violations.append(f"{kind}:loop_overbilled({len(requests)})")
        # Every billed call on the run stays in the trace ledger (C-TRACE-1
        # invariant restated for the loop-aware vocabulary).
        traced_ledger = len(
            session.scalars(
                select(TraceEvent.id).where(
                    TraceEvent.run_id == run.id,
                    TraceEvent.event_type.startswith("model.")
                    | (TraceEvent.event_type == "tool.request"),
                )
            ).all()
        )
        if traced_ledger != run.model_calls:
            violations.append(f"{kind}:ledger_mismatch({traced_ledger}/{run.model_calls})")
        if kind == "cap_exhaustion":
            if len(requests) != max_rounds:
                violations.append(f"cap:requests({len(requests)}!={max_rounds})")
            if not fallback or fallback[0].get("reason") != "round_cap_exhausted":
                violations.append("cap:fallback_not_disclosed")
        elif kind == "unknown_tool":
            if not refused or "whitelist" not in str(refused[0].get("reason", "")):
                violations.append("unknown_tool:refusal_not_traced")
            if any(
                p.get("name") != "search_curriculum_standards" and p.get("outcome") == "dispatched"
                for p in results
            ):
                violations.append("unknown_tool:non_whitelisted_dispatch")
        elif kind == "malformed_arguments":
            if not refused or not str(refused[0].get("reason", "")).startswith(
                ("missing required argument", "argument ", "arguments ")
            ):
                violations.append("malformed:refusal_reason_missing")
        elif kind == "tool_failure_mid_loop":
            if not entry["failed_rounds"]:
                violations.append("tool_failure:not_traced")
            if not fallback:
                violations.append("tool_failure:no_fallback")

    return CriterionResult(
        criterion_key="C-TOOL-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence=evidence,
    )


FAMILY_EVENT_SUFFIX = {"lesson_plan": "lesson", "slide_deck": "deck", "exercise": "exercises"}


def _artifacts_for_run(session: Session, run: GenerationRun) -> list:
    from lessoncanvas.modules.run_orchestration import service as run_service

    fetch = {
        "lesson_plan": run_service.artifacts_of,
        "slide_deck": run_service.deck_artifacts_of,
        "exercise": run_service.exercise_artifacts_of,
    }[run.artifact_kind]
    return fetch(session, run.id)


def _trace_lesson_index(payload: dict):
    """Lesson index of a trace payload: tool/retrieval events carry it at the
    top level; model-stage events nest it under prompt.lesson."""

    if isinstance(payload.get("lesson_index"), int):
        return payload["lesson_index"]
    prompt = payload.get("prompt")
    source = prompt if isinstance(prompt, dict) else payload
    lesson = source.get("lesson") or {}
    return lesson.get("lesson_index") if isinstance(lesson, dict) else None


def evaluate_specialist_stages(
    session: Session, evaluation: TechnicalEvaluation
) -> CriterionResult:
    """F016 C-STAGE-1: every completed artifact carries its family's full
    specialist stage trace (design for plans; write and review everywhere),
    revise rounds stay bounded, and review strictly precedes rendering."""

    violations: list[str] = []
    evidence: dict = {"complete_artifacts": 0, "stage_events": {}}
    for run_id in _run_ids(evaluation):
        run = session.get(GenerationRun, run_id)
        if run is None or run.artifact_kind not in FAMILY_EVENT_SUFFIX:
            continue
        suffix = FAMILY_EVENT_SUFFIX[run.artifact_kind]
        write_kind = f"model.generation_write_{suffix}"
        review_kind = f"model.generation_review_{suffix}"
        revise_kind = f"model.generation_revise_{suffix}"
        traces = (
            session.scalars(
                select(TraceEvent).where(TraceEvent.run_id == run_id)
            ).all()
        )
        # RunEvent rows carry a monotonic seq: stage ORDER is judged there,
        # not on trace timestamps (same-microsecond ties scramble trace order).
        run_events = (
            session.scalars(
                select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.seq)
            ).all()
        )
        for artifact in _artifacts_for_run(session, run):
            if artifact.status != "complete":
                continue
            evidence["complete_artifacts"] += 1
            lesson_events = [
                event
                for event in traces
                if _trace_lesson_index(json.loads(event.payload_json or "{}"))
                == artifact.lesson_index
            ]
            kinds = [event.event_type for event in lesson_events]
            evidence["stage_events"][f"{run_id}:{artifact.lesson_index}"] = kinds
            if run.artifact_kind == "lesson_plan" and (
                "model.generation_design_lesson" not in kinds
            ):
                violations.append(f"lesson{artifact.lesson_index}:missing_design")
            if write_kind not in kinds:
                violations.append(f"lesson{artifact.lesson_index}:missing_write")
            if review_kind not in kinds:
                violations.append(f"lesson{artifact.lesson_index}:missing_review")
            if kinds.count(revise_kind) > 1:
                violations.append(f"lesson{artifact.lesson_index}:revise_unbounded")
            if getattr(artifact, "review_rounds", 0) > 2:
                violations.append(f"lesson{artifact.lesson_index}:rounds_unbounded")

            def _payload(item) -> dict:
                try:
                    return json.loads(item.payload_json) if item.payload_json else {}
                except json.JSONDecodeError:
                    return {}

            lesson_statuses = [
                _payload(item).get("status")
                for item in run_events
                if item.event_type == "lesson"
                and _payload(item).get("lesson_index") == artifact.lesson_index
                and _payload(item).get("status")
            ]
            try:
                last_reviewing = max(
                    i for i, st in enumerate(lesson_statuses) if st in ("reviewing", "revising")
                )
            except ValueError:
                last_reviewing = -1
            try:
                first_rendering = min(
                    i for i, st in enumerate(lesson_statuses) if st == "rendering"
                )
            except ValueError:
                first_rendering = len(lesson_statuses)
            if last_reviewing >= first_rendering:
                violations.append(f"lesson{artifact.lesson_index}:render_before_review")
    if evidence["complete_artifacts"] == 0:
        return CriterionResult(
            criterion_key="C-STAGE-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no completed artifacts to judge stages on"},
        )
    return CriterionResult(
        criterion_key="C-STAGE-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence={"violations": violations, **evidence},
    )


def evaluate_design_fault(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    """F016 C-DESIGN-1: an invalid design fails honestly after exactly one
    corrective retry — stage-named failure, no drafting, completed lessons
    preserved."""

    pointer = (observation or {}).get("run_id")
    lesson_index = (observation or {}).get("lesson_index")
    if not pointer or lesson_index is None:
        return CriterionResult(
            criterion_key="C-DESIGN-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no design-fault run recorded"},
        )
    run = session.get(GenerationRun, uuid.UUID(pointer))
    if run is None:
        return CriterionResult(
            criterion_key="C-DESIGN-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "run missing"},
        )
    violations: list[str] = []
    artifacts = _artifacts_for_run(session, run)
    faulted = [a for a in artifacts if a.lesson_index == lesson_index]
    completed = [a for a in artifacts if a.status == "complete"]
    design_events = [
        event
        for event in session.scalars(
            select(TraceEvent).where(
                TraceEvent.run_id == run.id,
                TraceEvent.event_type == "model.generation_design_lesson",
            )
        ).all()
        if _trace_lesson_index(json.loads(event.payload_json or "{}")) == lesson_index
    ]
    write_events = [
        event
        for event in session.scalars(
            select(TraceEvent).where(
                TraceEvent.run_id == run.id,
                TraceEvent.event_type == "model.generation_write_lesson",
            )
        ).all()
        if _trace_lesson_index(json.loads(event.payload_json or "{}")) == lesson_index
    ]
    if not faulted or faulted[0].status != "failed":
        violations.append("faulted_lesson_not_failed")
    elif "design stage failed" not in (faulted[0].failure_reason or ""):
        violations.append("failure_not_stage_named")
    if len(design_events) != 2:
        violations.append(f"design_attempts_{len(design_events)}")
    if write_events:
        violations.append("drafted_after_design_failure")
    if not completed:
        violations.append("no_completed_lessons_preserved")
    return CriterionResult(
        criterion_key="C-DESIGN-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence={"violations": violations, "settled_status": run.status},
    )


def evaluate_review_fault(
    session: Session, evaluation: TechnicalEvaluation, observation: dict | None
) -> CriterionResult:
    """F016 C-REVIEW-1: severe findings twice settle failed-after-revise —
    exactly one revise round, no rendering of the rejected draft, completed
    lessons preserved."""

    pointer = (observation or {}).get("run_id")
    lesson_index = (observation or {}).get("lesson_index")
    if not pointer or lesson_index is None:
        return CriterionResult(
            criterion_key="C-REVIEW-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "no review-fault run recorded"},
        )
    run = session.get(GenerationRun, uuid.UUID(pointer))
    if run is None:
        return CriterionResult(
            criterion_key="C-REVIEW-1",
            classification=BLOCKING,
            outcome="missing_evidence",
            evidence={"reason": "run missing"},
        )
    violations: list[str] = []
    artifacts = _artifacts_for_run(session, run)
    faulted = [a for a in artifacts if a.lesson_index == lesson_index]
    completed = [a for a in artifacts if a.status == "complete"]
    traces = [
        event
        for event in session.scalars(
            select(TraceEvent).where(TraceEvent.run_id == run.id)
        ).all()
        if _trace_lesson_index(json.loads(event.payload_json or "{}")) == lesson_index
    ]
    kinds = [event.event_type for event in traces]
    if not faulted or faulted[0].status != "failed":
        violations.append("faulted_lesson_not_failed")
    else:
        if faulted[0].review_outcome != "failed_after_revise":
            violations.append("outcome_not_failed_after_revise")
        if faulted[0].review_rounds != 2:
            violations.append("rounds_not_two")
        if "review stage" not in (faulted[0].failure_reason or ""):
            violations.append("failure_not_stage_named")
    if kinds.count("model.generation_review_lesson") != 2:
        violations.append("review_round_count_wrong")
    if kinds.count("model.generation_revise_lesson") != 1:
        violations.append("revise_round_count_wrong")
    if any(kind.startswith("tool.render_") for kind in kinds):
        violations.append("rendered_rejected_draft")
    if not completed:
        violations.append("no_completed_lessons_preserved")
    return CriterionResult(
        criterion_key="C-REVIEW-1",
        classification=BLOCKING,
        outcome="pass" if not violations else "fail",
        evidence={"violations": violations, "settled_status": run.status},
    )


def evaluate_pass(
    session: Session,
    evaluation: TechnicalEvaluation,
    observation: dict | None = None,
) -> list[CriterionResult]:
    """Compute the criterion results defined for one evaluation pass.

    Deterministic: identical recorded state yields identical outcomes. The
    harness observation is re-verified against recorded state, never trusted.
    """

    results: list[CriterionResult] = []
    for key in SCENARIO_CRITERIA.get(evaluation.scenario, []):
        if key == "C-TRACE-1":
            results.append(evaluate_trace_completeness(session, evaluation))
        elif key == "C-GROUND-1":
            results.append(evaluate_citation_resolvability(session, evaluation))
        elif key == "C-ART-1":
            results.append(evaluate_artifact_completeness(session, evaluation))
        elif key == "C-MEM-1":
            results.append(evaluate_memory_pinning(evaluation))
        elif key == "C-IDEM-1":
            results.append(evaluate_duplicate_submission(session, evaluation, observation))
        elif key == "C-SUPER-1":
            results.append(evaluate_supersession_safety(session, evaluation, observation))
        elif key == "C-RECOV-1":
            results.append(evaluate_recovery(session, evaluation, observation))
        elif key == "C-RENDER-1":
            results.append(evaluate_partial_render(session, evaluation, observation))
        elif key == "C-TOOL-1":
            results.append(evaluate_tool_loop_governance(session, evaluation, observation))
        elif key == "C-STAGE-1":
            results.append(evaluate_specialist_stages(session, evaluation))
        elif key == "C-DESIGN-1":
            results.append(evaluate_design_fault(session, evaluation, observation))
        elif key == "C-REVIEW-1":
            results.append(evaluate_review_fault(session, evaluation, observation))
    if evaluation.scenario == "full_pipeline":
        results.append(measure_latency(session, evaluation))
        results.append(measure_cost(session, evaluation))
        results.append(measure_coverage(session, evaluation))
    return results


def overall_outcome(results: list[CriterionResult]) -> str | None:
    """Overall pass derives only from blocking criteria; diagnostics never
    participate, and missing_evidence never counts as pass."""

    blocking = [result for result in results if result.classification == BLOCKING]
    if not blocking:
        return None
    outcomes = {result.outcome for result in blocking}
    if "fail" in outcomes:
        return "fail"
    if "missing_evidence" in outcomes:
        return "missing_evidence"
    return "pass"

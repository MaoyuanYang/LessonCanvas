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
    "full_pipeline": ["C-TRACE-1", "C-GROUND-1", "C-ART-1", "C-MEM-1"],
    "fault:duplicate_submission": ["C-IDEM-1"],
    "fault:stale_version": ["C-SUPER-1"],
    "fault:worker_provider_failure": ["C-RECOV-1"],
    "fault:partial_render": ["C-RENDER-1"],
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
        traced = len(
            session.scalars(
                select(TraceEvent.id).where(
                    TraceEvent.run_id == run_id,
                    TraceEvent.event_type.startswith("model."),
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

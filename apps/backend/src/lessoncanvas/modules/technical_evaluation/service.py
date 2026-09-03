"""F009 technical-evaluation service: idempotent pass creation (Spec D10),
execution to terminal state, and the overview/detail/report read models."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lessoncanvas.models import TechnicalEvaluation, TechnicalEvaluationResult, Workspace, utcnow
from lessoncanvas.modules.technical_evaluation import criteria
from lessoncanvas.modules.technical_evaluation.dataset import (
    DatasetGovernanceError,
    cached_dataset,
    load_dataset,
)
from lessoncanvas.settings import get_settings

MODES = ("live", "deterministic")
# Legacy placeholder kept only so pre-F013 rows remain interpretable; new
# evaluations pin the structured revision-list snapshot below (F013 D6).
MEMORY_STATE_EMPTY_JSON = json.dumps(
    {"memory_state": criteria.MEMORY_STATE_EMPTY}, ensure_ascii=False
)
ALL_BLOCKING_KEYS = {
    key
    for keys in criteria.SCENARIO_CRITERIA.values()
    for key in keys
}


class EvaluationRequirementError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class HarnessNotFound(Exception):
    pass


def model_config_snapshot() -> str:
    settings = get_settings()
    return json.dumps(
        {
            "model_adapter": settings.model_adapter,
            "model": settings.deepseek_model,
            "checkpoint_backend": settings.checkpoint_backend,
            "tasks_eager": settings.tasks_eager,
            "max_model_calls_per_run": settings.max_model_calls_per_run,
            # F014 D5/AC-005: retrieval mode joins the pass-comparability
            # signature so truncation-era and semantic-retrieval passes never
            # compare silently.
            "retrieval_mode": settings.embedding_adapter,
        },
        ensure_ascii=False,
    )


def _memory_state_snapshot(session: Session, workspace_id: uuid.UUID) -> str:
    """F013 D6: pin the applied memory-set revision list at evaluation
    creation. Harness workspaces never confirm proposals, so the snapshot is
    the empty set by construction; comparability below includes it."""

    from lessoncanvas.modules.teacher_memory.service import memory_state_snapshot

    return memory_state_snapshot(session, workspace_id)


def create_evaluation(
    session: Session,
    workspace: Workspace,
    project_id: uuid.UUID,
    unit_key: str,
    pass_index: int,
    mode: str,
    scenario: str,
) -> tuple[TechnicalEvaluation, bool]:
    """Idempotent creation per (project, dataset revision, unit, pass index,
    mode, scenario); a duplicate returns the existing record (Spec D10)."""

    try:
        bundle = cached_dataset()
    except DatasetGovernanceError as error:
        session.rollback()
        raise EvaluationRequirementError(
            "evaluation dataset failed its governance check",
            {"rule": str(error)},
        ) from error
    if unit_key not in bundle.units:
        raise EvaluationRequirementError(
            "unknown evaluation unit", {"unit_key": unit_key, "dataset_revision": bundle.revision}
        )
    if mode not in MODES:
        raise EvaluationRequirementError("mode must be live or deterministic", {"mode": mode})
    if scenario not in criteria.SCENARIO_CRITERIA:
        raise EvaluationRequirementError("unknown evaluation scenario", {"scenario": scenario})
    if not isinstance(pass_index, int) or pass_index < 1:
        raise EvaluationRequirementError("pass_index must be a positive integer")
    adapter = get_settings().model_adapter
    if mode == "deterministic" and adapter != "fake":
        raise EvaluationRequirementError(
            "deterministic evaluation requires the fake adapter in the evaluation environment",
            {"active_adapter": adapter},
        )
    if mode == "live" and adapter == "fake":
        raise EvaluationRequirementError(
            "live evaluation requires the live model provider configuration",
            {"active_adapter": adapter},
        )

    existing = session.scalars(
        select(TechnicalEvaluation).where(
            TechnicalEvaluation.project_id == project_id,
            TechnicalEvaluation.dataset_revision == bundle.revision,
            TechnicalEvaluation.unit_key == unit_key,
            TechnicalEvaluation.pass_index == pass_index,
            TechnicalEvaluation.mode == mode,
            TechnicalEvaluation.scenario == scenario,
        )
    ).first()
    if existing is not None:
        return existing, False

    evaluation = TechnicalEvaluation(
        project_id=project_id,
        workspace_id=workspace.id,
        dataset_revision=bundle.revision,
        unit_key=unit_key,
        pass_index=pass_index,
        mode=mode,
        scenario=scenario,
        model_config_json=model_config_snapshot(),
        memory_state_json=_memory_state_snapshot(session, workspace.id),
        created_by=workspace.subject,
    )
    session.add(evaluation)
    try:
        session.commit()
    except IntegrityError:
        # Concurrent duplicate create converges on the existing record (Spec D10).
        session.rollback()
        existing = session.scalars(
            select(TechnicalEvaluation).where(
                TechnicalEvaluation.project_id == project_id,
                TechnicalEvaluation.dataset_revision == bundle.revision,
                TechnicalEvaluation.unit_key == unit_key,
                TechnicalEvaluation.pass_index == pass_index,
                TechnicalEvaluation.mode == mode,
                TechnicalEvaluation.scenario == scenario,
            )
        ).first()
        if existing is None:
            raise
        return existing, False
    _dispatch(evaluation)
    session.expire_all()
    return session.get(TechnicalEvaluation, evaluation.id), True


def _dispatch(evaluation: TechnicalEvaluation) -> None:
    from lessoncanvas.worker import run_technical_evaluation

    if get_settings().tasks_eager:
        run_technical_evaluation.apply(args=[str(evaluation.id)])
    else:
        run_technical_evaluation.delay(str(evaluation.id))


def execute_evaluation(evaluation_id: uuid.UUID) -> str:
    """Worker entrypoint: run the scenario, compute criteria, settle terminal
    status. Re-invocation of a terminal evaluation is a no-op; a crashed or
    provider-interrupted pass keeps its identity and resumes the same pass."""

    from lessoncanvas.adapters.model import ModelProviderError
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.modules.technical_evaluation import harness

    with SessionLocal() as session:
        evaluation = session.get(TechnicalEvaluation, evaluation_id)
        if evaluation is None:
            raise HarnessNotFound(f"evaluation {evaluation_id} not found")
        if evaluation.status in ("completed", "provider_unavailable", "failed"):
            return evaluation.status
        evaluation.status = "active"
        evaluation.started_at = evaluation.started_at or utcnow()
        session.commit()

        try:
            bundle = load_dataset()
            unit = bundle.units.get(evaluation.unit_key)
            if unit is None:
                raise harness.HarnessFailure(f"unit {evaluation.unit_key} missing from dataset")
            executor = harness.SCENARIO_EXECUTORS[evaluation.scenario]
            outcome = executor(
                session, StorageAdapter(), evaluation.workspace_id, evaluation.project_id, unit
            )
            evaluation.brief_version_id = uuid.UUID(outcome["brief_version_id"])
            evaluation.blueprint_version_id = uuid.UUID(outcome["blueprint_version_id"])
            evaluation.run_ids_json = json.dumps(outcome["run_ids"])
            session.commit()

            results = criteria.evaluate_pass(session, evaluation, outcome.get("observation"))
            for result in results:
                session.add(
                    TechnicalEvaluationResult(
                        evaluation_id=evaluation.id,
                        criterion_key=result.criterion_key,
                        classification=result.classification,
                        outcome=result.outcome,
                        measured_json=(
                            json.dumps(result.measured, ensure_ascii=False)
                            if result.measured is not None
                            else None
                        ),
                        evidence_json=json.dumps(result.evidence, ensure_ascii=False),
                    )
                )
            evaluation.overall_outcome = criteria.overall_outcome(results)
            evaluation.status = "completed"
            evaluation.completed_at = utcnow()
            session.commit()
            return evaluation.status
        except ModelProviderError as error:
            evaluation.status = "provider_unavailable"
            evaluation.failure_reason = f"provider unavailable during evaluation: {error}"
            evaluation.completed_at = utcnow()
            session.commit()
            return evaluation.status
        except Exception as error:  # noqa: BLE001 - harness settles failed with the reason
            session.rollback()
            evaluation = session.get(TechnicalEvaluation, evaluation_id)
            frames = " <- ".join(
                f"{frame.filename.rsplit('/', 1)[-1]}:{frame.lineno}"
                for frame in (__import__("traceback").extract_tb(error.__traceback__) or [])[-4:]
            )
            evaluation.status = "failed"
            evaluation.failure_reason = f"{type(error).__name__}: {error} [{frames}]"
            evaluation.completed_at = utcnow()
            session.commit()
            return evaluation.status


def _results_of(session: Session, evaluation_id: uuid.UUID) -> list[TechnicalEvaluationResult]:
    return session.scalars(
        select(TechnicalEvaluationResult)
        .where(TechnicalEvaluationResult.evaluation_id == evaluation_id)
        .order_by(TechnicalEvaluationResult.criterion_key)
    ).all()


def _pass_out(evaluation: TechnicalEvaluation, results) -> dict:
    return {
        "evaluation_id": str(evaluation.id),
        "unit_key": evaluation.unit_key,
        "pass_index": evaluation.pass_index,
        "mode": evaluation.mode,
        "scenario": evaluation.scenario,
        "status": evaluation.status,
        "overall_outcome": evaluation.overall_outcome,
        "failure_reason": evaluation.failure_reason,
        "dataset_revision": evaluation.dataset_revision,
        "model_config": json.loads(evaluation.model_config_json),
        "memory_state": json.loads(evaluation.memory_state_json),
        "brief_version_id": (
            str(evaluation.brief_version_id) if evaluation.brief_version_id else None
        ),
        "blueprint_version_id": (
            str(evaluation.blueprint_version_id) if evaluation.blueprint_version_id else None
        ),
        "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None,
        "criteria": [
            {
                "criterion_key": row.criterion_key,
                "classification": row.classification,
                "outcome": row.outcome,
                "measured": json.loads(row.measured_json) if row.measured_json else None,
                "evidence": json.loads(row.evidence_json),
            }
            for row in results
        ],
    }


def evaluation_overview(session: Session, project_id: uuid.UUID) -> dict:
    try:
        current_revision = load_dataset().revision
    except DatasetGovernanceError as error:
        return {"dataset_revision": None, "dataset_governance_error": str(error), "passes": []}
    evaluations = session.scalars(
        select(TechnicalEvaluation)
        .where(TechnicalEvaluation.project_id == project_id)
        .order_by(
            TechnicalEvaluation.unit_key,
            TechnicalEvaluation.pass_index,
            TechnicalEvaluation.scenario,
        )
    ).all()
    passes = []
    for evaluation in evaluations:
        entry = _pass_out(evaluation, _results_of(session, evaluation.id))
        entry["superseded_configuration"] = evaluation.dataset_revision != current_revision
        passes.append(entry)
    return {"dataset_revision": current_revision, "passes": passes}


def evaluation_detail(
    session: Session, project_id: uuid.UUID, evaluation_id: uuid.UUID
) -> dict | None:
    evaluation = session.get(TechnicalEvaluation, evaluation_id)
    if evaluation is None or evaluation.project_id != project_id:
        return None
    return _pass_out(evaluation, _results_of(session, evaluation.id))


def _config_signature(entry: dict) -> str:
    # F013 D6: the memory-set snapshot joins the model-config signature so
    # passes with different memory state never compare silently.
    return json.dumps(
        {
            "model_config": entry.get("model_config"),
            "memory_state": entry.get("memory_state"),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def _product_validation_status(session, project_id) -> str:
    """F010: live product-validation status derived from recorded assignments
    (Spec D6/D7); lazy import keeps the module boundary acyclic."""
    from lessoncanvas.modules.product_validation import service as pv_service

    return pv_service.derive_overall_status(session, project_id)


def evaluation_report(session: Session, project_id: uuid.UUID) -> dict:
    overview = evaluation_overview(session, project_id)
    passes = overview["passes"]
    completed_full = [
        entry
        for entry in passes
        if entry["scenario"] == "full_pipeline" and entry["status"] == "completed"
    ]

    comparisons = []
    for entry in passes:
        if entry["scenario"] != "full_pipeline":
            continue
        comparable = [
            other
            for other in completed_full
            if other["unit_key"] == entry["unit_key"]
            and other["pass_index"] != entry["pass_index"]
            and other["dataset_revision"] == entry["dataset_revision"]
            and _config_signature(other) == _config_signature(entry)
        ]
        reason = None
        if not comparable:
            same_unit = [other for other in passes if other["unit_key"] == entry["unit_key"]]
            others = [other for other in same_unit if other["pass_index"] != entry["pass_index"]]
            differing = [
                other
                for other in others
                if other["dataset_revision"] != entry["dataset_revision"]
                or _config_signature(other) != _config_signature(entry)
            ]
            if differing:
                reason = "不同数据集版本或模型配置"
            elif not others:
                reason = "该单元仅有此一遍"
            else:
                reason = "对比数据不足"
        comparisons.append(
            {
                "evaluation_id": entry["evaluation_id"],
                "unit_key": entry["unit_key"],
                "pass_index": entry["pass_index"],
                "comparison_available": bool(comparable),
                "comparison_unavailable_reason": reason,
                "comparable_pass_indexes": sorted({other["pass_index"] for other in comparable}),
            }
        )

    blocking_outcomes: dict[str, set[str]] = {}
    for entry in passes:
        for criterion in entry["criteria"]:
            if criterion["classification"] != criteria.BLOCKING:
                continue
            blocking_outcomes.setdefault(criterion["criterion_key"], set()).add(
                criterion["outcome"] or "missing_evidence"
            )
    all_outcomes = {value for values in blocking_outcomes.values() for value in values}
    if not blocking_outcomes:
        set_outcome = None
    elif "fail" in all_outcomes:
        set_outcome = "fail"
    elif not ALL_BLOCKING_KEYS.issubset(set(blocking_outcomes)) or (
        "missing_evidence" in all_outcomes
    ):
        set_outcome = "missing_evidence"
    else:
        set_outcome = "pass"

    return {
        "dataset_revision": overview["dataset_revision"],
        "dataset_governance_error": overview.get("dataset_governance_error"),
        "passes": passes,
        "comparisons": comparisons,
        "blocking_criterion_outcomes": {
            key: sorted(values) for key, values in sorted(blocking_outcomes.items())
        },
        "overall_outcome": set_outcome,
        "product_validation_status": _product_validation_status(session, project_id),
        "technical_note": (
            "技术评估与教师产品验证为两个独立状态；技术结果不代表课堂可用性，"
            "产品验证以外部教师评审证据为准。"
        ),
    }

"""F009 technical-evaluation API: owner-authorized overview, idempotent pass
creation, per-pass detail with criterion evidence, and the report read model."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, RequirementError
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)
from lessoncanvas.modules.technical_evaluation import service

router = APIRouter(
    prefix="/projects/{project_id}/technical-evaluation", tags=["technical-evaluation"]
)


def _owned(session, workspace, project_id: uuid.UUID):
    try:
        return get_owned_project(session, workspace, project_id)
    except ServiceNotFound as error:
        raise NotFoundError("project not found") from error


class CriterionOut(BaseModel):
    criterion_key: str
    classification: str
    outcome: str | None
    measured: dict | None
    evidence: dict


class EvaluationPassOut(BaseModel):
    # `model_config` is Pydantic's protected namespace, so the configuration
    # snapshot field carries the wire name through an alias.
    model_config = ConfigDict(populate_by_name=True)

    evaluation_id: str
    unit_key: str
    pass_index: int
    mode: str
    scenario: str
    status: str
    overall_outcome: str | None
    failure_reason: str | None
    dataset_revision: str
    superseded_configuration: bool = False
    model_configuration: dict = Field(alias="model_config")
    memory_state: dict
    brief_version_id: str | None
    blueprint_version_id: str | None
    created_at: datetime | None
    completed_at: datetime | None
    criteria: list[CriterionOut]


class OverviewOut(BaseModel):
    dataset_revision: str | None
    dataset_governance_error: str | None = None
    passes: list[EvaluationPassOut]


class CreateEvaluationIn(BaseModel):
    unit_key: str
    pass_index: int
    mode: Literal["live", "deterministic"]
    scenario: str = "full_pipeline"


class CreateEvaluationOut(BaseModel):
    evaluation: EvaluationPassOut
    created: bool


class ReportOut(BaseModel):
    dataset_revision: str | None
    dataset_governance_error: str | None
    passes: list[EvaluationPassOut]
    comparisons: list[dict[str, Any]]
    blocking_criterion_outcomes: dict[str, list[str]]
    overall_outcome: str | None
    product_validation_status: str
    technical_note: str


def _pass_payload(entry: dict) -> EvaluationPassOut:
    return EvaluationPassOut(
        **{
            **entry,
            "criteria": [CriterionOut(**item) for item in entry["criteria"]],
        }
    )


@router.get("", response_model=OverviewOut)
def overview(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> OverviewOut:
    _owned(session, workspace, project_id)
    data = service.evaluation_overview(session, project_id)
    return OverviewOut(
        dataset_revision=data["dataset_revision"],
        dataset_governance_error=data.get("dataset_governance_error"),
        passes=[_pass_payload(entry) for entry in data["passes"]],
    )


@router.post("/runs", response_model=CreateEvaluationOut, status_code=201)
def create_run(
    project_id: uuid.UUID,
    body: CreateEvaluationIn,
    workspace: WorkspaceDep,
    session: SessionDep,
) -> CreateEvaluationOut:
    _owned(session, workspace, project_id)
    try:
        evaluation, created = service.create_evaluation(
            session,
            workspace,
            project_id,
            body.unit_key,
            body.pass_index,
            body.mode,
            body.scenario,
        )
    except service.EvaluationRequirementError as error:
        session.rollback()
        raise RequirementError(error.message, error.details) from error
    data = service.evaluation_detail(session, project_id, evaluation.id) or {}
    return CreateEvaluationOut(evaluation=_pass_payload(data), created=created)


@router.get("/runs/{evaluation_id}", response_model=EvaluationPassOut)
def run_detail(
    project_id: uuid.UUID, evaluation_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
) -> EvaluationPassOut:
    _owned(session, workspace, project_id)
    data = service.evaluation_detail(session, project_id, evaluation_id)
    if data is None:
        raise NotFoundError("evaluation not found")
    return _pass_payload(data)


@router.get("/report", response_model=ReportOut)
def report(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> ReportOut:
    _owned(session, workspace, project_id)
    data = service.evaluation_report(session, project_id)
    return ReportOut(
        dataset_revision=data["dataset_revision"],
        dataset_governance_error=data.get("dataset_governance_error"),
        passes=[_pass_payload(entry) for entry in data["passes"]],
        comparisons=data["comparisons"],
        blocking_criterion_outcomes=data["blocking_criterion_outcomes"],
        overall_outcome=data["overall_outcome"],
        product_validation_status=data["product_validation_status"],
        technical_note=data["technical_note"],
    )

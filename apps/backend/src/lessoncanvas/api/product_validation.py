"""F010 product-validation API: owner-authorized assignment fixing,
structured rubric-evidence import with the original document, not-complete
conclusion, and overview/detail reads. Zero model calls (Spec D3/D7)."""

import json
import uuid
from types import SimpleNamespace

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from lessoncanvas.adapters.storage import StorageAdapter
from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, RequirementError
from lessoncanvas.models import ProductValidationEvidence
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project
from lessoncanvas.modules.product_validation import service
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/projects/{project_id}/product-validation", tags=["product-validation"])

MIN_NOT_COMPLETE_REASON_LENGTH = 5


def _owned(session, workspace, project_id: uuid.UUID):
    try:
        return get_owned_project(session, workspace, project_id)
    except ServiceNotFound as error:
        raise NotFoundError("project not found") from error


def _requirement(error: service.ProductValidationError) -> RequirementError:
    return RequirementError(error.message, error.details)


class AssignmentCreateIn(BaseModel):
    unit_key: str = Field(min_length=1, max_length=64)


class AssignmentOut(BaseModel):
    id: str
    unit_key: str
    dataset_revision: str
    rubric_revision: str
    state: str
    staleness: dict | None = None
    not_complete_reason: str | None = None
    outcome: str | None = None
    outcome_detail: dict | None = None
    created: bool = True
    created_at: str
    concluded_at: str | None = None


class EvidenceOut(BaseModel):
    id: str
    assignment_id: str
    evidence_revision: str
    status: str
    capture_channel: str
    outcome: str
    outcome_detail: dict
    created: bool
    created_at: str


class ConclusionIn(BaseModel):
    reason: str = Field(min_length=MIN_NOT_COMPLETE_REASON_LENGTH)


def _overview_row(session, assignment) -> dict:
    for row in service.overview(session, assignment.project_id)["assignments"]:
        if row["id"] == str(assignment.id):
            return row
    raise NotFoundError("assignment not found")


@router.get("")
def get_overview(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    _owned(session, workspace, project_id)
    return service.overview(session, project_id)


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(
    project_id: uuid.UUID,
    payload: AssignmentCreateIn,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _owned(session, workspace, project_id)
    try:
        assignment, created = service.create_assignment(
            session, workspace, project_id, payload.unit_key
        )
    except service.ProductValidationError as error:
        raise _requirement(error) from error
    row = _overview_row(session, assignment)
    row["created"] = created
    return row


@router.get("/assignments/{assignment_id}")
def get_assignment_detail(
    project_id: uuid.UUID, assignment_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
):
    _owned(session, workspace, project_id)
    try:
        return service.detail(session, project_id, assignment_id)
    except service.AssignmentNotFoundError as error:
        raise NotFoundError("assignment not found") from error


@router.post("/assignments/{assignment_id}/evidence", response_model=EvidenceOut, status_code=201)
async def import_evidence(
    project_id: uuid.UUID,
    assignment_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    evidence_revision: str = Form(...),
    evidence: str = Form(...),
    document: UploadFile = ...,
):
    """Import the evaluator's completed rubric evidence (multipart): the
    submission revision label, the rubric payload as JSON, and the original
    completed document. Idempotent per (assignment, evidence revision)."""

    _owned(session, workspace, project_id)
    try:
        payload = json.loads(evidence)
    except json.JSONDecodeError as error:
        raise RequirementError(
            "rubric evidence must be a JSON object",
            {"field": "evidence", "violations": ["evidence: invalid JSON"]},
        ) from error
    if not isinstance(payload, dict):
        raise RequirementError(
            "rubric evidence must be a JSON object",
            {"field": "evidence", "violations": ["evidence: must be a JSON object"]},
        )

    incoming = SimpleNamespace(
        filename=document.filename,
        content_type=document.content_type,
        data=await document.read(),
    )
    try:
        row, created = service.import_evidence(
            session,
            workspace,
            project_id,
            assignment_id,
            evidence_revision,
            payload,
            incoming,
        )
    except service.ProductValidationError as error:
        raise _requirement(error) from error
    except service.AssignmentNotFoundError as error:
        raise NotFoundError("assignment not found") from error
    return EvidenceOut(
        id=str(row.id),
        assignment_id=str(assignment_id),
        evidence_revision=row.evidence_revision,
        status=row.status,
        capture_channel=row.capture_channel,
        outcome=row.outcome,
        outcome_detail=json.loads(row.outcome_json),
        created=created,
        created_at=row.created_at.isoformat(),
    )


@router.post(
    "/assignments/{assignment_id}/conclusion", response_model=AssignmentOut, status_code=200
)
def conclude_not_complete(
    project_id: uuid.UUID,
    assignment_id: uuid.UUID,
    payload: ConclusionIn,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    """Conclude an assignment the evaluator cannot complete, recording the
    honest reason (Spec D9 fallback)."""

    _owned(session, workspace, project_id)
    try:
        assignment = service.conclude_not_complete(
            session, workspace, project_id, assignment_id, payload.reason
        )
    except service.ProductValidationError as error:
        raise _requirement(error) from error
    except service.AssignmentNotFoundError as error:
        raise NotFoundError("assignment not found") from error
    return _overview_row(session, assignment)


@router.get("/assignments/{assignment_id}/evidence/{evidence_id}/document")
def download_evidence_document(
    project_id: uuid.UUID,
    assignment_id: uuid.UUID,
    evidence_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    """Owner-authorized download of the evaluator's original document (Spec
    D4: private evidence; never surfaced on public or report reads)."""

    _owned(session, workspace, project_id)
    try:
        service.detail(session, project_id, assignment_id)
    except service.AssignmentNotFoundError as error:
        raise NotFoundError("assignment not found") from error
    row = session.scalars(
        select(ProductValidationEvidence).where(
            ProductValidationEvidence.id == evidence_id,
            ProductValidationEvidence.assignment_id == assignment_id,
        )
    ).first()
    if row is None or not row.document_object_key:
        raise NotFoundError("evidence document not found")
    storage = StorageAdapter(bucket=get_settings().s3_bucket_artifacts)
    try:
        content = storage.get(row.document_object_key)
    except Exception as error:
        raise NotFoundError("evidence document not found") from error
    return Response(
        content=content,
        media_type=row.document_content_type or "application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="rubric-evidence"'},
    )

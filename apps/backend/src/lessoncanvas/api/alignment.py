"""F008 alignment API: deterministic alignment view for the current confirmed
version pair, printable-report data, and owner-authorized reasoned overrides
for disputed conflict-class severe findings (Spec D1/D2/D6)."""

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, RequirementError, StaleVersionError
from lessoncanvas.models import AlignmentOverride, AuditEvent, utcnow
from lessoncanvas.modules.alignment_evaluation import service as alignment_service
from lessoncanvas.modules.alignment_evaluation.service import PRODUCT_VALIDATION_STATUS
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project

router = APIRouter(prefix="/projects/{project_id}/alignment", tags=["alignment"])

MIN_REASON_LENGTH = 10


class OverrideIn(BaseModel):
    finding_key: str
    reason: str = Field(min_length=MIN_REASON_LENGTH)
    brief_version: int | None = None
    blueprint_version: int | None = None


class OverrideOut(BaseModel):
    id: str
    finding_key: str
    reason: str
    status: str
    created_at: str
    withdrawn_at: str | None = None


def _owned(session, workspace, project_id) -> None:
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


def _alignment_or_422(session, project_id: uuid.UUID) -> dict:
    try:
        return alignment_service.compute_alignment(session, project_id)
    except alignment_service.MissingPairError as err:
        raise RequirementError(
            "confirmed brief and blueprint versions are required before alignment review",
            {"gate": "confirmed_pair"},
        ) from err


@router.get("")
def get_alignment(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    _owned(session, workspace, project_id)
    return _alignment_or_422(session, project_id)


@router.get("/report")
def get_report(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    _owned(session, workspace, project_id)
    alignment = _alignment_or_422(session, project_id)
    alignment["generated_at"] = utcnow().isoformat()
    alignment["product_validation_status"] = PRODUCT_VALIDATION_STATUS
    return alignment


@router.post("/overrides", response_model=OverrideOut, status_code=201)
def record_override(
    project_id: uuid.UUID,
    payload: OverrideIn,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _owned(session, workspace, project_id)
    alignment = _alignment_or_422(session, project_id)

    if payload.brief_version is not None and payload.brief_version != alignment["brief_version"]:
        raise StaleVersionError(
            "brief version changed; refresh and re-decide on the current version",
            {
                "current_brief_version": alignment["brief_version"],
                "current_blueprint_version": alignment["blueprint_version"],
            },
        )
    if (
        payload.blueprint_version is not None
        and payload.blueprint_version != alignment["blueprint_version"]
    ):
        raise StaleVersionError(
            "blueprint version changed; refresh and re-decide on the current version",
            {
                "current_brief_version": alignment["brief_version"],
                "current_blueprint_version": alignment["blueprint_version"],
            },
        )

    finding = next(
        (item for item in alignment["findings"] if item["key"] == payload.finding_key), None
    )
    if finding is None:
        raise RequirementError(
            "finding not found in the current alignment state", {"finding_key": payload.finding_key}
        )
    if finding["severity"] != "severe" or finding["kind"] != "conflict":
        raise RequirementError(
            "only disputed conflict-class severe findings may be overridden",
            {"finding_key": payload.finding_key, "kind": finding["kind"]},
        )
    if not finding["overridable"]:
        raise RequirementError(
            "this finding is not eligible for override; correct or regenerate instead",
            {"finding_key": payload.finding_key},
        )

    existing = next(
        (
            row
            for row in alignment["overrides"]
            if row["finding_key"] == payload.finding_key and row["status"] == "recorded"
        ),
        None,
    )
    if existing is not None:
        return OverrideOut(**existing)

    override = AlignmentOverride(
        project_id=project_id,
        workspace_id=workspace.id,
        brief_version_id=uuid.UUID(alignment["brief_version_id"]),
        blueprint_version_id=uuid.UUID(alignment["blueprint_version_id"]),
        finding_key=payload.finding_key,
        reason=payload.reason,
        created_by=workspace.clerk_user_id,
    )
    session.add(override)
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor=workspace.clerk_user_id,
            action="alignment.override.recorded",
            target_type="alignment_finding",
            target_id=payload.finding_key,
        )
    )
    session.commit()
    session.refresh(override)
    return OverrideOut(
        id=str(override.id),
        finding_key=override.finding_key,
        reason=override.reason,
        status=override.status,
        created_at=override.created_at.isoformat(),
        withdrawn_at=None,
    )


@router.delete("/overrides/{override_id}", response_model=OverrideOut)
def withdraw_override(
    project_id: uuid.UUID,
    override_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _owned(session, workspace, project_id)
    override = session.scalar(
        select(AlignmentOverride).where(
            AlignmentOverride.id == override_id,
            AlignmentOverride.project_id == project_id,
        )
    )
    if override is None:
        raise NotFoundError("override not found")
    if override.status != "withdrawn":
        override.status = "withdrawn"
        override.withdrawn_at = utcnow()
        session.add(
            AuditEvent(
                workspace_id=workspace.id,
                actor=workspace.clerk_user_id,
                action="alignment.override.withdrawn",
                target_type="alignment_finding",
                target_id=override.finding_key,
            )
        )
        session.commit()
        session.refresh(override)
    return OverrideOut(
        id=str(override.id),
        finding_key=override.finding_key,
        reason=override.reason,
        status=override.status,
        created_at=override.created_at.isoformat(),
        withdrawn_at=override.withdrawn_at.isoformat() if override.withdrawn_at else None,
    )

"""F007 version-transition API: pre-confirmation impact preview and the
current-transition comparison payload. Owner-authorized, read-only."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, RequirementError
from lessoncanvas.models import BlueprintDraft, BlueprintVersion, BriefDraft, BriefVersion
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project
from lessoncanvas.modules.run_orchestration import transition
from lessoncanvas.modules.run_orchestration.impact import compute_impact

router = APIRouter(prefix="/projects/{project_id}", tags=["versions"])


def _owned(session, workspace, project_id) -> None:
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


@router.get("/impact")
def impact(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> dict:
    """D1-matrix impact preview for the current drafts vs the confirmed pair."""

    _owned(session, workspace, project_id)
    brief = session.scalar(
        select(BriefVersion)
        .where(BriefVersion.project_id == project_id)
        .order_by(BriefVersion.version.desc())
    )
    blueprint = session.scalar(
        select(BlueprintVersion)
        .where(BlueprintVersion.project_id == project_id)
        .order_by(BlueprintVersion.version.desc())
    )
    if brief is None or blueprint is None:
        raise RequirementError(
            "a confirmed brief and blueprint are required before impact preview",
            {"gate": "blueprint"},
        )
    brief_draft = session.scalar(
        select(BriefDraft)
        .where(BriefDraft.project_id == project_id)
        .order_by(BriefDraft.revision.desc())
    )
    blueprint_draft = session.scalar(
        select(BlueprintDraft)
        .where(BlueprintDraft.project_id == project_id)
        .order_by(BlueprintDraft.revision.desc())
    )
    new_brief_fields = brief_draft.fields_json if brief_draft is not None else brief.fields_json
    new_blueprint_payload = (
        blueprint_draft.payload_json if blueprint_draft is not None else blueprint.payload_json
    )
    return compute_impact(
        brief.fields_json,
        new_brief_fields,
        blueprint.payload_json,
        new_blueprint_payload,
    )


@router.get("/versions/current-transition")
def current_transition(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> dict:
    _owned(session, workspace, project_id)
    return transition.current_transition(session, project_id)

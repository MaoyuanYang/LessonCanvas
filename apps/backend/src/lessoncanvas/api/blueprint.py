import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, RequirementError, StaleVersionError
from lessoncanvas.modules.discovery_planning import blueprint as blueprint_service
from lessoncanvas.modules.discovery_planning.blueprint import (
    ChecksFailedError,
    FindingDecisionError,
    StaleBriefError,
    StaleRevisionError,
    UndecidedFindingsError,
)
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)

router = APIRouter(prefix="/projects/{project_id}/blueprint", tags=["blueprint"])


class BlueprintOut(BaseModel):
    available: bool
    draft_revision: int | None
    draft: dict | None
    checks: list[dict]
    findings: list[dict]
    confirmed_version: int | None
    confirmed_payload: dict | None
    confirmed_stale: bool | None
    stale: bool
    brief_diff: list[dict] | None
    impact_summary: dict | None


class DraftPatch(BaseModel):
    payload: dict
    base_revision: int


class DecisionIn(BaseModel):
    finding_id: str
    reason: str
    base_revision: int


class ConfirmIn(BaseModel):
    base_revision: int


class ConfirmOut(BaseModel):
    version: int
    payload: dict


def _owned(session, workspace, project_id, *, sample_read: bool = False):
    try:
        get_owned_project(session, workspace, project_id, allow_sample_read=sample_read)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


def _stale_guard(function):
    try:
        return function()
    except StaleRevisionError as err:
        raise StaleVersionError("a newer draft revision exists") from err
    except StaleBriefError as err:
        raise RequirementError(
            "blueprint is bound to an older confirmed brief version", {"stale_brief": True}
        ) from err
    except ServiceNotFound as err:
        raise NotFoundError(err.args[0] if err.args else "resource not found") from err


@router.get("", response_model=BlueprintOut)
def get_blueprint(
    project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep
) -> BlueprintOut:
    _owned(session, workspace, project_id, sample_read=True)
    blueprint_service.sync_draft_from_run_guarded(session, workspace.id, project_id)
    session.commit()
    return BlueprintOut(**blueprint_service.get_blueprint(session, workspace.id, project_id))


@router.patch("/draft", response_model=BlueprintOut)
def patch_draft(
    project_id: uuid.UUID, body: DraftPatch, workspace: WorkspaceDep, session: SessionDep
) -> BlueprintOut:
    _owned(session, workspace, project_id)
    blueprint_service.sync_draft_from_run_guarded(session, workspace.id, project_id)
    session.commit()

    def apply():
        return blueprint_service.patch_draft(
            session, workspace.id, project_id, body.payload, body.base_revision
        )

    _stale_guard(apply)
    session.commit()
    return BlueprintOut(**blueprint_service.get_blueprint(session, workspace.id, project_id))


@router.post("/decisions", response_model=BlueprintOut)
def record_decision(
    project_id: uuid.UUID, body: DecisionIn, workspace: WorkspaceDep, session: SessionDep
) -> BlueprintOut:
    _owned(session, workspace, project_id)
    blueprint_service.sync_draft_from_run_guarded(session, workspace.id, project_id)
    session.commit()
    if not body.reason.strip():
        raise RequirementError("a decision reason is required", {"field": "reason"})

    def apply():
        return blueprint_service.record_decision(
            session, workspace.id, project_id, body.finding_id, body.reason, body.base_revision
        )

    try:
        _stale_guard(apply)
    except FindingDecisionError as err:
        session.rollback()
        raise RequirementError(str(err), {"finding": body.finding_id}) from err
    session.commit()
    return BlueprintOut(**blueprint_service.get_blueprint(session, workspace.id, project_id))


@router.post("/confirm", response_model=ConfirmOut)
def confirm(
    project_id: uuid.UUID, body: ConfirmIn, workspace: WorkspaceDep, session: SessionDep
) -> ConfirmOut:
    _owned(session, workspace, project_id)
    blueprint_service.sync_draft_from_run_guarded(session, workspace.id, project_id)
    session.commit()

    def apply():
        return blueprint_service.confirm_blueprint(
            session, workspace.id, project_id, body.base_revision
        )

    try:
        version = _stale_guard(apply)
    except ChecksFailedError as err:
        session.rollback()
        raise RequirementError(
            "blueprint completeness checks failed",
            {"failed_checks": [check["id"] for check in err.failed], "checks": err.failed},
        ) from err
    except UndecidedFindingsError as err:
        session.rollback()
        raise RequirementError(
            "waivable findings require a fix or a recorded decision",
            {"undecided_findings": err.findings},
        ) from err
    session.commit()
    import json

    # F013 D3: confirmed blueprint is proposal evidence; the pass is
    # idempotent per (workspace, blueprint version) and best-effort.
    from lessoncanvas.modules.teacher_memory.service import schedule_pass

    schedule_pass(session, workspace.id, "blueprint_confirm", version.id)
    return ConfirmOut(version=version.version, payload=json.loads(version.payload_json))

import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, ProviderTransientError, QuotaExceededError
from lessoncanvas.modules.discovery_planning import service
from lessoncanvas.modules.discovery_planning.graph import RunQuotaError
from lessoncanvas.modules.discovery_planning.service import ProviderFailureError
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)

router = APIRouter(prefix="/projects/{project_id}/discovery", tags=["discovery"])


class DiscoveryOut(BaseModel):
    run_id: str
    status: str
    round_count: int
    questions: list[dict]
    draft: dict | None


class AnswersIn(BaseModel):
    answers: dict


def _run_or_404(session, workspace, project_id):
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


@router.post("/start", response_model=DiscoveryOut)
def start(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> DiscoveryOut:
    _run_or_404(session, workspace, project_id)
    try:
        service.start_discovery(session, workspace.id, project_id)
    except ProviderFailureError as err:
        raise ProviderTransientError("model provider unavailable") from err
    except RunQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return DiscoveryOut(**service.discovery_status(session, project_id))


@router.get("", response_model=DiscoveryOut)
def status(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> DiscoveryOut:
    _run_or_404(session, workspace, project_id)
    try:
        return DiscoveryOut(**service.discovery_status(session, project_id))
    except ServiceNotFound as err:
        raise NotFoundError("discovery run not found") from err


@router.post("/answers", response_model=DiscoveryOut)
def answers(
    project_id: uuid.UUID, body: AnswersIn, workspace: WorkspaceDep, session: SessionDep
) -> DiscoveryOut:
    _run_or_404(session, workspace, project_id)
    try:
        service.submit_answers(session, project_id, body.answers)
    except ProviderFailureError as err:
        raise ProviderTransientError("model provider unavailable") from err
    except RunQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return DiscoveryOut(**service.discovery_status(session, project_id))


@router.post("/retry", response_model=DiscoveryOut)
def retry(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> DiscoveryOut:
    _run_or_404(session, workspace, project_id)
    try:
        service.retry_discovery(session, project_id)
    except ProviderFailureError as err:
        raise ProviderTransientError("model provider unavailable") from err
    except RunQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return DiscoveryOut(**service.discovery_status(session, project_id))

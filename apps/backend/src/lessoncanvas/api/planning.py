import json
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError, ProviderTransientError, QuotaExceededError
from lessoncanvas.api.errors import RequirementError as ApiRequirementError
from lessoncanvas.modules.discovery_planning import planning as planning_service
from lessoncanvas.modules.discovery_planning.blueprint import current_brief_version
from lessoncanvas.modules.discovery_planning.narration import (
    NarrationQuotaError,
    get_narration,
    request_stop,
    start_narration,
)
from lessoncanvas.modules.discovery_planning.planning import (
    PlanningQuotaError,
    ProviderFailureError,
)
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)

router = APIRouter(prefix="/projects/{project_id}/planning", tags=["planning"])


class PlanningOut(BaseModel):
    run_id: str
    status: str
    round_count: int
    questions: list[dict]
    draft: dict | None


class AnswersIn(BaseModel):
    answers: dict


class NarrateIn(BaseModel):
    text: str = "请叙述下一步规划。"


def _owned(session, workspace, project_id):
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


def _run_or_404(session, workspace, project_id):
    _owned(session, workspace, project_id)
    try:
        return planning_service.get_planning_run_or_raise(session, project_id)
    except KeyError as err:
        raise NotFoundError("planning run not found") from err


@router.post("/start", response_model=PlanningOut)
def start(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> PlanningOut:
    _owned(session, workspace, project_id)
    brief_version = current_brief_version(session, project_id)
    if brief_version is None:
        raise ApiRequirementError(
            "a confirmed brief is required before planning", {"gate": "brief"}
        )
    try:
        planning_service.start_planning(session, workspace.id, project_id, brief_version.id)
    except ProviderFailureError as err:
        raise ProviderTransientError("model provider unavailable") from err
    except PlanningQuotaError as err:
        raise QuotaExceededError("planning run quota exhausted") from err
    return PlanningOut(**planning_service.planning_status(session, project_id))


@router.get("", response_model=PlanningOut)
def status(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> PlanningOut:
    _run_or_404(session, workspace, project_id)
    return PlanningOut(**planning_service.planning_status(session, project_id))


@router.post("/answers", response_model=PlanningOut)
def answers(
    project_id: uuid.UUID, body: AnswersIn, workspace: WorkspaceDep, session: SessionDep
) -> PlanningOut:
    _run_or_404(session, workspace, project_id)
    try:
        planning_service.submit_planning_answers(session, project_id, body.answers)
    except ProviderFailureError as err:
        raise ProviderTransientError("model provider unavailable") from err
    return PlanningOut(**planning_service.planning_status(session, project_id))


@router.post("/retry", response_model=PlanningOut)
def retry(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> PlanningOut:
    _run_or_404(session, workspace, project_id)
    try:
        planning_service.retry_planning(session, project_id)
    except ProviderFailureError as err:
        raise ProviderTransientError("model provider unavailable") from err
    return PlanningOut(**planning_service.planning_status(session, project_id))


@router.post("/narrate", status_code=202)
def narrate(project_id: uuid.UUID, body: NarrateIn, workspace: WorkspaceDep, session: SessionDep):
    run = _run_or_404(session, workspace, project_id)
    try:
        start_narration(str(run.id), body.text)
    except NarrationQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return {"run_id": str(run.id), "started": True}


@router.post("/reask", status_code=202)
def reask(project_id: uuid.UUID, body: NarrateIn, workspace: WorkspaceDep, session: SessionDep):
    run = _run_or_404(session, workspace, project_id)
    try:
        start_narration(str(run.id), body.text)
    except NarrationQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return {"run_id": str(run.id), "started": True}


@router.post("/stop-narration")
def stop_narration(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    run = _run_or_404(session, workspace, project_id)
    stopped = request_stop(str(run.id))
    return {"stopped": stopped}


@router.get("/stream")
def stream(
    project_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
):
    run = _run_or_404(session, workspace, project_id)
    run_id = str(run.id)

    def event_stream():
        state = get_narration(run_id)
        index = offset
        if state is not None:
            while True:
                with state.condition:
                    tokens = list(state.tokens)
                    stop_requested = state.stop_requested
                    complete = state.complete
                    if len(tokens) <= index and not complete and not stop_requested:
                        state.condition.wait(timeout=0.5)
                        continue
                while index < len(tokens):
                    yield _sse("token", {"i": index, "t": tokens[index]})
                    index += 1
                if stop_requested:
                    yield _sse("stopped", {"i": index})
                    return
                if complete:
                    yield _sse("complete", {"i": index, "text": "".join(tokens)})
                    return
        else:
            from sqlalchemy import select

            from lessoncanvas.models import InteractionMessage

            message = session.scalar(
                select(InteractionMessage)
                .where(InteractionMessage.run_id == run.id, InteractionMessage.role == "agent")
                .order_by(InteractionMessage.created_at.desc())
            )
            text = message.content if message else ""
            while index < len(text):
                yield _sse("token", {"i": index, "t": text[index]})
                index += 1
            yield _sse("complete", {"i": index, "text": text})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

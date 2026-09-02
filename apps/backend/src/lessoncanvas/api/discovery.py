import json
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lessoncanvas.api.deps import SessionDep, WorkspaceDep, require_expensive_rate
from lessoncanvas.api.errors import NotFoundError, ProviderTransientError, QuotaExceededError
from lessoncanvas.api.sse_registry import acquire_stream_slot, release_stream_slot
from lessoncanvas.modules.discovery_planning import service
from lessoncanvas.modules.discovery_planning.graph import RunQuotaError
from lessoncanvas.modules.discovery_planning.narration import (
    NarrationQuotaError,
    get_narration,
    request_stop,
    start_narration,
)
from lessoncanvas.modules.discovery_planning.service import ProviderFailureError
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/projects/{project_id}/discovery", tags=["discovery"])


class DiscoveryOut(BaseModel):
    run_id: str
    status: str
    round_count: int
    questions: list[dict]
    draft: dict | None


class AnswersIn(BaseModel):
    answers: dict


def _run_or_404(session, workspace, project_id, *, sample_read: bool = False):
    try:
        get_owned_project(session, workspace, project_id, allow_sample_read=sample_read)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


@router.post("/start", response_model=DiscoveryOut,
             dependencies=[Depends(require_expensive_rate)])
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
    _run_or_404(session, workspace, project_id, sample_read=True)
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


class NarrateIn(BaseModel):
    text: str = "请叙述下一步访谈。"


def _get_run_or_404(session, workspace, project_id, *, sample_read: bool = False):
    from lessoncanvas.modules.discovery_planning.service import get_run_or_raise

    try:
        get_owned_project(session, workspace, project_id, allow_sample_read=sample_read)
        run = get_run_or_raise(session, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("discovery run not found") from err
    return run


@router.post("/narrate", status_code=202)
def narrate(project_id: uuid.UUID, body: NarrateIn, workspace: WorkspaceDep, session: SessionDep):
    run = _get_run_or_404(session, workspace, project_id)
    try:
        start_narration(str(run.id), body.text)
    except NarrationQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return {"run_id": str(run.id), "started": True}


@router.post("/reask", status_code=202)
def reask(project_id: uuid.UUID, body: NarrateIn, workspace: WorkspaceDep, session: SessionDep):
    run = _get_run_or_404(session, workspace, project_id)
    try:
        start_narration(str(run.id), body.text)
    except NarrationQuotaError as err:
        raise QuotaExceededError("model call quota exhausted") from err
    return {"run_id": str(run.id), "started": True}


@router.post("/stop-narration")
def stop_narration(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    run = _get_run_or_404(session, workspace, project_id)
    stopped = request_stop(str(run.id))
    return {"stopped": stopped}


@router.get("/stream")
def stream(
    project_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
):
    run = _get_run_or_404(session, workspace, project_id)
    run_id = str(run.id)

    settings = get_settings()
    acquire_stream_slot(workspace.id, settings.max_concurrent_sse_streams_per_workspace)
    workspace_id = workspace.id

    def event_stream():
        try:
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
                    .where(
                        InteractionMessage.run_id == run.id,
                        InteractionMessage.role == "agent",
                    )
                    .order_by(InteractionMessage.created_at.desc())
                )
                text = message.content if message else ""
                while index < len(text):
                    yield _sse("token", {"i": index, "t": text[index]})
                    index += 1
                yield _sse("complete", {"i": index, "text": text})
        finally:
            release_stream_slot(workspace_id)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

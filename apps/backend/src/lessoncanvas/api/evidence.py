"""F006 evidence API: layered, owner-authorized run evidence — project run
inventory, teacher summary, cursor-paginated technical events, and streamed
explanation narration. Every route is a safe read except narration start/stop,
which change no business state (Spec D5/D8)."""

import json
import time
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from lessoncanvas.api.deps import SessionDep, WorkspaceDep, require_expensive_rate
from lessoncanvas.api.errors import NotFoundError, QuotaExceededError, RequirementError
from lessoncanvas.api.sse_registry import acquire_stream_slot, release_stream_slot
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project
from lessoncanvas.modules.run_orchestration import evidence
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/projects/{project_id}/evidence", tags=["evidence"])


def _owned(session, workspace, project_id, *, sample_read: bool = False) -> None:
    try:
        get_owned_project(session, workspace, project_id, allow_sample_read=sample_read)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


def _resolve_or_404(
    session, workspace, project_id, run_id: uuid.UUID, *, sample_read: bool = False
):
    _owned(session, workspace, project_id, sample_read=sample_read)
    try:
        return evidence.resolve_run(session, project_id, run_id)
    except evidence.RunNotFoundError as err:
        raise NotFoundError("run not found") from err


@router.get("")
def inventory(
    project_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    after: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
):
    _owned(session, workspace, project_id, sample_read=True)
    try:
        return evidence.run_inventory(session, project_id, after_cursor=after, limit=limit)
    except evidence.InvalidEvidenceQueryError as err:
        raise RequirementError(str(err)) from err


@router.get("/{run_id}")
def summary(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _resolve_or_404(session, workspace, project_id, run_id, sample_read=True)
    return evidence.run_summary(session, project_id, run_id)


@router.get("/{run_id}/events")
def events(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    after: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    kind: str | None = Query(default=None),
):
    _resolve_or_404(session, workspace, project_id, run_id)
    try:
        return evidence.evidence_events(
            session, project_id, run_id, after_cursor=after, limit=limit, kind=kind
        )
    except evidence.InvalidEvidenceQueryError as err:
        raise RequirementError(str(err)) from err


@router.post("/{run_id}/narrate", status_code=202,
             dependencies=[Depends(require_expensive_rate)])
def narrate(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _resolve_or_404(session, workspace, project_id, run_id)
    try:
        evidence.start_evidence_narration(session, workspace.id, project_id, run_id)
    except evidence.NarrationQuotaError as err:
        raise QuotaExceededError(
            "evidence narration quota exhausted for this workspace"
        ) from err
    return {"run_id": str(run_id), "started": True}


@router.post("/{run_id}/narrate/stop")
def stop_narration(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
):
    _resolve_or_404(session, workspace, project_id, run_id)
    return {"stopped": evidence.stop_evidence_narration(run_id)}


@router.get("/{run_id}/narrate/stream")
def narration_stream(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
):
    _resolve_or_404(session, workspace, project_id, run_id)
    run_id_str = str(run_id)

    settings = get_settings()
    acquire_stream_slot(workspace.id, settings.max_concurrent_sse_streams_per_workspace)
    workspace_id = workspace.id

    def event_stream():
        try:
            state = evidence.get_evidence_narration(run_id_str)
            index = offset
            if state is not None:
                last_emit = time.monotonic()
                while True:
                    keepalive = False
                    with state.condition:
                        tokens = list(state.tokens)
                        stop_requested = state.stop_requested
                        complete = state.complete
                        if len(tokens) <= index and not complete and not stop_requested:
                            state.condition.wait(timeout=0.5)
                            keepalive = time.monotonic() - last_emit > 5.0
                            if not keepalive:
                                continue
                    if keepalive:
                        last_emit = time.monotonic()
                        # SSE comment keepalive: provider latency before the first
                        # tokens must not let idle-timeout intermediaries drop the
                        # stream (same class as the generation-stream fix, F006).
                        yield ": keepalive\n\n"
                        continue
                    while index < len(tokens):
                        yield _sse("token", {"i": index, "t": tokens[index]})
                        index += 1
                    last_emit = time.monotonic()
                    if stop_requested:
                        yield _sse("stopped", {"i": index})
                        return
                    if complete:
                        if state.error is not None:
                            yield _sse("error", {"message": "model provider unavailable"})
                        else:
                            yield _sse("complete", {"i": index, "text": "".join(tokens)})
                        return
            else:
                text = evidence.last_narration_text(session, run_id) or ""
                while index < len(text):
                    yield _sse("token", {"i": index, "t": text[index]})
                    index += 1
                yield _sse("complete", {"i": index, "text": text})
        finally:
            release_stream_slot(workspace_id)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

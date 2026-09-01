"""F005 exercise-generation API: idempotent start with a required difficulty
tier gated on a complete lesson-plan run, snapshot with pair summaries and the
recorded tier, authoritative SSE with Last-Event-ID replay, scoped resume, and
authorized per-file DOCX download."""

import json
import time
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select as sa_select

from lessoncanvas.api.deps import SessionDep, WorkspaceDep, require_expensive_rate
from lessoncanvas.api.errors import (
    NotFoundError,
    RequirementError,
    StaleVersionError,
)
from lessoncanvas.api.errors import (
    RunAdmissionError as ApiRunAdmissionError,
)
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import ExerciseArtifact, GenerationRun
from lessoncanvas.modules.identity_workspace import service as iw_service
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import get_owned_project
from lessoncanvas.modules.run_orchestration import service as run_service
from lessoncanvas.modules.run_orchestration.schemas import ExerciseGenerationSnapshot
from lessoncanvas.settings import get_settings

router = APIRouter(prefix="/projects/{project_id}/exercises/generation", tags=["exercises"])

TERMINAL_STATUSES = (
    "complete",
    "partial_failure",
    "capped_failure",
    "superseded",
    "terminal_failure",
)
STREAM_POLL_SECONDS = 1.0
STREAM_MAX_SECONDS = 900.0
STREAM_KEEPALIVE_SECONDS = 5.0

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

exercise_router = APIRouter(prefix="/projects/{project_id}/exercises", tags=["exercises"])


class StartRequest(BaseModel):
    difficulty: Literal["foundation", "consolidation", "advanced"]


class ResumeOut(BaseModel):
    status: str


def _owned(session, workspace, project_id) -> None:
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err


def _run_or_404(session, workspace, project_id) -> GenerationRun:
    _owned(session, workspace, project_id)
    run = run_service.current_exercise_run(session, project_id)
    if run is None:
        raise NotFoundError("exercise generation run not found")
    return run


def _snapshot(session, run: GenerationRun) -> ExerciseGenerationSnapshot:
    from lessoncanvas.modules.run_orchestration.schemas import (
        RetainedArtifactOut,
        exercise_artifact_out,
    )

    data = run_service.exercise_run_snapshot(session, run)
    return ExerciseGenerationSnapshot(
        run_id=data["run_id"],
        status=data["status"],
        brief_version=data["brief_version"],
        blueprint_version=data["blueprint_version"],
        language_mode=data["language_mode"],
        difficulty=data["difficulty"],
        scope_lesson_indexes=data["scope_lesson_indexes"],
        retained_artifacts=[RetainedArtifactOut(**entry) for entry in data["retained_artifacts"]],
        model_calls=data["model_calls"],
        model_call_cap=data["model_call_cap"],
        artifacts=[exercise_artifact_out(artifact) for artifact in data["artifacts"]],
        complete_count=data["complete_count"],
        total_count=data["total_count"],
    )


def _dispatch(run: GenerationRun) -> None:
    from lessoncanvas.worker import generate_exercises

    if get_settings().tasks_eager:
        generate_exercises.apply(args=[str(run.id)])
    else:
        generate_exercises.delay(str(run.id))


@router.post("/start", response_model=ExerciseGenerationSnapshot,
             dependencies=[Depends(require_expensive_rate)])
def start(
    project_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    request: StartRequest,
):
    _owned(session, workspace, project_id)
    try:
        run, created = run_service.start_exercise_generation(
            session, workspace.id, project_id, request.difficulty
        )
    except run_service.MissingVersionsError as err:
        raise RequirementError(
            "confirmed brief and blueprint versions are required before exercise generation",
            {"gate": "blueprint"},
        ) from err
    except run_service.PrerequisiteNotMetError as err:
        raise RequirementError(
            "lesson-plan coverage for the current confirmed versions is required before "
            + "exercise generation",
            {
                "gate": "lesson_plans",
                "reason": err.reason,
                "uncovered_lessons": err.uncovered_lessons,
            },
        ) from err
    except run_service.NothingToRegenerateError as err:
        raise RequirementError(
            "the current version transition affects no lessons here; nothing to regenerate",
            {"affected_lessons": []},
        ) from err
    except run_service.RunAdmissionError as err:
        raise ApiRunAdmissionError(
            "workspace concurrent generation limit reached",
            {"limit": err.limit, "active_run_ids": err.active_run_ids},
        ) from err
    session.commit()
    if created:
        _dispatch(run)
        session.refresh(run)
    return _snapshot(session, run)


@router.get("", response_model=ExerciseGenerationSnapshot)
def status(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    run = _run_or_404(session, workspace, project_id)
    return _snapshot(session, run)


@router.post("/resume", response_model=ResumeOut)
def resume(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep):
    run = _run_or_404(session, workspace, project_id)
    try:
        run_service.resume_run(session, run)
    except run_service.ResumeNotAllowedError as err:
        raise StaleVersionError(
            f"resume not allowed from status {err.status}", {"run_status": err.status}
        ) from err
    session.commit()
    _dispatch(run)
    session.refresh(run)
    return ResumeOut(status=run.status)


@router.get("/events")
def events(
    project_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    last_event_id: str | None = Header(default=None),
):
    run = _run_or_404(session, workspace, project_id)
    run_id = str(run.id)
    try:
        cursor = max(int(last_event_id), 0)
    except (TypeError, ValueError):
        cursor = 0

    def event_stream():
        nonlocal cursor
        started = time.monotonic()
        last_emit = started
        while True:
            stream_session = SessionLocal()
            try:
                run_uuid = uuid.UUID(run_id)
                rows = run_service.replay_events(stream_session, run_uuid, after_seq=cursor)
                current = stream_session.get(GenerationRun, run_uuid)
                status_now = current.status if current else "missing_run"
            finally:
                stream_session.close()
            for event in rows:
                cursor = event.seq
                payload = json.loads(event.payload_json)
                data = {
                    "run_id": run_id,
                    "seq": event.seq,
                    "event_type": event.event_type,
                    "payload": payload,
                    "created_at": event.created_at.isoformat(),
                }
                body = json.dumps(data, ensure_ascii=False)
                yield f"id: {event.seq}\nevent: {event.event_type}\ndata: {body}\n\n"
            if rows:
                last_emit = time.monotonic()
            if status_now in TERMINAL_STATUSES and not rows:
                yield "event: end\ndata: {}\n\n"
                return
            if time.monotonic() - last_emit > STREAM_KEEPALIVE_SECONDS:
                last_emit = time.monotonic()
                # SSE comment keepalive (F006; see generation.py for rationale).
                yield ": keepalive\n\n"
            if time.monotonic() - started > STREAM_MAX_SECONDS:
                yield "event: timeout\ndata: {}\n\n"
                return
            time.sleep(STREAM_POLL_SECONDS)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@exercise_router.get("/{artifact_id}/download")
def download(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    workspace: WorkspaceDep,
    session: SessionDep,
    file: Literal["exercise", "answer"] = Query(...),
):
    _owned(session, workspace, project_id)
    artifact = session.scalar(
        sa_select(ExerciseArtifact).where(
            ExerciseArtifact.id == artifact_id,
            ExerciseArtifact.project_id == project_id,
        )
    )
    object_key = artifact.exercise_object_key if file == "exercise" else artifact.answer_object_key
    if artifact is None or artifact.status != "complete" or not object_key:
        raise NotFoundError("exercise artifact not found")

    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.settings import get_settings

    try:
        content = StorageAdapter(bucket=get_settings().s3_bucket_artifacts).get(object_key)
    except Exception as err:  # noqa: BLE001 - storage miss must not fake success
        raise NotFoundError("exercise artifact not found") from err

    iw_service.audit_download(
        session,
        workspace.id,
        workspace.clerk_user_id,
        f"exercise_{file}",
        artifact.id,
    )
    session.commit()
    suffix = "exercises" if file == "exercise" else "answers"
    filename = f"{suffix}-lesson-{artifact.lesson_index:02d}.docx"
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

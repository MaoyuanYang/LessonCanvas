"""Pydantic projections for generation run state and the SSE event envelope.

These schemas are the frozen F003 contract between API/SSE and the Web client
(Spec API Behavior; ux-ui.md Frontend/Backend Contract).
"""

import uuid

from pydantic import BaseModel

TERMINAL_RUN_STATUSES = ("complete", "terminal_failure")
RESUMABLE_RUN_STATUSES = ("partial_failure", "capped_failure")
ACTIVE_RUN_STATUSES = ("queued", "generating", "validating")


class LessonArtifactOut(BaseModel):
    id: str
    lesson_index: int
    status: str
    language_mode: str
    failure_reason: str | None = None
    retry_count: int
    download_url: str | None = None


class GenerationSnapshot(BaseModel):
    run_id: str
    status: str
    brief_version: int
    blueprint_version: int
    language_mode: str
    model_calls: int
    model_call_cap: int
    artifacts: list[LessonArtifactOut]
    complete_count: int
    total_count: int


class RunEventOut(BaseModel):
    id: str
    run_id: str
    seq: int
    event_type: str
    payload: dict
    created_at: str


def artifact_out(artifact) -> LessonArtifactOut:
    return LessonArtifactOut(
        id=str(artifact.id),
        lesson_index=artifact.lesson_index,
        status=artifact.status,
        language_mode=artifact.language_mode,
        failure_reason=artifact.failure_reason,
        retry_count=artifact.retry_count,
        download_url=f"/projects/{artifact.project_id}/lesson-plans/{artifact.id}/download"
        if artifact.status == "complete"
        else None,
    )


def event_out(event) -> RunEventOut:
    import json

    return RunEventOut(
        id=str(event.id),
        run_id=str(event.run_id),
        seq=event.seq,
        event_type=event.event_type,
        payload=json.loads(event.payload_json),
        created_at=event.created_at.isoformat(),
    )


def run_id_of(snapshot_run_id: uuid.UUID | str) -> str:
    return str(snapshot_run_id)

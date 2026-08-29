"""Run orchestration: idempotent generation runs, checkpoints, and the authoritative event log.

PostgreSQL owns run state, per-lesson outcomes, and SSE-replayable events
(ADR-0002). Redis/Celery are transport only.
"""

from lessoncanvas.modules.run_orchestration.schemas import (
    GenerationSnapshot,
    LessonArtifactOut,
    RunEventOut,
)
from lessoncanvas.modules.run_orchestration.service import (
    MissingVersionsError,
    ResumeNotAllowedError,
    append_event,
    current_run,
    replay_events,
    reserve_model_call,
    resume_run,
    run_snapshot,
    start_generation,
)

__all__ = [
    "GenerationSnapshot",
    "LessonArtifactOut",
    "RunEventOut",
    "MissingVersionsError",
    "ResumeNotAllowedError",
    "append_event",
    "current_run",
    "replay_events",
    "reserve_model_call",
    "resume_run",
    "run_snapshot",
    "start_generation",
]

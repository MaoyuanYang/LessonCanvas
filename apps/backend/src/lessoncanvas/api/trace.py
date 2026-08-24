import uuid

from fastapi import APIRouter
from sqlalchemy import select

from lessoncanvas.api.deps import SessionDep, WorkspaceDep
from lessoncanvas.api.errors import NotFoundError
from lessoncanvas.models import DiscoveryRun, InteractionMessage, TraceEvent
from lessoncanvas.modules.identity_workspace.service import (
    NotFoundError as ServiceNotFound,
)
from lessoncanvas.modules.identity_workspace.service import (
    get_owned_project,
)

router = APIRouter(prefix="/projects/{project_id}/trace", tags=["trace"])


@router.get("")
def read_trace(project_id: uuid.UUID, workspace: WorkspaceDep, session: SessionDep) -> dict:
    try:
        get_owned_project(session, workspace, project_id)
    except ServiceNotFound as err:
        raise NotFoundError("project not found") from err

    runs = session.scalars(select(DiscoveryRun).where(DiscoveryRun.project_id == project_id)).all()
    run_ids = [run.id for run in runs]
    events: list[dict] = []
    messages: list[dict] = []
    if run_ids:
        events = [
            {
                "run_id": str(event.run_id),
                "event_type": event.event_type,
                "latency_ms": event.latency_ms,
                "cost_usd": event.cost_usd,
                "created_at": event.created_at.isoformat(),
            }
            for event in session.scalars(
                select(TraceEvent)
                .where(TraceEvent.run_id.in_(run_ids))
                .order_by(TraceEvent.created_at)
            )
        ]
        messages = [
            {
                "run_id": str(message.run_id),
                "role": message.role,
                "round_index": message.round_index,
                "created_at": message.created_at.isoformat(),
            }
            for message in session.scalars(
                select(InteractionMessage)
                .where(InteractionMessage.run_id.in_(run_ids))
                .order_by(InteractionMessage.created_at)
            )
        ]
    return {
        "runs": [
            {
                "run_id": str(run.id),
                "status": run.status,
                "round_count": run.round_count,
                "model_calls": run.model_calls,
            }
            for run in runs
        ],
        "events": events,
        "messages": messages,
    }

import json
import uuid
from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from sqlalchemy import select

from lessoncanvas.adapters.model import ModelProviderError
from lessoncanvas.models import DiscoveryRun, InteractionMessage
from lessoncanvas.modules.discovery_planning import graph
from lessoncanvas.modules.identity_workspace.service import NotFoundError
from lessoncanvas.settings import get_settings


class ProviderFailureError(Exception):
    pass


class RunQuotaError(Exception):
    pass


def _dsn() -> str:
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")


@lru_cache
def get_checkpointer():
    settings = get_settings()
    if settings.checkpoint_backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(_dsn(), open=True, kwargs={"autocommit": True})
    saver = PostgresSaver(pool)
    saver.setup()
    return saver


@lru_cache
def compiled_graph():
    return graph.build_graph().compile(checkpointer=get_checkpointer())


def get_active_run(session, project_id: uuid.UUID) -> DiscoveryRun | None:
    return session.scalar(
        select(DiscoveryRun)
        .where(DiscoveryRun.project_id == project_id, DiscoveryRun.status != "draft_ready")
        .order_by(DiscoveryRun.created_at.desc())
    )


def get_run_or_raise(session, project_id: uuid.UUID) -> DiscoveryRun:
    run = session.scalar(
        select(DiscoveryRun)
        .where(DiscoveryRun.project_id == project_id)
        .order_by(DiscoveryRun.created_at.desc())
    )
    if run is None:
        raise NotFoundError("discovery run not found")
    return run


def _initial_state(session, run: DiscoveryRun) -> dict:
    corpus = graph.build_corpus(session, run.project_id)
    project_hints = ""
    from lessoncanvas.models import Project

    project = session.get(Project, run.project_id)
    if project and project.unit_hints:
        project_hints = project.unit_hints
    known = graph.extract_known_fields("\n".join(p for p in [corpus, project_hints] if p))
    return {"run_id": str(run.id), "known_fields": known, "round_count": 0}


def _pending_questions(session, run: DiscoveryRun) -> list[dict]:
    message = session.scalar(
        select(InteractionMessage)
        .where(InteractionMessage.run_id == run.id, InteractionMessage.role == "agent")
        .order_by(InteractionMessage.created_at.desc())
    )
    if message is None or run.status != "questioning":
        return []
    try:
        return json.loads(message.content)
    except json.JSONDecodeError:
        return []


def _sync_status(session, run: DiscoveryRun) -> None:
    compiled = compiled_graph()
    snapshot = compiled.get_state({"configurable": {"thread_id": str(run.id)}})
    if not snapshot.next:
        run.status = "draft_ready"
    else:
        run.status = "questioning"
    session.commit()


def start_discovery(session, workspace_id: uuid.UUID, project_id: uuid.UUID) -> DiscoveryRun:
    existing = get_active_run(session, project_id)
    if existing is not None:
        return existing
    run = DiscoveryRun(project_id=project_id, workspace_id=workspace_id, status="initializing")
    session.add(run)
    session.commit()

    state = _initial_state(session, run)
    compiled = compiled_graph()
    config = {"configurable": {"thread_id": str(run.id)}}
    try:
        compiled.invoke(state, config)
    except ModelProviderError as error:
        run.status = "provider_failed"
        session.commit()
        raise ProviderFailureError(str(error)) from error
    _sync_status(session, run)
    return run


def retry_discovery(session, project_id: uuid.UUID) -> DiscoveryRun:
    run = get_run_or_raise(session, project_id)
    if run.status != "provider_failed":
        return run
    compiled = compiled_graph()
    config = {"configurable": {"thread_id": str(run.id)}}
    try:
        compiled.invoke(None, config)
    except ModelProviderError as error:
        run.status = "provider_failed"
        session.commit()
        raise ProviderFailureError(str(error)) from error
    _sync_status(session, run)
    return run


def submit_answers(session, project_id: uuid.UUID, answers: dict) -> DiscoveryRun:
    run = get_run_or_raise(session, project_id)
    if run.status == "draft_ready":
        return run
    compiled = compiled_graph()
    config = {"configurable": {"thread_id": str(run.id)}}
    try:
        compiled.invoke(Command(resume={"answers": answers}), config)
    except ModelProviderError as error:
        run.status = "provider_failed"
        session.commit()
        raise ProviderFailureError(str(error)) from error
    _sync_status(session, run)
    return run


def discovery_status(session, project_id: uuid.UUID) -> dict:
    run = get_run_or_raise(session, project_id)
    return {
        "run_id": str(run.id),
        "status": run.status,
        "round_count": run.round_count,
        "questions": _pending_questions(session, run),
        "draft": json.loads(run.draft_json) if run.draft_json else None,
    }

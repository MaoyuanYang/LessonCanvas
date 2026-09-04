import uuid

from lessoncanvas.db import SessionLocal
from lessoncanvas.settings import get_settings
from lessoncanvas.worker import celery_app


@celery_app.task(name="lessoncanvas.parse_source")
def parse_source(source_id: str) -> str:
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.modules.sources_grounding.service import process_source

    session = SessionLocal()
    status = "failed"
    try:
        source = process_source(session, StorageAdapter(), uuid.UUID(source_id))
        session.commit()
        status = source.status
    finally:
        session.close()
    # F016 D1: a successfully parsed source (chunks exist; embedding attempts
    # settled) receives its analysis asynchronously. Embedding failures do not
    # gate the analysis — it reads chunk text, not vectors.
    if status == "ready":
        enqueue_analysis(uuid.UUID(source_id))
    return status


@celery_app.task(name="lessoncanvas.analyze_source", max_retries=0)
def analyze_source(source_id: str) -> str:
    """One bounded analysis call per trigger; failure settles a visible
    failed state with a manual retry (never a silent Celery re-bill)."""

    from lessoncanvas.modules.sources_grounding.analysis import (
        AnalysisInProgressError,
    )
    from lessoncanvas.modules.sources_grounding.analysis import (
        analyze_source as run,
    )

    session = SessionLocal()
    try:
        row = run(session, uuid.UUID(source_id))
        session.commit()
        return row.status
    except AnalysisInProgressError:
        session.rollback()
        return "in-flight"
    except ValueError:
        # Source vanished or is not ready; nothing to analyze.
        session.rollback()
        return "skipped"
    finally:
        session.close()


def enqueue_analysis(source_id: uuid.UUID) -> None:
    if get_settings().tasks_eager:
        analyze_source.apply(args=[str(source_id)])
    else:
        analyze_source.delay(str(source_id))

import uuid

from lessoncanvas.db import SessionLocal
from lessoncanvas.worker import celery_app


@celery_app.task(name="lessoncanvas.parse_source")
def parse_source(source_id: str) -> str:
    from lessoncanvas.adapters.storage import StorageAdapter
    from lessoncanvas.modules.sources_grounding.service import process_source

    session = SessionLocal()
    try:
        source = process_source(session, StorageAdapter(), uuid.UUID(source_id))
        session.commit()
        return source.status
    finally:
        session.close()

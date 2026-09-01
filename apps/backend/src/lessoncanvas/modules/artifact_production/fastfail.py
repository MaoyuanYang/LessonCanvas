"""F011 D6 worker fast-fail on vanished runs (F006 M-2 / F004 M-2 class).

Deleting a project mid-run races the Worker's in-flight lesson update: the
UPDATE matches zero rows and raises StaleDataError (reproduced live in the
F006 TS-024 evidence). Bounded retries cannot recover data that no longer
exists, so this class settles immediately as the terminal missing_run outcome
instead of two 180 s-delayed retries. Transient provider failures keep the
bounded-retry path.
"""

import json
import uuid

from sqlalchemy.orm.exc import StaleDataError


def settle_vanished_run(run_id: str, error: Exception) -> str | None:
    """Return "missing_run" when the error is the vanished-run class.

    Returns None when the error should keep the existing bounded-retry path.
    """
    vanished = isinstance(error, StaleDataError) or _run_row_missing(run_id)
    if not vanished:
        return None
    _settle_terminal(run_id, type(error).__name__)
    return "missing_run"


def _run_row_missing(run_id: str) -> bool:
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun

    session = SessionLocal()
    try:
        return session.get(GenerationRun, uuid.UUID(run_id)) is None
    except Exception:
        # Unprovable (for example a connection blip) is not vanished: keep
        # the retryable path rather than settling live work prematurely.
        return False
    finally:
        session.close()


def _settle_terminal(run_id: str, error_kind: str) -> None:
    """Best-effort terminal settle when the run row itself still exists."""
    from lessoncanvas.db import SessionLocal
    from lessoncanvas.models import GenerationRun
    from lessoncanvas.modules.run_orchestration import service as run_service

    session = SessionLocal()
    try:
        run = session.get(GenerationRun, uuid.UUID(run_id))
        if run is None:
            return
        run.status = "missing_run"
        run.failure_json = json.dumps(
            {"reason": "owning project deleted mid-run", "error": error_kind}
        )
        session.commit()
        run_service.append_event(
            session,
            run.id,
            "run",
            {"status": "missing_run", "reason": "owning project deleted mid-run"},
        )
        session.commit()
    except Exception:
        pass
    finally:
        session.close()

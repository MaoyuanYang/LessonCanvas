"""Workspace rate limiting with PostgreSQL as the single truth (F011 D1/D2).

Fixed windows: every attempt atomically increments a per-(workspace, class,
window) counter via ``INSERT ... ON CONFLICT DO UPDATE``; the returned count
decides admission. Window boundaries are deterministic instants, so a rejected
caller can always be told exactly when the next window opens. Gateway or
provider limits are defense in depth only and never the Source of Truth.

Counters count attempts, including rejected ones: a saturated window cannot
be drained by retrying, which keeps the public-demo abuse profile bounded.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from lessoncanvas.ids import uuid7
from lessoncanvas.models import RateWindowCounter

GENERAL_CLASS = "general"
EXPENSIVE_CLASS = "expensive"
UPLOAD_DAILY_CLASS = "upload_daily"

_UPSERT = text(
    """
    INSERT INTO rate_window_counters
        (id, workspace_id, limit_class, window_start, count, bytes_accum)
    VALUES (:id, :workspace_id, :limit_class, :window_start, :count, :bytes_accum)
    ON CONFLICT (workspace_id, limit_class, window_start)
    DO UPDATE SET count = rate_window_counters.count + EXCLUDED.count,
                  bytes_accum = rate_window_counters.bytes_accum + EXCLUDED.bytes_accum
    RETURNING count, bytes_accum
    """
)


def floor_window(now: datetime, window_seconds: int) -> datetime:
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - epoch % window_seconds, tz=UTC)


def window_reset(now: datetime, window_seconds: int) -> datetime:
    start = floor_window(now, window_seconds)
    return start + timedelta(seconds=window_seconds)


def consume_rate(
    session: Session,
    workspace_id: uuid.UUID,
    limit_class: str,
    limit_value: int,
    window_seconds: int,
    *,
    bytes_accum: int = 0,
) -> tuple[bool, dict]:
    """Consume one request slot (and optional bytes) for the current window.

    Returns ``(allowed, details)``; ``details`` carries the limit facts the
    429 payload and the usage read surface both use.
    """
    now = datetime.now(UTC)
    start = floor_window(now, window_seconds)
    row = session.execute(
        _UPSERT,
        {
            "id": uuid7(),
            "workspace_id": workspace_id,
            "limit_class": limit_class,
            "window_start": start,
            "count": 1,
            "bytes_accum": bytes_accum,
        },
    ).one()
    used, used_bytes = int(row.count), int(row.bytes_accum)
    retry_after = max(1, int((window_reset(now, window_seconds) - now).total_seconds()) + 1)
    if bytes_accum:
        allowed = used_bytes <= limit_value
        used_metric = used_bytes
    else:
        allowed = used <= limit_value
        used_metric = used
    details = {
        "limit": limit_class,
        "limit_value": limit_value,
        "window_seconds": window_seconds,
        "used": used_metric,
        "retry_after_seconds": retry_after,
    }
    if allowed and window_seconds >= 3600:
        _prune_old_windows(session, workspace_id, limit_class, start, window_seconds)
    return allowed, details


def _prune_old_windows(
    session: Session,
    workspace_id: uuid.UUID,
    limit_class: str,
    keep_start: datetime,
    window_seconds: int,
) -> None:
    # Daily (and longer) windows prune their previous windows so the table
    # stays bounded; short windows are cheap enough to leave to natural churn.
    horizon = keep_start - timedelta(seconds=window_seconds * 2)
    session.execute(
        text(
            "DELETE FROM rate_window_counters "
            "WHERE workspace_id = :workspace_id AND limit_class = :limit_class "
            "AND window_start < :horizon"
        ),
        {"workspace_id": workspace_id, "limit_class": limit_class, "horizon": horizon},
    )


def read_window(
    session: Session,
    workspace_id: uuid.UUID,
    limit_class: str,
    window_seconds: int,
) -> dict:
    """Current-window usage snapshot for the account usage surface."""
    now = datetime.now(UTC)
    start = floor_window(now, window_seconds)
    row = session.execute(
        text(
            "SELECT count, bytes_accum FROM rate_window_counters "
            "WHERE workspace_id = :workspace_id AND limit_class = :limit_class "
            "AND window_start = :window_start"
        ),
        {"workspace_id": workspace_id, "limit_class": limit_class, "window_start": start},
    ).first()
    used = int(row.count) if row else 0
    used_bytes = int(row.bytes_accum) if row else 0
    reset = window_reset(now, window_seconds)
    return {
        "window_seconds": window_seconds,
        "used": used,
        "used_bytes": used_bytes,
        "reset_at": reset.isoformat(),
        "retry_after_seconds": max(1, int((reset - now).total_seconds()) + 1),
    }


def current_window_start(window_seconds: int) -> datetime:
    return floor_window(datetime.now(UTC), window_seconds)


__all__ = [
    "EXPENSIVE_CLASS",
    "GENERAL_CLASS",
    "UPLOAD_DAILY_CLASS",
    "RateWindowCounter",
    "consume_rate",
    "current_window_start",
    "read_window",
    "window_reset",
]

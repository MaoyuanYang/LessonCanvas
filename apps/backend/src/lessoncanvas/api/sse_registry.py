"""Per-workspace concurrent SSE stream admission (F011 D2).

In-process registry: the API deployment shape is a single application process
(Spec D1 assumption), so process-local counting is authoritative for streams.
Slots release in ``finally`` so disconnects never leak. Streams never create
model work, so rejection is a named capacity limit, not a content error.
"""

import threading
import uuid

from lessoncanvas.api.errors import QuotaExceededError

_active_streams: dict[uuid.UUID, int] = {}
_lock = threading.Lock()


def active_stream_count(workspace_id: uuid.UUID) -> int:
    with _lock:
        return _active_streams.get(workspace_id, 0)


def acquire_stream_slot(workspace_id: uuid.UUID, limit: int) -> None:
    """Admit-or-reject before the response starts; release_stream_slot frees."""
    with _lock:
        current = _active_streams.get(workspace_id, 0)
        if current >= limit:
            raise QuotaExceededError(
                "concurrent stream limit reached",
                {
                    "limit": "concurrent_sse_streams",
                    "limit_value": limit,
                    "used": current,
                },
            )
        _active_streams[workspace_id] = current + 1


def release_stream_slot(workspace_id: uuid.UUID) -> None:
    with _lock:
        remaining = _active_streams.get(workspace_id, 1) - 1
        if remaining <= 0:
            _active_streams.pop(workspace_id, None)
        else:
            _active_streams[workspace_id] = remaining

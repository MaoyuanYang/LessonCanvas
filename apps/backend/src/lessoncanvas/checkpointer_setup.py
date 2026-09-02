"""F012 TS-011 fix (B-001 routed residual): pre-create the LangGraph
PostgresSaver schema at container startup.

Why: `PostgresSaver.setup()` runs DDL (`CREATE INDEX CONCURRENTLY ...`) on
first use per process. In the deployed multi-process topology (api + worker +
one-off seeds) concurrent first-use setup can queue on locks behind open
transactions and hang requests indefinitely (observed 2026-09-02 on the
deployed stack: discovery start blocked in `setup()`). Running setup once,
serially, in the container entrypoint — with a bounded lock timeout and
retries — removes the race; later in-process `setup()` calls become no-ops
(their migrations table is already current).

Usage: python -m lessoncanvas.checkpointer_setup
"""

import sys
import time

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from lessoncanvas.modules.discovery_planning.service import _dsn

LOCK_TIMEOUT_SECONDS = 15
ATTEMPTS = 6
ATTEMPT_DELAY_SECONDS = 5


def run() -> None:
    pool = ConnectionPool(
        _dsn(), open=True, kwargs={"autocommit": True}, timeout=LOCK_TIMEOUT_SECONDS
    )
    try:
        conn = pool.getconn()
        try:
            conn.execute(f"SET lock_timeout = '{LOCK_TIMEOUT_SECONDS}s'")
        finally:
            pool.putconn(conn)
        last_error: Exception | None = None
        for attempt in range(1, ATTEMPTS + 1):
            try:
                PostgresSaver(pool).setup()
                print(
                    f"checkpointer setup ok (attempt {attempt})", file=sys.stderr
                )
                return
            except Exception as error:  # lock timeout or transient DDL race
                last_error = error
                print(
                    f"checkpointer setup attempt {attempt} failed: {error!r}",
                    file=sys.stderr,
                )
                time.sleep(ATTEMPT_DELAY_SECONDS)
        raise SystemExit(f"checkpointer setup failed after {ATTEMPTS} attempts: {last_error!r}")
    finally:
        pool.close()


if __name__ == "__main__":
    run()

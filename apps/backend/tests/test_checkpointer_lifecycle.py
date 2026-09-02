"""F012 TS-011 (F001/B-001 routed residual): Postgres LangGraph checkpointer
behavior in the deployed topology. Verifies the two properties the deployed
multi-process stack (api + worker containers, restarts) depends on:

1. `PostgresSaver.setup()` is idempotent and repeat-safe across fresh pool
   instances (both processes create/check the tables at first use).
2. Checkpoints persist across saver instances, so a restarted process resumes
   from persisted state instead of silently starting over.

Deletion-scope cleanup of checkpoint rows is already covered by F011
(test_guardrails_deletion.py) and is not repeated here.
"""

import uuid

import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from lessoncanvas.modules.discovery_planning.service import _dsn


def _fresh_saver() -> tuple[PostgresSaver, ConnectionPool]:
    # A brand-new pool+saver stands in for a brand-new process. setup() is
    # idempotent: on an already-migrated database it re-checks and no-ops.
    pool = ConnectionPool(_dsn(), open=True, kwargs={"autocommit": True})
    saver = PostgresSaver(pool)
    saver.setup()
    return saver, pool


@pytest.fixture(autouse=True)
def _clean_checkpoint_tables():
    """Start from the real PostgresSaver schema: drop any degraded layout
    left by earlier tooling, then let setup() recreate the authoritative one.
    In production a fresh database never sees the degraded layout; this
    fixture only isolates the test database from that history."""
    from sqlalchemy import text

    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    try:
        session.execute(
            text(
                "DROP TABLE IF EXISTS checkpoints, checkpoint_blobs, "
                "checkpoint_writes, checkpoint_migrations"
            )
        )
        session.commit()
    finally:
        session.close()


def test_setup_is_repeatable_across_fresh_instances():
    saver_a, pool_a = _fresh_saver()
    saver_b, pool_b = _fresh_saver()
    try:
        list(saver_a.list(None, limit=1))
        list(saver_b.list(None, limit=1))
    finally:
        pool_a.close()
        pool_b.close()


def test_checkpoint_persists_across_saver_instances():
    thread_id = f"test-checkpoint-{uuid.uuid4()}"
    saver_a, pool_a = _fresh_saver()
    try:
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        saver_a.put(
            config,
            {
                "ts": "2026-09-02T00:00:00+00:00",
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, thread_id)),
                "channel_values": {},
                "v": 4,
            },
            {"source": "input", "step": 1},
            {},
        )
    finally:
        pool_a.close()

    # A later instance (e.g. after a container restart) must observe it.
    saver_b, pool_b = _fresh_saver()
    try:
        found = saver_b.get_tuple({"configurable": {"thread_id": thread_id}})
        assert found is not None
        assert found.config["configurable"]["thread_id"] == thread_id
    finally:
        pool_b.close()

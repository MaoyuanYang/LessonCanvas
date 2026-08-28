import datetime
import os
import socket
from pathlib import Path

os.environ.setdefault(
    "LESSONCANVAS_DATABASE_URL",
    "postgresql+psycopg://lessoncanvas:lessoncanvas_dev_only@localhost:5432/lessoncanvas_test",
)
os.environ["LESSONCANVAS_CLERK_JWKS_URL"] = ""
os.environ["LESSONCANVAS_TASKS_EAGER"] = "true"
os.environ["LESSONCANVAS_S3_BUCKET_SOURCES"] = "lessoncanvas-sources-test"
os.environ["LESSONCANVAS_MODEL_ADAPTER"] = "fake"
os.environ["LESSONCANVAS_CHECKPOINT_BACKEND"] = "memory"

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from lessoncanvas.settings import get_settings

TABLES = (
    "trace_events, interaction_messages, discovery_runs, blueprint_drafts, blueprint_versions, "
    "source_chunks, sources, brief_versions, brief_drafts, audit_events, quota_counters, "
    "projects, workspaces, account_deletion_events"
)


def _postgres_available() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=2):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    if not _postgres_available():
        pytest.skip("local PostgreSQL is not running (docker compose up -d)")
    settings = get_settings()
    admin_engine = create_engine(
        settings.database_url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'lessoncanvas_test'")
        ).scalar()
        if not exists:
            connection.execute(text("CREATE DATABASE lessoncanvas_test"))
    admin_engine.dispose()

    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent.parent / "migrations"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
    yield


@pytest.fixture()
def db_session():
    from lessoncanvas.db import SessionLocal

    session = SessionLocal()
    session.execute(text(f"TRUNCATE TABLE {TABLES}"))
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    from lessoncanvas import main

    return TestClient(main.app)


def make_token(subject: str) -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "aud": settings.auth_dev_audience,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    }
    return pyjwt.encode(payload, settings.auth_dev_secret, algorithm="HS256")


@pytest.fixture()
def teacher_a_token() -> str:
    return make_token("teacher_a")


@pytest.fixture()
def teacher_b_token() -> str:
    return make_token("teacher_b")


@pytest.fixture()
def auth(teacher_a_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {teacher_a_token}"}

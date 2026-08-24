from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from lessoncanvas.settings import get_settings


def build_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_database() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"

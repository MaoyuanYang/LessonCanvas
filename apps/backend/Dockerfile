# LessonCanvas FastAPI application image (F012 D1).
# Also runs `alembic upgrade head` before serving so a fresh stack migrates.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
RUN uv sync --locked --no-dev

EXPOSE 8000

# F012 TS-011: migrate, then pre-create the LangGraph checkpointer schema
# serially before serving (multi-process setup() races otherwise).
CMD ["sh", "-c", "alembic upgrade head && python -m lessoncanvas.checkpointer_setup && uvicorn lessoncanvas.main:app --host 0.0.0.0 --port 8000"]

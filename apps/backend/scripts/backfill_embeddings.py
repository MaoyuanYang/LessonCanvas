"""F014 T2 (Spec D2): idempotent deploy-time embedding backfill.

Embeds every source chunk that is still `pending` (pre-migration rows and
any chunk whose parse-time embedding failed permanently), and fills missing
content/text hashes as a safety net. Safe to re-run: completed chunks are
skipped, a failed chunk never blocks the rest, and re-running after an
interrupted pass completes the remainder exactly once.

Runs inside the deployed image after `alembic upgrade head`:
    uv run python scripts/backfill_embeddings.py
"""

import sys
import uuid

from sqlalchemy import select

from lessoncanvas.db import SessionLocal
from lessoncanvas.models import Source, SourceChunk
from lessoncanvas.modules.sources_grounding import embeddings as embeddings_module
from lessoncanvas.settings import get_settings

BATCH_SIZE = 64


def backfill(session) -> dict:
    stats = {"embedded": 0, "failed": 0, "hashes_filled": 0}
    chunk_ids = session.scalars(
        select(SourceChunk.id)
        .where(SourceChunk.embedding_status != "ok")
        .order_by(SourceChunk.source_id, SourceChunk.position)
    ).all()
    by_source: dict[uuid.UUID, list[uuid.UUID]] = {}
    for chunk_id in chunk_ids:
        chunk = session.get(SourceChunk, chunk_id)
        by_source.setdefault(chunk.source_id, []).append(chunk_id)

    for ids in by_source.values():
        for start in range(0, len(ids), BATCH_SIZE):
            batch = [session.get(SourceChunk, cid) for cid in ids[start : start + BATCH_SIZE]]
            states = embeddings_module.embed_chunks([chunk.text for chunk in batch])
            for chunk, state in zip(batch, states, strict=True):
                if chunk.text_sha256 is None:
                    chunk.text_sha256 = embeddings_module.text_hash(chunk.text)
                    stats["hashes_filled"] += 1
                chunk.embedding = state["vector"]
                chunk.embedding_status = state["status"]
                chunk.embedding_error = state["error"]
                stats["embedded" if state["status"] == "ok" else "failed"] += 1
        session.commit()

    for source in session.scalars(select(Source)).all():
        if source.content_sha256 is not None:
            continue
        chunk_texts = session.scalars(
            select(SourceChunk.text)
            .where(SourceChunk.source_id == source.id)
            .order_by(SourceChunk.position)
        ).all()
        if not chunk_texts:
            continue
        source.content_sha256 = embeddings_module.content_hash(chunk_texts)
        stats["hashes_filled"] += 1
        session.commit()
    return stats


def main() -> int:
    settings = get_settings()
    if settings.model_adapter != "fake" and settings.embedding_adapter == "fake":
        print(
            "backfill_embeddings: refusing to run with the fake embedding adapter "
            "outside test environments (set LESSONCANVAS_EMBEDDING_ADAPTER=fastembed)",
            file=sys.stderr,
        )
        return 2
    session = SessionLocal()
    try:
        stats = backfill(session)
    finally:
        session.close()
    print(
        f"backfill_embeddings: embedded={stats['embedded']} "
        f"failed={stats['failed']} hashes_filled={stats['hashes_filled']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Semantic source retrieval columns (F014, ADR-0007).

Revision ID: f014c1e3f5a7
Revises: f013b1d2e3f4
Create Date: 2026-09-03
"""

import hashlib

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "f014c1e3f5a7"
down_revision: str | None = "f013b1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "sources",
        sa.Column("content_sha256", sa.String(64), nullable=True),
    )
    op.add_column(
        "source_chunks",
        sa.Column("embedding", Vector(512), nullable=True),
    )
    op.add_column(
        "source_chunks",
        sa.Column(
            "embedding_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "source_chunks",
        sa.Column("embedding_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "source_chunks",
        sa.Column("text_sha256", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_source_chunks_embedding_hnsw",
        "source_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    # Legacy rows: chunk hashes and source content hashes are computed here;
    # embeddings for legacy chunks come from the idempotent deploy-time
    # backfill command (Spec D2), never lazily at read time.
    connection = op.get_bind()
    chunks = connection.execute(
        sa.text(
            "SELECT id, source_id, position, text FROM source_chunks "
            "ORDER BY source_id, position"
        )
    ).mappings()
    source_texts: dict[str, list[str]] = {}
    for chunk in chunks:
        digest = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()
        connection.execute(
            sa.text("UPDATE source_chunks SET text_sha256 = :h WHERE id = :id"),
            {"h": digest, "id": chunk["id"]},
        )
        source_texts.setdefault(str(chunk["source_id"]), []).append(chunk["text"])
    for source_id, texts in source_texts.items():
        digest = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()
        connection.execute(
            sa.text("UPDATE sources SET content_sha256 = :h WHERE id = :id"),
            {"h": digest, "id": source_id},
        )


def downgrade() -> None:
    op.drop_index("ix_source_chunks_embedding_hnsw", table_name="source_chunks")
    op.drop_column("source_chunks", "text_sha256")
    op.drop_column("source_chunks", "embedding_error")
    op.drop_column("source_chunks", "embedding_status")
    op.drop_column("source_chunks", "embedding")
    op.drop_column("sources", "content_sha256")

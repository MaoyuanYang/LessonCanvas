"""add guardrail rate counters and retained security ledger

Revision ID: f011e2f4a5b6
Revises: f010b7c9d1e3
Create Date: 2026-09-01 22:20:00.000000

F011 Public Multi-Account Guardrails: fixed-window rate/byte counters with
PostgreSQL as the single rate truth (Spec D1/D2), and the content-free
retained security ledger that survives workspace deletion (Spec D4(b) —
action, workspace id, time only; never content).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f011e2f4a5b6"
down_revision: str | None = "f010b7c9d1e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Latent F001 defect surfaced by F011 docx upload hardening: the OOXML
    # content type is 71 characters and never fit the original 64-char column.
    op.alter_column("sources", "content_type", type_=sa.String(length=128))

    op.create_table(
        "rate_window_counters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("limit_class", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bytes_accum", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.UniqueConstraint(
            "workspace_id", "limit_class", "window_start", name="uq_rate_window_identity"
        ),
    )
    op.create_index(
        "ix_rate_window_counters_workspace_id", "rate_window_counters", ["workspace_id"]
    )

    op.create_table(
        "retained_security_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_retained_security_events_workspace_id",
        "retained_security_events",
        ["workspace_id"],
    )

    # F011 D5 metadata-only deletion residual ledger: store/key identifiers
    # that outlived a failed cascade pass; never content. Drives repair until
    # the deletion completes, then the rows go too.
    op.create_table(
        "deletion_residuals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("store", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("table_name", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deletion_residuals_project_id", "deletion_residuals", ["project_id"])
    op.create_index("ix_deletion_residuals_workspace_id", "deletion_residuals", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_deletion_residuals_workspace_id", table_name="deletion_residuals")
    op.drop_index("ix_deletion_residuals_project_id", table_name="deletion_residuals")
    op.drop_table("deletion_residuals")
    op.drop_index(
        "ix_retained_security_events_workspace_id", table_name="retained_security_events"
    )
    op.drop_table("retained_security_events")
    op.drop_index("ix_rate_window_counters_workspace_id", table_name="rate_window_counters")
    op.drop_table("rate_window_counters")
    op.alter_column("sources", "content_type", type_=sa.String(length=64))

"""Rename Clerk-era subject columns to subject (ADR-0006 D12).

Revision ID: f012a7c9d2e4
Revises: f011e2f4a5b6
Create Date: 2026-09-02
"""

from alembic import op

revision: str = "f012a7c9d2e4"
down_revision: str | None = "f011e2f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("workspaces", "clerk_user_id", new_column_name="subject")
    op.alter_column(
        "account_deletion_events", "clerk_user_id", new_column_name="subject"
    )
    op.execute(
        "ALTER INDEX ix_account_deletion_events_clerk_user_id "
        "RENAME TO ix_account_deletion_events_subject"
    )
    op.execute(
        "ALTER TABLE workspaces RENAME CONSTRAINT "
        "workspaces_clerk_user_id_key TO workspaces_subject_key"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE workspaces RENAME CONSTRAINT "
        "workspaces_subject_key TO workspaces_clerk_user_id_key"
    )
    op.execute(
        "ALTER INDEX ix_account_deletion_events_subject "
        "RENAME TO ix_account_deletion_events_clerk_user_id"
    )
    op.alter_column(
        "account_deletion_events", "subject", new_column_name="clerk_user_id"
    )
    op.alter_column("workspaces", "subject", new_column_name="clerk_user_id")

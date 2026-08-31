"""add exercise artifact table and generation run difficulty

Revision ID: d5a9c1f3b7e4
Revises: b41d6c0f7a2e
Create Date: 2026-08-31 13:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5a9c1f3b7e4"
down_revision: str | None = "b41d6c0f7a2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Spec D9: the difficulty tier is write-once metadata on the run and is
    # deliberately NOT part of the unique run identity.
    op.add_column(
        "generation_runs",
        sa.Column("difficulty", sa.String(length=16), nullable=True),
    )

    op.create_table(
        "exercise_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("lesson_index", sa.Integer(), nullable=False),
        sa.Column("language_mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("category_count", sa.Integer(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=True),
        sa.Column("exercise_object_key", sa.Text(), nullable=True),
        sa.Column("exercise_checksum", sa.Text(), nullable=True),
        sa.Column("answer_object_key", sa.Text(), nullable=True),
        sa.Column("answer_checksum", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["generation_runs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.UniqueConstraint("run_id", "lesson_index", name="uq_exercise_artifact_lesson"),
    )
    op.create_index("ix_exercise_artifacts_run_id", "exercise_artifacts", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_exercise_artifacts_run_id", table_name="exercise_artifacts")
    op.drop_table("exercise_artifacts")
    op.drop_column("generation_runs", "difficulty")

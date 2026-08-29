"""add generation run artifact kind and slide deck artifact table

Revision ID: b41d6c0f7a2e
Revises: e7a2c50b9d31
Create Date: 2026-08-29 19:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b41d6c0f7a2e"
down_revision: str | None = "e7a2c50b9d31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_runs",
        sa.Column(
            "artifact_kind",
            sa.String(length=16),
            nullable=False,
            server_default="lesson_plan",
        ),
    )
    op.add_column(
        "generation_runs",
        sa.Column("prerequisite_run_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_generation_runs_prerequisite_run_id",
        "generation_runs",
        "generation_runs",
        ["prerequisite_run_id"],
        ["id"],
    )
    op.drop_constraint("uq_generation_run_identity", "generation_runs", type_="unique")
    op.create_unique_constraint(
        "uq_generation_run_identity",
        "generation_runs",
        ["project_id", "brief_version_id", "blueprint_version_id", "artifact_kind"],
    )

    op.create_table(
        "slide_deck_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("lesson_index", sa.Integer(), nullable=False),
        sa.Column("language_mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("slide_count", sa.Integer(), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["generation_runs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.UniqueConstraint("run_id", "lesson_index", name="uq_slide_deck_artifact_lesson"),
    )
    op.create_index("ix_slide_deck_artifacts_run_id", "slide_deck_artifacts", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_slide_deck_artifacts_run_id", table_name="slide_deck_artifacts")
    op.drop_table("slide_deck_artifacts")
    op.drop_constraint("uq_generation_run_identity", "generation_runs", type_="unique")
    op.create_unique_constraint(
        "uq_generation_run_identity",
        "generation_runs",
        ["project_id", "brief_version_id", "blueprint_version_id"],
    )
    op.drop_constraint(
        "fk_generation_runs_prerequisite_run_id", "generation_runs", type_="foreignkey"
    )
    op.drop_column("generation_runs", "prerequisite_run_id")
    op.drop_column("generation_runs", "artifact_kind")

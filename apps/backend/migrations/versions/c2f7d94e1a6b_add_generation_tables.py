"""add generation run, lesson plan artifact, and run event tables

Revision ID: c2f7d94e1a6b
Revises: 6d1c9a20b7f4
Create Date: 2026-08-29 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2f7d94e1a6b"
down_revision: str | None = "6d1c9a20b7f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=False),
        sa.Column("blueprint_version_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("model_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_call_cap", sa.Integer(), nullable=False),
        sa.Column("failure_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"]),
        sa.UniqueConstraint(
            "project_id", "brief_version_id", "blueprint_version_id",
            name="uq_generation_run_identity",
        ),
    )
    op.create_index("ix_generation_runs_project_id", "generation_runs", ["project_id"])

    op.create_table(
        "lesson_plan_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("lesson_index", sa.Integer(), nullable=False),
        sa.Column("language_mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
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
        sa.UniqueConstraint("run_id", "lesson_index", name="uq_lesson_plan_artifact_lesson"),
    )
    op.create_index("ix_lesson_plan_artifacts_run_id", "lesson_plan_artifacts", ["run_id"])

    op.create_table(
        "run_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["generation_runs.id"]),
        sa.UniqueConstraint("run_id", "seq", name="uq_run_event_seq"),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_index("ix_lesson_plan_artifacts_run_id", table_name="lesson_plan_artifacts")
    op.drop_table("lesson_plan_artifacts")
    op.drop_index("ix_generation_runs_project_id", table_name="generation_runs")
    op.drop_table("generation_runs")

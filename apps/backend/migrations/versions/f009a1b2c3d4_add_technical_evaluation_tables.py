"""add technical evaluation tables

Revision ID: f009a1b2c3d4
Revises: f008c3e7a9b1
Create Date: 2026-09-01 12:00:00.000000

F009 Technical Portfolio Evaluation: idempotent evaluation-pass records
bound to dataset revision, unit, mode, scenario, and the immutable version
pair each pass creates, plus per-criterion outcome rows (blocking
pass/fail/missing_evidence; diagnostic measured values without pass/fail).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f009a1b2c3d4"
down_revision: str | None = "f008c3e7a9b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "technical_evaluations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("dataset_revision", sa.String(length=32), nullable=False),
        sa.Column("unit_key", sa.String(length=64), nullable=False),
        sa.Column("pass_index", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("scenario", sa.String(length=48), nullable=False),
        sa.Column("model_config_json", sa.Text(), nullable=False),
        sa.Column("memory_state_json", sa.Text(), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=True),
        sa.Column("blueprint_version_id", sa.UUID(), nullable=True),
        sa.Column("run_ids_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("overall_outcome", sa.String(length=16), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"]),
        sa.UniqueConstraint(
            "project_id",
            "dataset_revision",
            "unit_key",
            "pass_index",
            "mode",
            "scenario",
            name="uq_technical_evaluation_identity",
        ),
    )
    op.create_index(
        "ix_technical_evaluations_project_id", "technical_evaluations", ["project_id"]
    )
    op.create_index(
        "ix_technical_evaluations_workspace_id", "technical_evaluations", ["workspace_id"]
    )

    op.create_table(
        "technical_evaluation_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evaluation_id", sa.UUID(), nullable=False),
        sa.Column("criterion_key", sa.String(length=48), nullable=False),
        sa.Column("classification", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("measured_json", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["technical_evaluations.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "evaluation_id",
            "criterion_key",
            name="uq_technical_evaluation_result_criterion",
        ),
    )
    op.create_index(
        "ix_technical_evaluation_results_evaluation_id",
        "technical_evaluation_results",
        ["evaluation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_technical_evaluation_results_evaluation_id",
        table_name="technical_evaluation_results",
    )
    op.drop_table("technical_evaluation_results")
    op.drop_index("ix_technical_evaluations_workspace_id", table_name="technical_evaluations")
    op.drop_index("ix_technical_evaluations_project_id", table_name="technical_evaluations")
    op.drop_table("technical_evaluations")

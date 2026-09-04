"""Specialist stage tables and columns (F016 Spec: source analyses, plan
design, review findings).

Revision ID: f016a1b2c3d4
Revises: f014d5f7b9c2
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "f016a1b2c3d4"
down_revision: str | None = "f014d5f7b9c2"
branch_labels = None
depends_on = None

FAMILIES = ("lesson_plan_artifacts", "slide_deck_artifacts", "exercise_artifacts")


def upgrade() -> None:
    op.create_table(
        "source_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sources.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="F016 D1: latest-wins source-analysis rows (one per source)",
    )
    op.add_column(
        "lesson_plan_artifacts",
        sa.Column(
            "design_json",
            sa.Text(),
            nullable=True,
            comment="F016 D4: validated activity-design intermediate (evidence-visible only)",
        ),
    )
    op.add_column(
        "lesson_plan_artifacts",
        sa.Column(
            "design_status",
            sa.String(16),
            nullable=True,
            comment="F016: pending | ready | failed for the design stage",
        ),
    )
    for table in FAMILIES:
        op.add_column(
            table,
            sa.Column(
                "review_findings_json",
                sa.Text(),
                nullable=True,
                comment="F016 D3: findings of the latest review round",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "review_rounds",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="F016: review rounds executed (0 | 1 | 2 with revise)",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "review_outcome",
                sa.String(24),
                nullable=True,
                comment="F016: passed | passed_after_revise | failed_after_revise",
            ),
        )


    op.add_column(
        "technical_evaluations",
        sa.Column(
            "source_analysis_state_json",
            sa.Text(),
            nullable=True,
            comment="F016 D7: pinned per-source analysis states for pass comparability",
        ),
    )


def downgrade() -> None:
    op.drop_column("technical_evaluations", "source_analysis_state_json")
    for table in FAMILIES:
        op.drop_column(table, "review_outcome")
        op.drop_column(table, "review_rounds")
        op.drop_column(table, "review_findings_json")
    op.drop_column("lesson_plan_artifacts", "design_status")
    op.drop_column("lesson_plan_artifacts", "design_json")
    op.drop_table("source_analyses")

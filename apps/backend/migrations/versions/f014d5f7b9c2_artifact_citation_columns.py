"""Artifact citation columns (F014 Spec AC-003, UX U1/U2).

Revision ID: f014d5f7b9c2
Revises: f014c1e3f5a7
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op

revision: str = "f014d5f7b9c2"
down_revision: str | None = "f014c1e3f5a7"
branch_labels = None
depends_on = None

TABLES = ("lesson_plan_artifacts", "slide_deck_artifacts", "exercise_artifacts")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "citations_json",
                sa.Text(),
                nullable=True,
                comment="F014: server-injected chunk citations from this artifact's own retrieval",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "grounding_state",
                sa.String(16),
                nullable=True,
                comment="F014: retrieved | none for this artifact's per-lesson retrieval",
            ),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "grounding_state")
        op.drop_column(table, "citations_json")

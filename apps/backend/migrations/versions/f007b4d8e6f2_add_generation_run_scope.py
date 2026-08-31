"""add generation run scope for targeted regeneration

Revision ID: f007b4d8e6f2
Revises: f006a1c9e221
Create Date: 2026-08-31 22:00:00.000000

F007 Versioned Targeted Regeneration: generation runs gain a nullable JSON
array of affected lesson indexes fixed at creation (null = full scope for
pre-F007 rows and ordinary first-generation starts).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f007b4d8e6f2"
down_revision: str | None = "f006a1c9e221"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("generation_runs", sa.Column("scope_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("generation_runs", "scope_json")

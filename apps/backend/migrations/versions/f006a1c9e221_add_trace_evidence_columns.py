"""add trace evidence columns for layered run evidence

Revision ID: f006a1c9e221
Revises: d5a9c1f3b7e4
Create Date: 2026-08-31 18:00:00.000000

F006 Layered Run Evidence: trace events gain nullable token usage and model
identifier columns; cost_usd becomes the write-time estimate (NULL = not
recorded). Legacy rows keep NULL usage and display as not recorded.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f006a1c9e221"
down_revision: str | None = "d5a9c1f3b7e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trace_events", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("trace_events", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("trace_events", sa.Column("model", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("trace_events", "model")
    op.drop_column("trace_events", "completion_tokens")
    op.drop_column("trace_events", "prompt_tokens")

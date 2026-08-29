"""free trace_events.run_id for generation runs

Revision ID: e7a2c50b9d31
Revises: c2f7d94e1a6b
Create Date: 2026-08-29 02:10:00.000000

The trace event log references runs polymorphically across discovery,
planning, and generation runs; the discovery-only foreign key is dropped.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7a2c50b9d31"
down_revision: str | None = "c2f7d94e1a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("trace_events_run_id_fkey", "trace_events", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key(
        "trace_events_run_id_fkey",
        "trace_events",
        "discovery_runs",
        ["run_id"],
        ["id"],
    )

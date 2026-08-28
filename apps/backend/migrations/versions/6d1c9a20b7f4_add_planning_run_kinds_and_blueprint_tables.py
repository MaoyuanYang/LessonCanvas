"""add planning run kinds and blueprint tables

Revision ID: 6d1c9a20b7f4
Revises: 35338f02204a
Create Date: 2026-08-28 16:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6d1c9a20b7f4"
down_revision: str | None = "35338f02204a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_PLANNING_STATUSES = "('initializing', 'questioning', 'drafting')"


def upgrade() -> None:
    op.add_column(
        "discovery_runs",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="discovery"),
    )
    op.add_column(
        "discovery_runs",
        sa.Column("brief_version_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_discovery_runs_brief_version",
        "discovery_runs",
        "brief_versions",
        ["brief_version_id"],
        ["id"],
    )
    op.create_index(
        "uq_active_planning_run",
        "discovery_runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text(f"kind = 'planning' AND status IN {ACTIVE_PLANNING_STATUSES}"),
    )

    op.create_table(
        "blueprint_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source_run_id", sa.UUID(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(["source_run_id"], ["discovery_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "revision", name="uq_blueprint_draft_revision"),
    )
    op.create_index(
        op.f("ix_blueprint_drafts_project_id"), "blueprint_drafts", ["project_id"], unique=False
    )

    op.create_table(
        "blueprint_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stale_brief_version_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(
            ["stale_brief_version_id"],
            ["brief_versions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "source_revision", name="uq_blueprint_version_source"),
        sa.UniqueConstraint("project_id", "version", name="uq_blueprint_version_number"),
    )
    op.create_index(
        op.f("ix_blueprint_versions_project_id"), "blueprint_versions", ["project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_blueprint_versions_project_id"), table_name="blueprint_versions")
    op.drop_table("blueprint_versions")
    op.drop_index(op.f("ix_blueprint_drafts_project_id"), table_name="blueprint_drafts")
    op.drop_table("blueprint_drafts")
    op.drop_index("uq_active_planning_run", table_name="discovery_runs")
    op.drop_constraint("fk_discovery_runs_brief_version", "discovery_runs", type_="foreignkey")
    op.drop_column("discovery_runs", "brief_version_id")
    op.drop_column("discovery_runs", "kind")

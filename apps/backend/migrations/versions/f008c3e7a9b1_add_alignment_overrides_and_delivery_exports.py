"""add alignment overrides and delivery exports

Revision ID: f008c3e7a9b1
Revises: f007b4d8e6f2
Create Date: 2026-09-01 10:00:00.000000

F008 Alignment Review and Delivery: teacher overrides for disputed
conflict-class severe findings, and version-bound delivery export records
(draft/validated ZIP package + printable-report snapshot).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f008c3e7a9b1"
down_revision: str | None = "f007b4d8e6f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alignment_overrides",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=False),
        sa.Column("blueprint_version_id", sa.UUID(), nullable=False),
        sa.Column("finding_key", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="recorded"),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"]),
        sa.UniqueConstraint(
            "project_id",
            "brief_version_id",
            "blueprint_version_id",
            "finding_key",
            "status",
            name="uq_alignment_override_active",
        ),
    )
    op.create_index("ix_alignment_overrides_project_id", "alignment_overrides", ["project_id"])
    op.create_index("ix_alignment_overrides_workspace_id", "alignment_overrides", ["workspace_id"])

    op.create_table(
        "delivery_exports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=False),
        sa.Column("blueprint_version_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("package_object_key", sa.Text(), nullable=True),
        sa.Column("report_object_key", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="building"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"]),
        sa.UniqueConstraint(
            "project_id",
            "brief_version_id",
            "blueprint_version_id",
            "label",
            "manifest_digest",
            name="uq_delivery_export_identity",
        ),
    )
    op.create_index("ix_delivery_exports_project_id", "delivery_exports", ["project_id"])
    op.create_index("ix_delivery_exports_workspace_id", "delivery_exports", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_delivery_exports_workspace_id", table_name="delivery_exports")
    op.drop_index("ix_delivery_exports_project_id", table_name="delivery_exports")
    op.drop_table("delivery_exports")
    op.drop_index("ix_alignment_overrides_workspace_id", table_name="alignment_overrides")
    op.drop_index("ix_alignment_overrides_project_id", table_name="alignment_overrides")
    op.drop_table("alignment_overrides")

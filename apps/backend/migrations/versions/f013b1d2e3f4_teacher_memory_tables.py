"""Teacher memory tables (F013, ADR-0005).

Revision ID: f013b1d2e3f4
Revises: f012a7c9d2e4
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "f013b1d2e3f4"
down_revision: str | None = "f012a7c9d2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("value", sa.String(32), nullable=True),
        sa.Column(
            "brief_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("brief_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "blueprint_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("blueprint_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "generation_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("generation_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "category", "content_hash", name="uq_memory_record_identity"
        ),
    )
    op.create_index("ix_memory_records_workspace_id", "memory_records", ["workspace_id"])

    op.create_table(
        "memory_passes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("trigger_kind", sa.String(24), nullable=False),
        sa.Column("trigger_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("proposal_count", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id", "trigger_kind", "trigger_id", name="uq_memory_pass_identity"
        ),
    )
    op.create_index("ix_memory_passes_workspace_id", "memory_passes", ["workspace_id"])

    op.create_table(
        "memory_proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "pass_id",
            UUID(as_uuid=True),
            sa.ForeignKey("memory_passes.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("value", sa.String(32), nullable=True),
        sa.Column(
            "brief_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("brief_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "blueprint_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("blueprint_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "generation_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("generation_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_proposals_workspace_id", "memory_proposals", ["workspace_id"])
    op.create_index("ix_memory_proposals_pass_id", "memory_proposals", ["pass_id"])

    op.create_table(
        "memory_project_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column(
            "workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "record_id",
            UUID(as_uuid=True),
            sa.ForeignKey("memory_records.id"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "record_id", name="uq_memory_override_identity"),
    )
    op.create_index(
        "ix_memory_project_overrides_project_id",
        "memory_project_overrides",
        ["project_id"],
    )
    op.create_index(
        "ix_memory_project_overrides_workspace_id",
        "memory_project_overrides",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_table("memory_project_overrides")
    op.drop_table("memory_proposals")
    op.drop_table("memory_passes")
    op.drop_table("memory_records")

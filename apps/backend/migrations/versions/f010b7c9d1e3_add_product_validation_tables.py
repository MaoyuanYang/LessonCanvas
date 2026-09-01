"""add product validation tables

Revision ID: f010b7c9d1e3
Revises: f009a1b2c3d4
Create Date: 2026-09-01 19:40:00.000000

F010 Teacher Product Validation: version-bound review assignments fixing
one complete package identity (dataset revision, confirmed pair, per-lesson
artifact checksums) and imported external-teacher rubric evidence with
deterministically computed outcomes (Spec D2/D5/D6/D8). Staleness is a
read-side derivation and stores no columns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f010b7c9d1e3"
down_revision: str | None = "f009a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_validation_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("unit_key", sa.String(length=64), nullable=False),
        sa.Column("dataset_revision", sa.String(length=32), nullable=False),
        sa.Column("brief_version_id", sa.UUID(), nullable=True),
        sa.Column("blueprint_version_id", sa.UUID(), nullable=True),
        sa.Column("package_json", sa.Text(), nullable=False),
        sa.Column("package_digest", sa.String(length=64), nullable=False),
        sa.Column("rubric_revision", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="pending_evidence"),
        sa.Column("not_complete_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concluded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["brief_version_id"], ["brief_versions.id"]),
        sa.ForeignKeyConstraint(["blueprint_version_id"], ["blueprint_versions.id"]),
        sa.UniqueConstraint(
            "project_id",
            "unit_key",
            "package_digest",
            name="uq_product_validation_assignment_identity",
        ),
    )
    op.create_index(
        "ix_product_validation_assignments_project_id",
        "product_validation_assignments",
        ["project_id"],
    )
    op.create_index(
        "ix_product_validation_assignments_workspace_id",
        "product_validation_assignments",
        ["workspace_id"],
    )

    op.create_table(
        "product_validation_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("evidence_revision", sa.String(length=32), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("capture_channel", sa.String(length=32), nullable=False),
        sa.Column("document_object_key", sa.Text(), nullable=True),
        sa.Column("document_filename", sa.String(length=255), nullable=True),
        sa.Column("document_content_type", sa.String(length=64), nullable=True),
        sa.Column("document_size_bytes", sa.Integer(), nullable=True),
        sa.Column("document_checksum", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("outcome_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="current"),
        sa.Column("superseded_by_evidence_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["product_validation_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_evidence_id"], ["product_validation_evidence.id"]
        ),
        sa.UniqueConstraint(
            "assignment_id",
            "evidence_revision",
            name="uq_product_validation_evidence_revision",
        ),
    )
    op.create_index(
        "ix_product_validation_evidence_assignment_id",
        "product_validation_evidence",
        ["assignment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_validation_evidence_assignment_id",
        table_name="product_validation_evidence",
    )
    op.drop_table("product_validation_evidence")
    op.drop_index(
        "ix_product_validation_assignments_workspace_id",
        table_name="product_validation_assignments",
    )
    op.drop_index(
        "ix_product_validation_assignments_project_id",
        table_name="product_validation_assignments",
    )
    op.drop_table("product_validation_assignments")

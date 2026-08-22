"""add immutable content snapshots and locked content packages

Revision ID: d4e8b6a1c902
Revises: cf7a0d6a10f2
Create Date: 2026-08-22 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8b6a1c902"
down_revision: Union[str, Sequence[str], None] = "cf7a0d6a10f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_versions",
        sa.Column("content_version_id", sa.String(length=96), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("interpretation_id", sa.String(length=112), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("change_reason", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interpretation_id"], ["interpretations.interpretation_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("content_version_id"),
        sa.UniqueConstraint("interpretation_id", "version_number", name="uq_content_version_number"),
    )
    op.create_table(
        "content_packages",
        sa.Column("package_id", sa.String(length=96), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("regulation_id", sa.String(length=64), nullable=False),
        sa.Column("pipeline_run_id", sa.String(length=96), nullable=False),
        sa.Column("package_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="HUMAN_LOCKED"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("locked_by", sa.String(length=128), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regulation_id"], ["regulations.regulation_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("package_id"),
        sa.UniqueConstraint("task_id", "package_version", name="uq_content_package_version"),
    )


def downgrade() -> None:
    op.drop_table("content_packages")
    op.drop_table("content_versions")

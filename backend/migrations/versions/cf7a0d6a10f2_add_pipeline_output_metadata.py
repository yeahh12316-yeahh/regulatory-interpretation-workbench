"""add S1-S4 pipeline output metadata

Revision ID: cf7a0d6a10f2
Revises: b2f3fd094106
Create Date: 2026-08-22 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cf7a0d6a10f2"
down_revision: Union[str, Sequence[str], None] = "b2f3fd094106"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("requirements", sa.Column("fact_class", sa.String(length=32), nullable=False, server_default="FACT"))
    op.add_column("requirements", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="needs_review"))
    op.add_column("requirements", sa.Column("structured_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("requirements", sa.Column("pipeline_run_id", sa.String(length=96), nullable=True))
    op.add_column("interpretations", sa.Column("fact_class", sa.String(length=32), nullable=False, server_default="INTERPRETATION"))
    op.add_column("interpretations", sa.Column("content_blocks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("interpretations", sa.Column("generated_by", sa.String(length=64), nullable=False, server_default="rule_based"))
    op.add_column("interpretations", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    op.add_column("interpretations", sa.Column("human_lock", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("interpretations", sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("interpretations", sa.Column("pipeline_run_id", sa.String(length=96), nullable=True))


def downgrade() -> None:
    for column in ("pipeline_run_id", "content_version", "human_lock", "prompt_version", "generated_by", "content_blocks", "fact_class"):
        op.drop_column("interpretations", column)
    for column in ("pipeline_run_id", "structured_data", "review_status", "fact_class"):
        op.drop_column("requirements", column)

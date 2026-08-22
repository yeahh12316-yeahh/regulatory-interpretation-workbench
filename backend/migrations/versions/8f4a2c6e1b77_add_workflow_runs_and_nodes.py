"""add durable workflow runs and node checkpoints

Revision ID: 8f4a2c6e1b77
Revises: d4e8b6a1c902
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f4a2c6e1b77"
down_revision: Union[str, Sequence[str], None] = "d4e8b6a1c902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("workflow_id", sa.String(length=96), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_node", sa.String(length=32), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("requested_from", sa.String(length=32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("error_state", sa.JSON(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("parent_workflow_id", sa.String(length=96), nullable=True),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workflow_id"),
    )
    op.create_index("ix_workflow_runs_task_id", "workflow_runs", ["task_id"])
    op.create_table(
        "workflow_nodes",
        sa.Column("node_id", sa.String(length=96), nullable=False),
        sa.Column("workflow_id", sa.String(length=96), nullable=False),
        sa.Column("node_name", sa.String(length=32), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("error_state", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_runs.workflow_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id"),
        sa.UniqueConstraint("workflow_id", "node_name", name="uq_workflow_node_name"),
    )
    op.create_index("ix_workflow_nodes_workflow_id", "workflow_nodes", ["workflow_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_nodes_workflow_id", table_name="workflow_nodes")
    op.drop_table("workflow_nodes")
    op.drop_index("ix_workflow_runs_task_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

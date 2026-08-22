"""scope regulations to organization workspaces

Revision ID: 3a7c2d1e9f44
Revises: d4e8b6a1c902
Create Date: 2026-08-22 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a7c2d1e9f44"
down_revision: Union[str, Sequence[str], None] = ("8f4a2c6e1b77", "d4e8b6a1c902")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("regulations", sa.Column("organization_id", sa.String(length=64), nullable=True))
    with op.batch_alter_table("regulations") as batch_op:
        batch_op.create_foreign_key(
            "fk_regulations_organization_id",
            "organizations",
            ["organization_id"],
            ["organization_id"],
            ondelete="SET NULL",
        )
    op.execute(
        sa.text(
            "UPDATE regulations SET organization_id = "
            "(SELECT organization_id FROM tasks WHERE tasks.regulation_id = regulations.regulation_id LIMIT 1) "
            "WHERE organization_id IS NULL"
        )
    )
    op.create_index("ix_regulations_organization_id", "regulations", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regulations_organization_id", table_name="regulations")
    with op.batch_alter_table("regulations") as batch_op:
        batch_op.drop_constraint("fk_regulations_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

"""link asset jobs to modification tasks

Revision ID: 8c73f26bda10
Revises: 4de0c2a9b7f1
Create Date: 2026-08-20 22:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "8c73f26bda10"
down_revision = "4de0c2a9b7f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset_jobs") as batch_op:
        batch_op.add_column(sa.Column("modification_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_asset_jobs_modification_id_modifications",
            "modifications",
            ["modification_id"],
            ["id"],
        )
        batch_op.create_index("ix_asset_jobs_modification_id", ["modification_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("asset_jobs") as batch_op:
        batch_op.drop_index("ix_asset_jobs_modification_id")
        batch_op.drop_constraint("fk_asset_jobs_modification_id_modifications", type_="foreignkey")
        batch_op.drop_column("modification_id")

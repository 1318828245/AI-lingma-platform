"""add persistent platform settings

Revision ID: a91b7c2d4e5f
Revises: f1a02d9b3c4e
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa

revision = "a91b7c2d4e5f"
down_revision = "f1a02d9b3c4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")

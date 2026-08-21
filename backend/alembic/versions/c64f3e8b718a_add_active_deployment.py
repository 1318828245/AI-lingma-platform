"""add active deployment

Revision ID: c64f3e8b718a
Revises: b193f24a50d2
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "c64f3e8b718a"
down_revision = "b193f24a50d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deployments", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("deployments", "is_active")

"""add deployment error

Revision ID: b193f24a50d2
Revises: 8c73f26bda10
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa

revision = "b193f24a50d2"
down_revision = "8c73f26bda10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deployments", sa.Column("error", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column("deployments", "error")

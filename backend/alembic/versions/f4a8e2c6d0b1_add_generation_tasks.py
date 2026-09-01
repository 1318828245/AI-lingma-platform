"""add resumable generation tasks

Revision ID: f4a8e2c6d0b1
Revises: d2c5a1f7b9e3
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa

revision = "f4a8e2c6d0b1"
down_revision = "d2c5a1f7b9e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generation_id", sa.Integer(), sa.ForeignKey("generations.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("generation_id", "sequence_no", name="uq_generation_tasks_sequence"),
    )
    op.create_index("ix_generation_tasks_generation_id", "generation_tasks", ["generation_id"])


def downgrade() -> None:
    op.drop_table("generation_tasks")

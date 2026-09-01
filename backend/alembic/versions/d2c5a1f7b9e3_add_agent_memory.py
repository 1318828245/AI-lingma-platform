"""add auditable agent context and summary memory

Revision ID: d2c5a1f7b9e3
Revises: a91b7c2d4e5f
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa

revision = "d2c5a1f7b9e3"
down_revision = "a91b7c2d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_context_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("generation_id", sa.Integer(), sa.ForeignKey("generations.id")),
        sa.Column("modification_id", sa.Integer(), sa.ForeignKey("modifications.id")),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("owner_id", "project_id", "session_id", "generation_id", "modification_id"):
        op.create_index(f"ix_agent_context_snapshots_{column}", "agent_context_snapshots", [column])
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id")),
        sa.Column("scope", sa.String(length=24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_message_id", sa.Integer()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "project_id", "session_id", "scope", name="uq_agent_memory_scope"),
    )
    for column in ("owner_id", "project_id", "session_id"):
        op.create_index(f"ix_agent_memories_{column}", "agent_memories", [column])


def downgrade() -> None:
    op.drop_table("agent_memories")
    op.drop_table("agent_context_snapshots")

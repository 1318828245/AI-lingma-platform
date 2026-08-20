"""add async asset collection tables

Revision ID: 4de0c2a9b7f1
Revises: 1c4243ee8fbd
Create Date: 2026-08-20 17:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "4de0c2a9b7f1"
down_revision = "1c4243ee8fbd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["generation_id"], ["generations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_jobs_project_id"), "asset_jobs", ["project_id"], unique=False)
    op.create_index(op.f("ix_asset_jobs_generation_id"), "asset_jobs", ["generation_id"], unique=False)
    op.create_index(op.f("ix_asset_jobs_session_id"), "asset_jobs", ["session_id"], unique=False)
    op.create_table(
        "project_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("asset_job_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("usage_role", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("local_path", sa.String(length=255), nullable=True),
        sa.Column("license_name", sa.String(length=128), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["asset_job_id"], ["asset_jobs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_assets_project_id"), "project_assets", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_assets_asset_job_id"), "project_assets", ["asset_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_assets_asset_job_id"), table_name="project_assets")
    op.drop_index(op.f("ix_project_assets_project_id"), table_name="project_assets")
    op.drop_table("project_assets")
    op.drop_index(op.f("ix_asset_jobs_session_id"), table_name="asset_jobs")
    op.drop_index(op.f("ix_asset_jobs_generation_id"), table_name="asset_jobs")
    op.drop_index(op.f("ix_asset_jobs_project_id"), table_name="asset_jobs")
    op.drop_table("asset_jobs")

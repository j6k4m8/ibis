"""Add original_created_at to videos.

Revision ID: 0006_video_original_created_at
Revises: 0005_processing_jobs
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_video_original_created_at"
down_revision = "0005_processing_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("original_created_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("videos", "original_created_at")

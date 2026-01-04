"""Add thumbnail metadata to videos.

Revision ID: 0007_video_thumbnail_key
Revises: 0006_video_original_created_at
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_video_thumbnail_key"
down_revision = "0006_video_original_created_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("thumbnail_key", sa.String(length=1024)))


def downgrade() -> None:
    op.drop_column("videos", "thumbnail_key")

"""Add video start/end ranges to notes.

Revision ID: 0003_video_ranges
Revises: 0002_tasks
Create Date: 2025-01-03 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_video_ranges"
down_revision = "0002_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("video_start_seconds", sa.Float(), nullable=True))
    op.add_column("notes", sa.Column("video_end_seconds", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("notes", "video_end_seconds")
    op.drop_column("notes", "video_start_seconds")

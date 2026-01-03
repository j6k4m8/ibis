"""Add video upload metadata.

Revision ID: 0004_video_uploads
Revises: 0003_video_ranges
Create Date: 2025-01-04 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_video_uploads"
down_revision = "0003_video_ranges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("videos")}

    if "file_size_bytes" not in existing:
        op.add_column("videos", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    if "original_filename" not in existing:
        op.add_column(
            "videos", sa.Column("original_filename", sa.String(length=255), nullable=True)
        )
    if "mime_type" not in existing:
        op.add_column("videos", sa.Column("mime_type", sa.String(length=255), nullable=True))
    if "user_id" not in existing:
        with op.batch_alter_table("videos") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("videos")}

    if "user_id" in existing:
        with op.batch_alter_table("videos") as batch_op:
            batch_op.drop_column("user_id")
    if "mime_type" in existing:
        op.drop_column("videos", "mime_type")
    if "original_filename" in existing:
        op.drop_column("videos", "original_filename")
    if "file_size_bytes" in existing:
        op.drop_column("videos", "file_size_bytes")

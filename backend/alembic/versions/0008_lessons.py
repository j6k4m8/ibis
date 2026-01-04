"""Add lessons and membership tables.

Revision ID: 0008_lessons
Revises: 0007_video_thumbnail_key
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0008_lessons"
down_revision = "0007_video_thumbnail_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    user_columns = {col["name"] for col in inspector.get_columns("users")}

    if "lesson_autogroup_hours" not in user_columns:
        op.add_column(
            "users",
            sa.Column("lesson_autogroup_hours", sa.Integer(), nullable=False, server_default="4"),
        )

    if "lessons" not in existing_tables:
        op.create_table(
            "lessons",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "lesson_notes" not in existing_tables:
        op.create_table(
            "lesson_notes",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("lesson_id", sa.String(length=36), nullable=False),
            sa.Column("note_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
            sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("lesson_id", "note_id", name="uq_lesson_note"),
        )

    if "lesson_videos" not in existing_tables:
        op.create_table(
            "lesson_videos",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("lesson_id", sa.String(length=36), nullable=False),
            sa.Column("video_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
            sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("lesson_id", "video_id", name="uq_lesson_video"),
        )

    if "lesson_autogroup_hours" not in user_columns and bind.dialect.name != "sqlite":
        op.alter_column("users", "lesson_autogroup_hours", server_default=None)


def downgrade() -> None:
    op.drop_table("lesson_videos")
    op.drop_table("lesson_notes")
    op.drop_table("lessons")
    op.drop_column("users", "lesson_autogroup_hours")

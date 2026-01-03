"""Add tasks table.

Revision ID: 0002_tasks
Revises: 0001_initial
Create Date: 2025-01-02 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_tasks"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("note_id", sa.String(length=36), sa.ForeignKey("notes.id"), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column(
            "completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "occurrence",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tasks")

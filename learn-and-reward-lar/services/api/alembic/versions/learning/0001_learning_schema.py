"""Learning schema (Mission B — Developer B scope, README section 8.4).

Creates the ``learning`` schema with courses, lessons, exercises, enrollments,
practice_sessions, chat_messages and certificates.

Revision ID: 0001_learning_schema
Revises: 0001_core_placeholder
Create Date: 2026-09-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_learning_schema"
down_revision = "0001_core_placeholder"
branch_labels = None
depends_on = None

LEARNING = "learning"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {LEARNING}")

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("language", sa.String(12), nullable=False, server_default="lb"),
        sa.Column("level", sa.String(32), nullable=False, server_default="beginner"),
        sa.Column("price_coins", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("community_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema=LEARNING,
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("vocabulary", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["course_id"], [f"{LEARNING}.courses.id"], ondelete="CASCADE"),
        schema=LEARNING,
    )

    op.create_table(
        "exercises",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("type", sa.String(32), nullable=False, server_default="multiple_choice"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", JSONB(), nullable=True),
        sa.Column("answer", JSONB(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["lesson_id"], [f"{LEARNING}.lessons.id"], ondelete="CASCADE"),
        schema=LEARNING,
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("completed_lesson_ids", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], [f"{LEARNING}.courses.id"]),
        sa.UniqueConstraint("course_id", "user_id", name="uq_enrollment_course_user"),
        schema=LEARNING,
    )

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("kind", sa.String(32), nullable=False, server_default="lesson_exercises"),
        sa.Column("status", sa.String(32), nullable=False, server_default="in_progress"),
        sa.Column("total_exercises", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_exercises", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coins_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], [f"{LEARNING}.lessons.id"]),
        schema=LEARNING,
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["session_id"], [f"{LEARNING}.practice_sessions.id"], ondelete="CASCADE"
        ),
        schema=LEARNING,
    )

    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True, index=True),
        sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("course_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["course_id"], [f"{LEARNING}.courses.id"]),
        schema=LEARNING,
    )


def downgrade() -> None:
    op.drop_table("certificates", schema=LEARNING)
    op.drop_table("chat_messages", schema=LEARNING)
    op.drop_table("practice_sessions", schema=LEARNING)
    op.drop_table("enrollments", schema=LEARNING)
    op.drop_table("exercises", schema=LEARNING)
    op.drop_table("lessons", schema=LEARNING)
    op.drop_table("courses", schema=LEARNING)
    op.execute(f"DROP SCHEMA IF EXISTS {LEARNING}")

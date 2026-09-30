"""Placeholder core schema for Mission B (Developer C scope).

Mission B requires authentication to function and the repository is empty, so this
migration creates the minimal ``core.users`` table used by the JWT shim. When
Developer C's real core module lands, replace this migration chain with the proper
core schema (users, communities, roles, community_members).

Revision ID: 0001_core_placeholder
Revises:
Create Date: 2026-09-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_core_placeholder"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="learner"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema="core",
    )


def downgrade() -> None:
    op.drop_table("users", schema="core")
    op.execute("DROP SCHEMA IF EXISTS core")

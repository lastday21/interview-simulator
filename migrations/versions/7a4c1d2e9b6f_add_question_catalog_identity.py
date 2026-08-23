"""add question catalog identity

Revision ID: 7a4c1d2e9b6f
Revises: 2f8d9e5c1a4b
Create Date: 2026-08-23 16:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "7a4c1d2e9b6f"
down_revision = "2f8d9e5c1a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("external_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("source_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        op.f("ix_questions_external_id"),
        "questions",
        ["external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_questions_external_id"), table_name="questions")
    op.drop_column("questions", "source_id")
    op.drop_column("questions", "external_id")

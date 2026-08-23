"""add trainer callback guard

Revision ID: 2f8d9e5c1a4b
Revises: 9c18e24a310b
Create Date: 2026-08-23 16:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "2f8d9e5c1a4b"
down_revision = "9c18e24a310b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_question_status",
        sa.Column("last_trainer_message_id", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_question_status", "last_trainer_message_id")

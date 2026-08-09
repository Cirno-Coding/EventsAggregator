"""create outbox table

Revision ID: a7faea498145
Revises: 3bc84d8a852d
Create Date: 2026-08-09 07:52:00.695404

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7faea498145"
down_revision: Union[str, None] = "3bc84d8a852d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создать таблицу сообщений Transactional Outbox."""
    op.create_table(
        "outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_pending_created_at", "outbox", ["created_at"], unique=False, postgresql_where=sa.text("status = 'pending'"))


def downgrade() -> None:
    """Удалить таблицу сообщений Transactional Outbox."""
    op.drop_index("ix_outbox_pending_created_at", table_name="outbox")
    op.drop_table("outbox")

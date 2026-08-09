"""create ticket idempotency table

Revision ID: 4b02b461e1d0
Revises: a7faea498145
Create Date: 2026-08-09 13:02:55.997029

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b02b461e1d0"
down_revision: Union[str, None] = "a7faea498145"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создать таблицу ключей идемпотентности регистрации билетов."""
    op.create_table(
        "ticket_idempotency_keys",
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("ticket_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )
    op.create_index(op.f("ix_ticket_idempotency_keys_expires_at"), "ticket_idempotency_keys", ["expires_at"], unique=False)


def downgrade() -> None:
    """Удалить таблицу ключей идемпотентности регистрации билетов."""
    op.drop_index(op.f("ix_ticket_idempotency_keys_expires_at"), table_name="ticket_idempotency_keys")
    op.drop_table("ticket_idempotency_keys")

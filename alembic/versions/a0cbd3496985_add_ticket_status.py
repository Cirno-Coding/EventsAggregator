"""add ticket status

Revision ID: a0cbd3496985
Revises: 4b02b461e1d0
Create Date: 2026-08-09 17:09:55.778593

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0cbd3496985"
down_revision: Union[str, None] = "4b02b461e1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить статус в таблицу локальных билетов."""
    op.add_column("tickets", sa.Column("status", sa.String(length=50), server_default=sa.text("'active'"), nullable=False))
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)


def downgrade() -> None:
    """Удалить статус локальных билетов."""
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_column("tickets", "status")

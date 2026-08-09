from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TicketIdempotencyKey(Base):
    """
    Результат успешной регистрации, сохранённый по ключу идемпотентности.

    Запись позволяет вернуть тот же ticket_id при повторной отправке
    идентичного запроса и не создавать дубликат билета.
    """

    __tablename__ = "ticket_idempotency_keys"

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

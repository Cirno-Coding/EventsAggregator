from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent, OutboxEventType, OutboxStatus


class OutboxRepository:
    """Репозиторий сообщений Transactional Outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, event_type: OutboxEventType, payload: dict[str, Any]) -> OutboxEvent:
        """
        Создать ожидающее отправки outbox-сообщение.
        Метод не выполняет commit: вызывающий код сможет сохранить сообщение
        в одной транзакции с билетом.
        """
        event = OutboxEvent(
            id=uuid4(),
            event_type=event_type.value,
            payload=payload,
            status=OutboxStatus.PENDING.value,
            created_at=datetime.now(timezone.utc),
            sent_at=None,
        )
        self._session.add(event)

        return event

    async def get_pending(self, *, limit: int) -> list[OutboxEvent]:
        """Вернуть ограниченную пачку ожидающих отправки сообщений."""
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.PENDING.value)
            .order_by(
                OutboxEvent.created_at.asc(),
                OutboxEvent.id.asc(),
            )
            .limit(limit),
        )

        return list(result.scalars().all())

    async def get_pending_by_id(self, event_id: UUID) -> OutboxEvent | None:
        """Вернуть ожидающее сообщение по UUID или None."""
        result = await self._session.execute(
            select(OutboxEvent).where(
                OutboxEvent.id == event_id,
                OutboxEvent.status == OutboxStatus.PENDING.value,
            ),
        )

        return result.scalar_one_or_none()

    async def mark_sent(self, event: OutboxEvent) -> None:
        """
        Пометить сообщение успешно отправленным.

        Фиксацию транзакции выполняет вызывающий worker.
        """
        event.status = OutboxStatus.SENT.value
        event.sent_at = datetime.now(timezone.utc)

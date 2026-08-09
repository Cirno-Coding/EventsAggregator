import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TypeAlias
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import OutboxEvent
from app.repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)

OutboxEventHandler: TypeAlias = Callable[[OutboxEvent], Awaitable[None]]


class OutboxWorker:
    """Фоновый worker для гарантированной доставки outbox-сообщения"""

    def __init__(
        self, *, session_factory: async_sessionmaker[AsyncSession], handler: OutboxEventHandler, batch_size: int, poll_interval_seconds: int
    ) -> None:
        self._session_factory = session_factory
        self._handler = handler
        self._batch_size = batch_size
        self._poll_interval_seconds = poll_interval_seconds

    async def process_once(self) -> int:
        """Обработать одну пачку ожидающих outbox-сообщений."""
        event_ids = await self._get_pending_event_ids()
        processed_count = 0
        for event_id in event_ids:
            if await self._process_event(event_id):
                processed_count += 1
        return processed_count

    async def run_forever(self) -> None:
        """Периодически запускать обработку ожидающих сообщений."""
        while True:
            try:
                await self.process_once()
            except Exception:
                logger.exception("Итерация outbox-worker завершилась ошибкой.")

            await asyncio.sleep(self._poll_interval_seconds)

    async def _get_pending_event_ids(self) -> list[UUID]:
        """Получить UUID очередной пачки ожидающих сообщений."""
        async with self._session_factory() as session:
            repository = OutboxRepository(session)
            events = await repository.get_pending(limit=self._batch_size)

            return [event.id for event in events]

    async def _process_event(self, event_id: UUID) -> bool:
        """
        Отправить одно сообщение и отметить его как sent.

        При любой ошибке транзакция откатывается, поэтому событие остаётся
        pending и будет повторно обработано в следующей итерации.
        """
        async with self._session_factory() as session:
            repository = OutboxRepository(session)
            event = await repository.get_pending_by_id(event_id)

            if event is None:
                return False

            try:
                await self._handler(event)
                await repository.mark_sent(event)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Не удалось обработать outbox-событие %s.", event_id)
                return False
        return True


def start_background_outbox(worker: OutboxWorker) -> asyncio.Task[None]:
    """Запустить фоновый outbox-worker."""
    return asyncio.create_task(worker.run_forever(), name="outbox-worker")


async def stop_background_outbox(task: asyncio.Task[None]) -> None:
    """Остановить outbox-worker и дождаться завершения задачи."""
    task.cancel()

    with suppress(asyncio.CancelledError):
        await task

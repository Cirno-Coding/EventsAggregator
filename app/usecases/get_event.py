from uuid import UUID

from app.db.models import Event
from app.repositories.events import EventRepository


class GetEventUseCase:
    """Получить одно событие из локальной БД."""

    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    async def execute(self, event_id: UUID) -> Event | None:
        """Вернуть событие вместе с площадкой или None, если оно не найдено."""
        return await self._repository.get_by_id(event_id)

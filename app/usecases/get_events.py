from datetime import date

from app.db.models import Event
from app.repositories.events import EventRepository


class GetEventsUseCase:
    """Получить страницу событий из локальной БД."""

    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Event]]:
        """Вернуть общее количество и события выбранной страницы."""
        return await self._repository.list(date_from=date_from, page=page, page_size=page_size)

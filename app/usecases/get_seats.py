from uuid import UUID

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus
from app.repositories.events import EventRepository


class EventNotFoundError(Exception):
    """Событие отсутствует в локальной БД."""


class EventNotPublishedError(Exception):
    """Событие не опубликовано и не может иметь доступных мест."""


class GetSeatsUseCase:
    """Получить актуальный список свободных мест для опубликованного события."""

    def __init__(self, *, events_repository: EventRepository, client: EventsProviderClient, cache: TTLCache[list[str]]) -> None:
        self._events_repository = events_repository
        self._client = client
        self._cache = cache

    async def execute(self, event_id: UUID) -> list[str]:
        """Вернуть свобдные места из кэша или Events Provider API."""
        event = await self._events_repository.get_by_id(event_id)

        if event is None:
            raise EventNotFoundError()

        if event.status != EventStatus.PUBLISHED.value:
            raise EventNotPublishedError()

        cache_key = str(event_id)
        cached_seats = self._cache.get(cache_key)

        if cached_seats is not None:
            return cached_seats

        seats = await self._client.get_available_seats(event_id)
        self._cache.set(cache_key, seats)

        return seats

from uuid import UUID

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus
from app.repositories.events import EventRepository
from app.repositories.tickets import TicketRepository


class EventNotFoundError(Exception):
    """Событие отсутствует в локальной БД."""


class EventNotPublishedError(Exception):
    """Событие не опубликовано и недоступно для регистрации."""


class CreateTicketUseCase:
    """Зарегистрировать посетителя на опубликованное событие."""

    def __init__(
        self,
        *,
        events_repository: EventRepository,
        tickets_repository: TicketRepository,
        client: EventsProviderClient,
        seats_cache: TTLCache[list[str]],
    ) -> None:
        self._events_repository = events_repository
        self._tickets_repository = tickets_repository
        self._client = client
        self._seats_cache = seats_cache

    async def execute(self, *, event_id: UUID, first_name: str, last_name: str, email: str, seat: str) -> UUID:
        """Создать регистрацию у Provider API и сохранить билет локально."""
        event = await self._events_repository.get_by_id(event_id)

        if event is None:
            raise EventNotFoundError()

        if event.status != EventStatus.PUBLISHED.value:
            raise EventNotPublishedError()

        ticket_id = await self._client.register(event_id=event.id, first_name=first_name, last_name=last_name, email=email, seat=seat)

        await self._tickets_repository.create(
            ticket_id=ticket_id, event_id=event.id, first_name=first_name, last_name=last_name, email=email, seat=seat
        )

        self._seats_cache.delete(str(event.id))

        return ticket_id

from uuid import UUID

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus, OutboxEventType
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
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
        outbox_repository: OutboxRepository,
        client: EventsProviderClient,
        seats_cache: TTLCache[list[str]],
    ) -> None:
        self._events_repository = events_repository
        self._tickets_repository = tickets_repository
        self._outbox_repository = outbox_repository
        self._client = client
        self._seats_cache = seats_cache

    async def execute(self, *, event_id: UUID, first_name: str, last_name: str, email: str, seat: str) -> UUID:
        """
        Зарегистрировать посетителя и добавить сообщение в Transactional Outbox.

        Commit не выполняется в use case: билет и outbox-событие фиксируются
        одной транзакцией в API-слое.
        """
        event = await self._events_repository.get_by_id(event_id)

        if event is None:
            raise EventNotFoundError()

        if event.status != EventStatus.PUBLISHED.value:
            raise EventNotPublishedError()

        ticket_id = await self._client.register(event_id=event.id, first_name=first_name, last_name=last_name, email=email, seat=seat)

        await self._tickets_repository.create(
            ticket_id=ticket_id, event_id=event.id, first_name=first_name, last_name=last_name, email=email, seat=seat
        )

        await self._outbox_repository.create(
            event_type=OutboxEventType.TICKET_PURCHASED,
            payload={"ticket_id": str(ticket_id), "event_id": str(event.id), "event_name": event.name, "seat": seat},
        )

        self._seats_cache.delete(str(event.id))

        return ticket_id

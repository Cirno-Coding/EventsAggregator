from uuid import UUID

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.db.models import TicketStatus
from app.repositories.tickets import TicketRepository


class TicketNotFoundError(Exception):
    """Активный билет отсутствует в локальной БД."""


class DeleteTicketUseCase:
    """Отменить регистрацию посетителя на событие."""

    def __init__(self, *, tickets_repository: TicketRepository, client: EventsProviderClient, seats_cache: TTLCache[list[str]]) -> None:
        self._tickets_repository = tickets_repository
        self._client = client
        self._seats_cache = seats_cache

    async def execute(self, ticket_id: UUID) -> None:
        """
        Отменить регистрацию у Provider API и пометить локальный билет отменённым.

        Повторная отмена не вызывает Provider API: билет со статусом cancelled
        считается недоступным для новой отмены.
        """
        ticket = await self._tickets_repository.get_by_id(ticket_id)

        if ticket is None or ticket.status != TicketStatus.ACTIVE.value:
            raise TicketNotFoundError()

        await self._client.unregister(event_id=ticket.event_id, ticket_id=ticket.id)

        await self._tickets_repository.mark_cancelled(ticket)
        self._seats_cache.delete(str(ticket.event_id))

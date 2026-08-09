import hashlib
import json
from uuid import UUID

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus, OutboxEventType
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.ticket_idempotency import TicketIdempotencyRepository
from app.repositories.tickets import TicketRepository


def build_request_fingerprint(
    *,
    event_id: UUID,
    first_name: str,
    last_name: str,
    email: str,
    seat: str,
) -> str:
    """
    Построить стабильный SHA-256-хеш значимых данных запроса.

    Хеш позволяет сравнивать запросы, не сохраняя повторно персональные данные
    посетителя в таблице ключей идемпотентности.
    """
    payload = {
        "email": email,
        "event_id": str(event_id),
        "first_name": first_name,
        "last_name": last_name,
        "seat": seat,
    }
    serialized_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


class EventNotFoundError(Exception):
    """Событие отсутствует в локальной БД."""


class EventNotPublishedError(Exception):
    """Событие не опубликовано и недоступно для регистрации."""


class IdempotencyConflictError(Exception):
    """Ключ идемпотентности уже использован с другими данными запроса."""


class CreateTicketUseCase:
    """Зарегистрировать посетителя на опубликованное событие."""

    def __init__(
        self,
        *,
        events_repository: EventRepository,
        tickets_repository: TicketRepository,
        outbox_repository: OutboxRepository,
        idempotency_repository: TicketIdempotencyRepository,
        client: EventsProviderClient,
        seats_cache: TTLCache[list[str]],
    ) -> None:
        self._events_repository = events_repository
        self._tickets_repository = tickets_repository
        self._outbox_repository = outbox_repository
        self._idempotency_repository = idempotency_repository
        self._client = client
        self._seats_cache = seats_cache

    async def execute(
        self,
        *,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
        idempotency_key: str | None,
        idempotency_ttl_seconds: int,
    ) -> UUID:
        """
        Зарегистрировать посетителя и добавить сообщение в Transactional Outbox.

        При наличии idempotency_key повторный идентичный запрос вернёт
        уже сохранённый ticket_id без нового вызова Events Provider API.
        """
        request_fingerprint: str | None = None

        if idempotency_key is not None:
            request_fingerprint = build_request_fingerprint(
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )

            await self._idempotency_repository.acquire_lock(idempotency_key)
            await self._idempotency_repository.delete_expired()

            existing_record = await self._idempotency_repository.get_by_key(
                idempotency_key,
            )
            if existing_record is not None:
                if existing_record.request_fingerprint != request_fingerprint:
                    raise IdempotencyConflictError()

                return existing_record.ticket_id

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

        if idempotency_key is not None and request_fingerprint is not None:
            await self._idempotency_repository.create(
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                ticket_id=ticket_id,
                ttl_seconds=idempotency_ttl_seconds,
            )

        self._seats_cache.delete(str(event.id))

        return ticket_id

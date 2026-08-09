from typing import Any

from app.clients.capashino import CapashinoClient
from app.db.models import OutboxEvent, OutboxEventType


class UnsupportedOutboxEventError(Exception):
    """Worker получил событие неподдерживаемого типа."""


class InvalidOutboxPayloadError(Exception):
    """Payload outbox-события не содержит обязательные данные."""


class CapashinoOutboxHandler:
    """Обработчик outbox-события покупки билета для Capashino"""

    def __init__(self, client: CapashinoClient) -> None:
        self._client = client

    async def __call__(self, event: OutboxEvent) -> None:
        """Отправить уведомление Capashino по данным outbox-события."""
        if event.event_type != OutboxEventType.TICKET_PURCHASED.value:
            raise UnsupportedOutboxEventError(f"Неподдерживаемый тип outbox-события: {event.event_type}")

        ticket_id = self._get_required_string(event.payload, field_name="ticket_id", event_id=event.id)
        event_name = self._get_required_string(event.payload, field_name="event_name", event_id=event.id)
        seat = self._get_required_string(event.payload, field_name="seat", event_id=event.id)

        await self._client.create_notification(
            message=f"Вы успешно зарегистрированы на мероприятие «{event_name}». Ваше место: {seat}",
            reference_id=ticket_id,
            idempotency_key=str(event.id),
        )

    @staticmethod
    def _get_required_string(payload: dict[str, Any], *, field_name: str, event_id: object) -> str:
        """Извлечь непустую строку из JSON-payload."""
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise InvalidOutboxPayloadError(f"Outbox-событие {event_id} не содержит поле {field_name}.")

        return value

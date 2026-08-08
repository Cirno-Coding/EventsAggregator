from datetime import datetime
from typing import TypedDict


class ProviderPlaceData(TypedDict):
    """
    Данные площадки из ответа Events Provider API
    """

    id: str
    name: str
    city: str
    address: str
    seats_pattern: str
    changed_at: str
    created_at: str


class ProviderEventData(TypedDict):
    """
    Данные события из ответа Events Provider API
    """

    id: str
    name: str
    place: ProviderPlaceData
    event_time: str
    registration_deadline: str
    status: str
    number_of_visitors: int
    changed_at: str
    created_at: str
    status_changed_at: str


class ProviderEventsPageData(TypedDict):
    """
    Страница событий при cursor-пагинации Provider API.
    """

    next: str | None
    previous: str | None
    results: list[ProviderEventData]


class ProviderSeatsData(TypedDict):
    """
    Список свободных мест из Provider API.
    """

    seats: list[str]


class ProviderTicketData(TypedDict):
    """
    Данные созданного билета из Provider API.
    """

    ticket_id: str


class ProviderUnregisterData(TypedDict):
    """
    Ответ Provider API на отмену регистрации.
    """

    success: bool


def parse_provider_datetime(value: str) -> datetime:
    """Преобразовать ISO-дату Provider API в datetime с часовым поясом."""
    normalized_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed_value = datetime.fromisoformat(normalized_value)

    if parsed_value.tzinfo is None:
        raise ValueError("Дата от Events Provider API должна содержать часовой пояс.")

    return parsed_value

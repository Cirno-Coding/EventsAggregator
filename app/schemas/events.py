from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlaceShortResponse(BaseModel):
    """Краткое описание площадки в списке событий."""

    id: UUID
    name: str
    city: str
    address: str

    model_config = ConfigDict(from_attributes=True)


class PlaceDetailResponse(PlaceShortResponse):
    """Подробное описание площадки."""

    seats_pattern: str


class EventListItemResponse(BaseModel):
    """Одно событие в ответе со списком событий."""

    id: UUID
    name: str
    place: PlaceShortResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(BaseModel):
    """Подробная информация о событии."""

    id: UUID
    name: str
    place: PlaceDetailResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    """Страница списка событий."""

    count: int
    next: str | None
    previous: str | None
    results: list[EventListItemResponse]


class SeatsResponse(BaseModel):
    """Список свободных мест для одного события."""

    event_id: UUID
    available_seats: list[str]

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contracts.events_provider import ProviderEventData
from app.db.models import Event, Place


def parse_datetime(value: str) -> datetime:
    """
    Преобразовать ISO-дату Provider API в datetime с часовым поясом.
    """

    normalized_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed_value = datetime.fromisoformat(normalized_value)

    if parsed_value.tzinfo is None:
        raise ValueError("Дата от Events Provider API должна содержать часовой пояс.")

    return parsed_value


class EventRepository:
    """
    Репозиторий событий и связанных с ними площадок.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: UUID) -> Event | None:
        """
        Вернуть событие вместе с площадкой или None, если оно не найдено.
        """
        result = await self._session.execute(select(Event).options(selectinload(Event.place)).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def list(self, *, date_from: date | None = None, page: int, page_size: int) -> tuple[int, list[Event]]:
        """
        Вернуть общее число событий и запрошенную страницу результатов.
        """
        events_query = select(Event).options(selectinload(Event.place))
        count_query = select(func.count()).select_from(Event)

        if date_from is not None:
            events_query = events_query.where(Event.event_time >= date_from)
            count_query = count_query.where(Event.event_time >= date_from)

        events_query = events_query.order_by(Event.event_time.asc(), Event.id.asc()).offset((page - 1) * page_size).limit(page_size)

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        events_result = await self._session.execute(events_query)
        events = list(events_result.scalars().all())

        return total, events

    async def upsert_event_with_place(self, event_data: ProviderEventData) -> None:
        """
        Создать или обновить событие и его площадку по данным Provider API.
        """
        place_data = event_data["place"]

        place = Place(
            id=UUID(place_data["id"]),
            name=place_data["name"],
            city=place_data["city"],
            address=place_data["address"],
            seats_pattern=place_data["seats_pattern"],
            changed_at=parse_datetime(place_data["changed_at"]),
            created_at=parse_datetime(place_data["created_at"]),
        )

        event = Event(
            id=UUID(event_data["id"]),
            name=event_data["name"],
            place_id=place.id,
            event_time=parse_datetime(event_data["event_time"]),
            registration_deadline=parse_datetime(event_data["registration_deadline"]),
            status=event_data["status"],
            number_of_visitors=event_data["number_of_visitors"],
            changed_at=parse_datetime(event_data["changed_at"]),
            created_at=parse_datetime(event_data["created_at"]),
            status_changed_at=parse_datetime(event_data["status_changed_at"]),
        )

        await self._session.merge(place)
        await self._session.merge(event)

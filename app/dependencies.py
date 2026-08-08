from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.seats import seats_cache
from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.core.config import Settings, get_settings
from app.core.database import get_async_session
from app.repositories.events import EventRepository
from app.repositories.tickets import TicketRepository


def get_app_settings() -> Settings:
    """Вернуть общие настройки приложения."""
    return get_settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Выдать сессию БД для запроса и закрыть её после обработки."""
    async for session in get_async_session():
        yield session


def get_event_repository(session: AsyncSession = Depends(get_db_session)) -> EventRepository:
    """Создать репозиторий событий для текущего запроса."""
    return EventRepository(session)


def get_ticket_repository(session: AsyncSession = Depends(get_db_session)) -> TicketRepository:
    """Создать репозиторий билетов для текущего запроса."""
    return TicketRepository(session)


async def get_events_provider_client(settings: Settings = Depends(get_app_settings)) -> AsyncGenerator[EventsProviderClient, None]:
    """Создать HTTP-клиент Provider API и закрыть его после запроса."""
    if not settings.events_provider_base_url:
        raise RuntimeError("Не задана переменная EVENTS_PROVIDER_BASE_URL.")

    if not settings.events_provider_api_key:
        raise RuntimeError("Не задана переменная EVENTS_PROVIDER_API_KEY.")

    client = EventsProviderClient(base_url=settings.events_provider_base_url, api_key=settings.events_provider_api_key)

    try:
        yield client
    finally:
        await client.close()


def get_seats_cache() -> TTLCache[list[str]]:
    """Вернуть общий кэш свободных мест."""
    return seats_cache

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_async_session
from app.repositories.events import EventRepository


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

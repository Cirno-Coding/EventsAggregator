from collections.abc import AsyncIterable, Callable
from datetime import date, datetime
from typing import TypeAlias

from app.contracts.events_provider import ProviderEventData, parse_provider_datetime
from app.repositories.events import EventRepository
from app.repositories.sync_metadata import SyncMetadataRepository

FIRST_SYNC_DATE = date(2000, 1, 1)

PaginatorFactory: TypeAlias = Callable[
    [date],
    AsyncIterable[ProviderEventData],
]


class SyncEventsUseCase:
    """Синхронизировать события Provider API с локальной базой данных."""

    def __init__(
        self,
        *,
        events_repository: EventRepository,
        metadata_repository: SyncMetadataRepository,
        paginator_factory: PaginatorFactory,
    ) -> None:
        self._events_repository = events_repository
        self._metadata_repository = metadata_repository
        self._paginator_factory = paginator_factory

    async def execute(self) -> datetime | None:
        """Синхронизировать события и вернуть максимальное changed_at"""
        metadata = await self._metadata_repository.get_or_create()

        changed_at = FIRST_SYNC_DATE if metadata.last_changed_at is None else metadata.last_changed_at.date()
        paginator = self._paginator_factory(changed_at)
        last_changed_at = metadata.last_changed_at

        async for event_data in paginator:
            await self._events_repository.upsert_event_with_place(event_data)

            event_changed_at = parse_provider_datetime(event_data["changed_at"])

            if last_changed_at is None or event_changed_at > last_changed_at:
                last_changed_at = event_changed_at

        return last_changed_at

from collections.abc import AsyncIterator
from datetime import date
from typing import Protocol

from app.contracts.events_provider import ProviderEventData, ProviderEventsPageData


class EventsPageClientProtocol(Protocol):
    """Контракт клиента, умеющего загружать страницы событий."""

    async def get_events_page(
        self,
        *,
        changed_at: date,
        cursor_url: str | None = None,
    ) -> ProviderEventsPageData:
        "Получить одну страницу событий Provider API."


class EventsPaginator:
    """Асинхронно обойти все страницы событий Provider API."""

    def __init__(self, *, client: EventsPageClientProtocol, changed_at: date) -> None:
        self._client = client
        self._changed_at = changed_at

    async def __aiter__(self) -> AsyncIterator[ProviderEventData]:
        """Последовательно вернуть все события со всех страниц Provider API."""
        next_url: str | None = None

        while True:
            page = await self._client.get_events_page(
                changed_at=self._changed_at,
                cursor_url=next_url,
            )

            for event in page["results"]:
                yield event

            next_url = page["next"]

            if next_url is None:
                break

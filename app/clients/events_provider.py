from datetime import date
from typing import Any, NoReturn, cast
from urllib.parse import urlparse
from uuid import UUID

import httpx

from app.contracts.events_provider import ProviderEventData, ProviderEventsPageData


class EventsProviderError(Exception):
    """Базовая ошибка взаимодействия с Events Provider API."""


class EventsProviderAuthError(EventsProviderError):
    """Ошибка аутентификации в Events Provider API."""


class EventsProviderNotFoundError(EventsProviderError):
    """Запрошенный ресурс отсутствует в Events Provider API."""


class EventsProviderBadRequestError(EventsProviderError):
    """Events Provider API отклонил запрос как некорректный."""


class EventsProviderRateLimitError(EventsProviderError):
    """Events Provider API временно ограничил число запросов."""


class EventsProviderClient:
    """
    Асинхронный HTTP-клиент для Events Provider API.
    """

    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        if not base_url:
            raise ValueError("Базовый URL Events Provider API не должен быть пустым.")

        if not api_key:
            raise ValueError("API-ключ Events Provider API не должен быть пустым.")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key},
            timeout=timeout_seconds,
        )

    async def close(self) -> None:
        """Закрыть HTTP-соединения клиента."""
        await self._client.aclose()

    async def get_events_page(
        self,
        *,
        changed_at: date,
        cursor_url: str | None = None,
    ) -> ProviderEventsPageData:
        """Получить страницу событий, изменённых после указанной даты."""

        if cursor_url is None:
            response = await self._client.get(
                "/api/events/",
                params={"changed_at": changed_at.isoformat()},
            )
        else:
            response = await self._client.get(
                self._normalize_next_url(cursor_url),
            )

        data = self._get_json(response, expected_status_code=(200,))

        raw_results = data.get("results")
        raw_next = data.get("next")
        raw_previous = data.get("previous")

        if not isinstance(raw_results, list):
            raise EventsProviderError("Events Provider API вернул некорректное поле results.")

        if raw_next is not None and not isinstance(raw_next, str):
            raise EventsProviderError("Events Provider API вернул некорректное поле next.")

        if raw_previous is not None and not isinstance(raw_previous, str):
            raise EventsProviderError("Events Provider API вернул некорректное поле previous.")

        return {"next": raw_next, "previous": raw_previous, "results": cast(list[ProviderEventData], raw_results)}

    async def get_available_seats(self, event_id: UUID) -> list[str]:
        """Получить актуальный список свободных мест для события."""
        response = await self._client.get(
            f"/api/events/{event_id}/seats/",
        )
        data = self._get_json(response, expected_status_code=(200,))

        raw_seats = data.get("seats")

        if not isinstance(raw_seats, list) or not all(isinstance(seat, str) for seat in raw_seats):
            raise EventsProviderError("Events Provider API вернул некорректное поле seats.")

        return list(cast(list[str], raw_seats))

    async def register(self, *, event_id: UUID, first_name: str, last_name: str, email: str, seat: str) -> UUID:
        """Зарегистрировать пользователя на событие и вернуть UUID билета."""

        response = await self._client.post(
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )
        data = self._get_json(response, expected_status_code=(200, 201))

        raw_ticket_id = data.get("ticket_id")

        if not isinstance(raw_ticket_id, str):
            raise EventsProviderError("Events Provider API вернул некорректное ticket_id.")

        try:
            return UUID(raw_ticket_id)
        except ValueError as error:
            raise EventsProviderError("Events Provider API вернул ticket_id не в формате UUID.") from error

    async def unregister(self, *, event_id: UUID, ticket_id: UUID) -> None:
        """Отменить регистрацию пользователя на событие."""
        response = await self._client.request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": str(ticket_id)},
        )
        data = self._get_json(response, expected_status_code=(200,))

        if data.get("success") is not True:
            raise EventsProviderError("Events Provider API не подтвердил отмену регистрации.")

    def _get_json(self, response: httpx.Response, *, expected_status_code: tuple[int, ...]) -> dict[str, Any]:
        """Проверить HTTP-статус и вернуть JSON-объект ответа."""
        if response.status_code not in expected_status_code:
            self._raise_for_error(response)

        try:
            data = response.json()
        except ValueError as error:
            raise EventsProviderError("Events Provider API вернул ответ не в формате JSON.") from error

        if not isinstance(data, dict):
            raise EventsProviderError("Events Provider API вернул JSON, который не является объектом.")

        return data

    def _raise_for_error(self, response: httpx.Response) -> NoReturn:
        """Преобразовать HTTP-ошибку Provider API в доменное исключение."""
        message = response.text

        if response.status_code == 400:
            raise EventsProviderBadRequestError(message)

        if response.status_code == 401:
            raise EventsProviderAuthError(message)

        if response.status_code == 404:
            raise EventsProviderNotFoundError(message)

        if response.status_code == 429:
            raise EventsProviderRateLimitError(message)

        raise EventsProviderError(f"Events Provider API вернул HTTP {response.status_code}: {message}.")

    def _normalize_next_url(self, next_url: str) -> str:
        """Оставить из URL следующей страницы только путь и query-параметры."""
        parsed_url = urlparse(next_url)

        if not parsed_url.path:
            raise EventsProviderError("Events Provider API вернул некорректную ссылку next.")

        if parsed_url.query:
            return f"{parsed_url.path}?{parsed_url.query}"

        return parsed_url.path

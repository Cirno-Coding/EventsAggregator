from typing import NoReturn

import httpx


class CapashinoError(Exception):
    """Базовая ошибка взаимодействия с Capashino."""


class CapashinoValidationError(CapashinoError):
    """Capashino отклонил данные уведомления."""


class CapashinoAuthorizationError(CapashinoError):
    """Capashino отклонил API-ключ."""


class CapashinoConflictError(CapashinoError):
    """Capashino сообщил о конфликте ключа идемпотентности."""


class CapashinoUnavailableError(CapashinoError):
    """Capashino временно недоступен."""


class CapashinoClient:
    """Асинхронный HTTP-клиент Notification-сервиса Capashino."""

    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        if not base_url:
            raise ValueError("Базовый URL Capashino не должен быть пустым.")

        if not api_key:
            raise ValueError("API-ключ Capashino не должен быть пустым.")

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Content-Type": "application/json", "X-API-Key": api_key},
            timeout=timeout_seconds,
        )

    async def close(self) -> None:
        """Закрыть HTTP-соединение клиента."""
        await self._client.aclose()

    async def create_notification(self, *, message: str, reference_id: str, idempotency_key: str) -> None:
        """
        Создать уведомление Capashino.

        Успехом считается только HTTP 201. Повторная отправка с тем же
        idempotency_key также должна получить HTTP 201 от Capashino.
        """
        if not message.strip():
            raise ValueError("Текст уведомления не должен быть пустым.")

        if not reference_id:
            raise ValueError("reference_id не должен быть пустым.")

        if not idempotency_key:
            raise ValueError("Ключ идемпотентности уведомления не должен быть пустым.")

        try:
            response = await self._client.post(
                "/api/notifications", json={"message": message, "reference_id": reference_id, "idempotency_key": idempotency_key}
            )
        except httpx.HTTPError as error:
            raise CapashinoUnavailableError("Capashino временно недоступен.") from error

        if response.status_code == httpx.codes.CREATED:
            return

        self._raise_for_error(response)

    def _raise_for_error(self, response: httpx.Response) -> NoReturn:
        """Преобразовать HTTP-ошибку Capashino в доменное исключение."""
        message = response.text

        if response.status_code in (httpx.codes.BAD_REQUEST, httpx.codes.UNPROCESSABLE_ENTITY):
            raise CapashinoValidationError(message)

        if response.status_code == httpx.codes.UNAUTHORIZED:
            raise CapashinoAuthorizationError(message)

        if response.status_code == httpx.codes.CONFLICT:
            raise CapashinoConflictError(message)

        if response.status_code >= httpx.codes.INTERNAL_SERVER_ERROR:
            raise CapashinoUnavailableError(message)

        raise CapashinoError(f"Capashino вернул HTTP {response.status_code}: {message}")

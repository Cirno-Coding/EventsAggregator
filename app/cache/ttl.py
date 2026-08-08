import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Потокобезопасный в рамках одного процесса кэш с ограниченным временем жизни."""

    def __init__(self, *, ttl_seconds: int) -> None:
        """
        Создать кэш.

        Args:
            ttl_seconds: Время хранения значения в секундах.
        """
        if ttl_seconds < 1:
            raise ValueError("Время жизни кэша должно быть не менее одной секунды.")

        self._ttl_seconds = ttl_seconds
        self._storage: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        """
        Вернуть неистёкшее значение по ключу или None.

        Просроченное значение удаляется при чтении.
        """
        item = self._storage.get(key)

        if item is None:
            return None

        expires_at, value = item

        if expires_at <= time.monotonic():
            self._storage.pop(key, None)
            return None

        return value

    def set(self, key: str, value: T) -> None:
        """Сохранить значение по ключу на время жизни кэша."""
        expires_at = time.monotonic() + self._ttl_seconds
        self._storage[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        """Удалить значение по ключу, если оно существует."""
        self._storage.pop(key, None)

    def clear(self) -> None:
        """Полностью очистить кэш."""
        self._storage.clear()

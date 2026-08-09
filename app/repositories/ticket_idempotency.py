from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketIdempotencyKey


class TicketIdempotencyRepository:
    """Репозиторий результатов успешной регистрации по ключам идемпотентности."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def acquire_lock(self, idempotency_key: str) -> None:
        """
        Получить транзакционную блокировку для ключа идемпотентности.

        PostgreSQL автоматически освободит блокировку после commit или rollback.
        Это предотвращает одновременное создание двух билетов с одинаковым ключом.
        """
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:idempotency_key))"),
            {"idempotency_key": idempotency_key},
        )

    async def delete_expired(self) -> None:
        """Удалить записи, срок хранения которых закончился."""
        await self._session.execute(
            delete(TicketIdempotencyKey).where(
                TicketIdempotencyKey.expires_at <= datetime.now(timezone.utc),
            ),
        )

    async def get_by_key(
        self,
        idempotency_key: str,
    ) -> TicketIdempotencyKey | None:
        """Вернуть сохранённый результат по ключу либо None."""
        result = await self._session.execute(
            select(TicketIdempotencyKey).where(
                TicketIdempotencyKey.idempotency_key == idempotency_key,
            ),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        ticket_id: UUID,
        ttl_seconds: int,
    ) -> TicketIdempotencyKey:
        """
        Сохранить результат успешной регистрации.

        Commit не выполняется: запись фиксируется вместе с билетом и outbox-событием.
        """
        created_at = datetime.now(timezone.utc)
        record = TicketIdempotencyKey(
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            ticket_id=ticket_id,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=ttl_seconds),
        )
        self._session.add(record)

        return record

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket, TicketStatus


class TicketRepository:
    """
    Репозиторий локально сохранённых регистраций.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        ticket_id: UUID,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        """
        Создать локальную запись о билете и вернуть её.
        """
        ticket = Ticket(
            id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
            status=TicketStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(ticket)
        return ticket

    async def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        """
        Вернуть билет по UUID или None, если билет не найден.
        """
        result = await self._session.execute(select(Ticket).where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()

    async def mark_cancelled(self, ticket: Ticket) -> None:
        """
        Пометить билет отменённым без физического удаления из БД.

        Commit выполняется API-слоем после успешной отмены регистрации
        в Events Provider API.
        """
        ticket.status = TicketStatus.CANCELLED.value

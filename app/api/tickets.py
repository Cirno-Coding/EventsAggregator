from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.ttl import TTLCache
from app.clients.events_provider import (
    EventsProviderBadRequestError,
    EventsProviderClient,
    EventsProviderError,
    EventsProviderNotFoundError,
)
from app.dependencies import (
    get_db_session,
    get_event_repository,
    get_events_provider_client,
    get_outbox_repository,
    get_seats_cache,
    get_ticket_repository,
)
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.tickets import TicketRepository
from app.schemas.tickets import (
    CreateTicketRequest,
    CreateTicketResponse,
    DeleteTicketResponse,
)
from app.usecases.create_ticket import (
    CreateTicketUseCase,
    EventNotFoundError,
    EventNotPublishedError,
)
from app.usecases.delete_ticket import (
    DeleteTicketUseCase,
    TicketNotFoundError,
)

router = APIRouter(prefix="/api/tickets", tags=["Билеты"])


@router.post(
    "",
    response_model=CreateTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать посетителя на событие",
    description=(
        "Проверяет опубликованное событие, создаёт регистрацию в Events "
        "Provider API и в одной транзакции сохраняет локальный билет "
        "с outbox-событием для последующей отправки уведомления."
    ),
)
async def create_ticket(
    ticket_data: CreateTicketRequest,
    session: AsyncSession = Depends(get_db_session),
    events_repository: EventRepository = Depends(get_event_repository),
    tickets_repository: TicketRepository = Depends(get_ticket_repository),
    outbox_repository: OutboxRepository = Depends(get_outbox_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
    seats_cache: TTLCache[list[str]] = Depends(get_seats_cache),
) -> CreateTicketResponse:
    """Создать билет и вернуть его UUID."""
    use_case = CreateTicketUseCase(
        events_repository=events_repository,
        tickets_repository=tickets_repository,
        outbox_repository=outbox_repository,
        client=client,
        seats_cache=seats_cache,
    )

    try:
        ticket_id = await use_case.execute(
            event_id=ticket_data.event_id,
            first_name=ticket_data.first_name,
            last_name=ticket_data.last_name,
            email=str(ticket_data.email),
            seat=ticket_data.seat,
        )
        await session.commit()
    except EventNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from None
    except EventNotPublishedError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not published",
        ) from None
    except EventsProviderBadRequestError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from None
    except EventsProviderNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found in provider",
        ) from None
    except EventsProviderError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from None

    return CreateTicketResponse(ticket_id=ticket_id)


@router.delete(
    "/{ticket_id}",
    response_model=DeleteTicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Отменить регистрацию по билету",
    description=("Отменяет регистрацию в Events Provider API, удаляет локальную " "запись о билете и очищает кэш свободных мест."),
)
async def delete_ticket(
    ticket_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    tickets_repository: TicketRepository = Depends(get_ticket_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
    seats_cache: TTLCache[list[str]] = Depends(get_seats_cache),
) -> DeleteTicketResponse:
    """Отменить регистрацию и вернуть признак успеха."""
    use_case = DeleteTicketUseCase(
        tickets_repository=tickets_repository,
        client=client,
        seats_cache=seats_cache,
    )

    try:
        await use_case.execute(ticket_id)
        await session.commit()
    except TicketNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        ) from None
    except EventsProviderNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found in provider",
        ) from None
    except EventsProviderBadRequestError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from None
    except EventsProviderError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from None

    return DeleteTicketResponse(success=True)

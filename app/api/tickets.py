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
from app.core.config import Settings
from app.dependencies import (
    get_app_settings,
    get_db_session,
    get_event_repository,
    get_events_provider_client,
    get_outbox_repository,
    get_seats_cache,
    get_ticket_idempotency_repository,
    get_ticket_repository,
)
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.ticket_idempotency import TicketIdempotencyRepository
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
    IdempotencyConflictError,
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
        "с outbox-событием для последующей отправки уведомления. "
        "Необязательное поле idempotency_key передаётся в теле запроса: "
        "повтор идентичного запроса с тем же ключом вернёт исходный билет."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "description": ("Ключ идемпотентности уже использован с другими данными " "регистрации."),
        },
    },
)
async def create_ticket(
    ticket_data: CreateTicketRequest,
    session: AsyncSession = Depends(get_db_session),
    events_repository: EventRepository = Depends(get_event_repository),
    tickets_repository: TicketRepository = Depends(get_ticket_repository),
    outbox_repository: OutboxRepository = Depends(get_outbox_repository),
    idempotency_repository: TicketIdempotencyRepository = Depends(get_ticket_idempotency_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
    settings: Settings = Depends(get_app_settings),
    seats_cache: TTLCache[list[str]] = Depends(get_seats_cache),
) -> CreateTicketResponse:
    """Создать билет либо вернуть результат предыдущего идентичного запроса."""
    use_case = CreateTicketUseCase(
        events_repository=events_repository,
        tickets_repository=tickets_repository,
        outbox_repository=outbox_repository,
        idempotency_repository=idempotency_repository,
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
            idempotency_key=ticket_data.idempotency_key,
            idempotency_ttl_seconds=settings.idempotency_key_ttl_seconds,
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
    except IdempotencyConflictError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Ключ идемпотентности уже использован с другими данными " "регистрации."),
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
    description=("Отменяет регистрацию в Events Provider API, помечает локальный билет " "отменённым и очищает кэш свободных мест."),
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

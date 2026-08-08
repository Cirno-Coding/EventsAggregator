from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_event_repository
from app.repositories.events import EventRepository
from app.schemas.events import EventDetailResponse, EventListItemResponse, EventListResponse
from app.usecases.get_event import GetEventUseCase
from app.usecases.get_events import GetEventsUseCase

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get(
    "",
    response_model=EventListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_events(
    request: Request,
    date_from: date | None = None,
    page: int = 1,
    page_size: int = 20,
    repository: EventRepository = Depends(get_event_repository),
) -> EventListResponse:
    """Вернуть страницу событий из локальной БД."""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page must be greater than or equal to 1",
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_size must be between 1 and 100",
        )

    use_case = GetEventsUseCase(repository)
    count, events = await use_case.execute(date_from=date_from, page=page, page_size=page_size)

    next_url: str | None = None
    previous_url: str | None = None

    if page * page_size < count:
        next_url = str(request.url.include_query_params(page=page + 1))

    if page > 1:
        previous_url = str(request.url.include_query_params(page=page - 1))

    return EventListResponse(
        count=count, next=next_url, previous=previous_url, results=[EventListItemResponse.model_validate(event) for event in events]
    )


@router.get(
    "/{event_id}",
    response_model=EventDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_event(
    event_id: UUID,
    repository: EventRepository = Depends(get_event_repository),
) -> EventDetailResponse:
    """Вернуть подробную информацию о событии по его UUID."""
    use_case = GetEventUseCase(repository)
    event = await use_case.execute(event_id)

    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    return EventDetailResponse.model_validate(event)

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from app.dependencies import (
    get_event_repository,
    get_ticket_repository,
)
from app.metrics.prometheus import (
    EVENTS_TOTAL,
    TICKETS_CANCELLED_TOTAL,
    TICKETS_CREATED_TOTAL,
)
from app.repositories.events import EventRepository
from app.repositories.tickets import TicketRepository

router = APIRouter(tags=["Метрики"])


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Получить метрики Prometheus",
    description=("Возвращает все зарегистрированные метрики в стандартном формате " "Prometheus. Эндпоинт не требует авторизации."),
)
async def get_metrics(
    events_repository: EventRepository = Depends(get_event_repository), tickets_repository: TicketRepository = Depends(get_ticket_repository)
) -> Response:
    """
    Обновить бизнес-метрики точными значениями из БД и вернуть реестр Prometheus.

    Значения не инкрементируются в коде, поэтому остаются корректными
    после перезапуска приложения.
    """
    EVENTS_TOTAL.set(await events_repository.count())
    TICKETS_CREATED_TOTAL.set(await tickets_repository.count())
    TICKETS_CANCELLED_TOTAL.set(await tickets_repository.count_cancelled())

    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

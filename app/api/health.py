from fastapi import APIRouter, status

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Проверить доступность сервиса",
    description=("Возвращает HTTP 200, если Events Aggregator запущен. " "Не обращается к БД и внешнему Provider API."),
)
async def health_check() -> dict[str, str]:
    """
    Вернуть простой статус работоспособности приложения.
    """
    return {"status": "ok"}

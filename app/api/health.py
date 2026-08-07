from fastapi import APIRouter, status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """
    Роутер отвечает только за HTTP. Он не обращается ни к БД, ни к Provider, поэтому проверяет именно доступность нашего приложения.
    """
    return {"status": "ok"}

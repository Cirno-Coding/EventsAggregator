from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """
    Это точка сборки приложения: здесь подключаются роуты и задаются общие настройки FastAPI
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
    )
    application.include_router(health_router)

    return application


app = create_app()

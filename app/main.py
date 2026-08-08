import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.sync import router as sync_router
from app.core.config import get_settings
from app.sync.worker import start_background_sync, stop_background_sync


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Управлять фоновым worker на протяжении жизни приложения."""
    settings = get_settings()
    sync_task: asyncio.Task[None] | None = None

    if settings.enable_background_sync:
        sync_task = start_background_sync(settings)

    try:
        yield
    finally:
        if sync_task is not None:
            await stop_background_sync(sync_task)


def create_app() -> FastAPI:
    """Создать и настроить экземпляр FastAPI-приложения."""
    settings = get_settings()

    application = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug, lifespan=lifespan)
    application.include_router(health_router)
    application.include_router(sync_router)

    return application


app = create_app()

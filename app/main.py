import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.sync import router as sync_router
from app.api.tickets import router as ticket_router
from app.clients.capashino import CapashinoClient
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.outbox.handlers import CapashinoOutboxHandler
from app.outbox.worker import OutboxWorker, start_background_outbox, stop_background_outbox
from app.sync.worker import start_background_sync, stop_background_sync


def configure_glitchtip() -> None:
    """
    Подключить Sentry SDK к GlitchTip при наличии DSN.

    FastAPI-интеграция автоматически отправляет необработанные исключения.
    При пустом GLITCHTIP_DSN приложение продолжает работать без мониторинга.
    """
    settings = get_settings()

    if settings.glitchtip_dsn is None:
        return

    sentry_sdk.init(
        dsn=settings.glitchtip_dsn,
        environment=settings.app_env,
        send_default_pii=False,
        integrations=[FastApiIntegration()],
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Управлять фоновым worker на протяжении жизни приложения."""
    settings = get_settings()
    sync_task: asyncio.Task[None] | None = None
    outbox_task: asyncio.Task[None] | None = None
    capashino_client: CapashinoClient | None = None

    try:
        if settings.enable_background_sync:
            sync_task = start_background_sync(settings)

        if settings.enable_outbox_worker:
            if not settings.capashino_base_url:
                raise RuntimeError("Для outbox-worker не задана переменная CAPASHINO_BASE_URL.")

            if not settings.capashino_api_key:
                raise RuntimeError("Для outbox-worker не задана переменная CAPASHINO_API_KEY.")

            capashino_client = CapashinoClient(base_url=settings.capashino_base_url, api_key=settings.capashino_api_key)
            outbox_worker = OutboxWorker(
                session_factory=async_session_maker,
                handler=CapashinoOutboxHandler(capashino_client),
                batch_size=settings.outbox_batch_size,
                poll_interval_seconds=settings.outbox_poll_interval_seconds,
            )
            outbox_task = start_background_outbox(outbox_worker)
        yield
    finally:
        if outbox_task is not None:
            await stop_background_outbox(outbox_task)

        if capashino_client is not None:
            await capashino_client.close()

        if sync_task is not None:
            await stop_background_sync(sync_task)


def create_app() -> FastAPI:
    """Создать и настроить экземпляр FastAPI-приложения."""
    settings = get_settings()
    configure_glitchtip()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="REST API для синхронизации событий, просмотра доступных мест и регистрации посетителей.",
        debug=settings.debug,
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exception: RequestValidationError) -> JSONResponse:
        """Вернуть ошибку валидации клиентского запроса с кодом HTTP 400."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": jsonable_encoder(exception.errors())},
        )

    application.include_router(metrics_router)
    application.include_router(health_router)
    application.include_router(events_router)
    application.include_router(ticket_router)
    application.include_router(sync_router)

    return application


app = create_app()

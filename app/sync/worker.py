import asyncio
import logging
from contextlib import suppress

from app.clients.events_provider import EventsProviderClient
from app.core.config import Settings
from app.core.database import async_session_maker
from app.repositories.events import EventRepository
from app.repositories.sync_metadata import SyncMetadataRepository
from app.sync.paginator import EventsPaginator
from app.usecases.sync_events import SyncEventsUseCase

logger = logging.getLogger(__name__)

_sync_lock = asyncio.Lock()


async def run_sync_once(settings: Settings) -> None:
    """Выполнить один запуск синхронизации событий."""

    async with _sync_lock:
        async with async_session_maker() as session:
            events_repository = EventRepository(session)
            metadata_repository = SyncMetadataRepository(session)
            client: EventsProviderClient | None = None

            try:
                if settings.events_provider_base_url is None:
                    raise RuntimeError("Не задана переменная EVENTS_PROVIDER_BASE_URL.")

                if settings.events_provider_api_key is None:
                    raise RuntimeError("Не задана переменная EVENTS_PROVIDER_API_KEY.")

                client = EventsProviderClient(base_url=settings.events_provider_base_url, api_key=settings.events_provider_api_key)

                await metadata_repository.mark_running()
                await session.commit()

                use_case = SyncEventsUseCase(
                    events_repository=events_repository,
                    metadata_repository=metadata_repository,
                    paginator_factory=lambda changed_at: EventsPaginator(client=client, changed_at=changed_at),
                )

                last_changed_at = await use_case.execute()

                await metadata_repository.mark_success(last_changed_at=last_changed_at)

                await session.commit()

                logger.info("Синхронизация событий успешно завершена.")

            except Exception as error:
                logger.exception("Синхронизация событий завершилась ошибкой.")
                await session.rollback()

                try:
                    await metadata_repository.mark_failure(error_message=str(error))
                    await session.commit()
                except Exception:
                    await session.rollback()
                    logger.exception("Не удалось сохранить статус ошибки синхронизации.")
            finally:
                if client is not None:
                    await client.close()


async def sync_loop(settings: Settings) -> None:
    """Запускать синхронизацию с заданной переодичностью."""
    while True:
        await run_sync_once(settings)
        await asyncio.sleep(settings.sync_interval_seconds)


def start_background_sync(settings: Settings) -> asyncio.Task[None]:
    """Запустить фоновый цикл синхронизации."""
    return asyncio.create_task(
        sync_loop(settings),
        name="events-background-sync",
    )


async def stop_background_sync(task: asyncio.Task[None]) -> None:
    """Отменить фоновый цикл и дождаться его остановки."""
    task.cancel()

    with suppress(asyncio.CancelledError):
        await task

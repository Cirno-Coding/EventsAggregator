import asyncio

from fastapi import APIRouter, Depends, status

from app.core.config import Settings
from app.dependencies import get_app_settings
from app.schemas.sync import SyncTriggerResponse
from app.sync.worker import run_sync_once

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post(
    "/trigger",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_200_OK,
)
async def trigger_sync(settings: Settings = Depends(get_app_settings)) -> SyncTriggerResponse:
    """Запустить синхронизацию событий вручную."""
    asyncio.create_task(
        run_sync_once(settings),
        name="events-manual-sync",
    )

    return SyncTriggerResponse(status="started")

from datetime import datetime, timezone
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncMetadata, SyncStatus

SYNC_METADATA_ID: Final[int] = 1


class SyncMetadataRepository:
    """
    Репозиторий метаданных фоновой синхронизации
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> SyncMetadata:
        """
        Вернуть единственную запись синхронизации или создать её.
        """

        result = await self._session.execute(select(SyncMetadata).where(SyncMetadata.id == SYNC_METADATA_ID))
        metadata = result.scalar_one_or_none()

        if metadata is None:
            metadata = SyncMetadata(
                id=SYNC_METADATA_ID,
                last_sync_time=None,
                last_changed_at=None,
                sync_status=SyncStatus.SUCCESS.value,
                error_message=None,
            )
            self._session.add(metadata)
            await self._session.flush()
        return metadata

    async def mark_running(self) -> SyncMetadata:
        """
        Отметить начало новой синхронизации.
        """
        metadata = await self.get_or_create()
        metadata.sync_status = SyncStatus.RUNNING.value
        metadata.error_message = None
        return metadata

    async def mark_success(self, *, last_changed_at: datetime | None) -> SyncMetadata:
        """
        Сохранить успешный итог синхронизации.
        """
        metadata = await self.get_or_create()
        metadata.sync_status = SyncStatus.SUCCESS.value
        metadata.last_sync_time = datetime.now(timezone.utc)
        metadata.error_message = None

        if last_changed_at is not None:
            metadata.last_changed_at = last_changed_at

        return metadata

    async def mark_failure(self, *, error_message: str) -> SyncMetadata:
        """
        Сохранить ошибку синхронизации.
        """
        metadata = await self.get_or_create()
        metadata.sync_status = SyncStatus.FAILED.value
        metadata.last_sync_time = datetime.now(timezone.utc)
        metadata.error_message = error_message
        return metadata

from typing import Literal

from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    """Ответ на ручной запуск синхронизации."""

    status: Literal["started"]

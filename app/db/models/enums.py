import enum


class EventStatus(str, enum.Enum):
    """Допустимые статусы события."""

    NEW = "new"
    PUBLISHED = "published"


class SyncStatus(str, enum.Enum):
    """Допустимые статусы синхронизации событий."""

    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"

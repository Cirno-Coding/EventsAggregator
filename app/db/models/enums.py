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


class OutboxStatus(str, enum.Enum):
    """Статусы сообщения Transactional Outbox."""

    PENDING = "pending"
    SENT = "sent"


class OutboxEventType(str, enum.Enum):
    """Поддерживаемые типы событий в Transactional Outbox."""

    TICKET_PURCHASED = "ticket_purchased"

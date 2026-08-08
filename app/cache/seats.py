from app.cache.ttl import TTLCache
from app.core.config import get_settings

settings = get_settings()

seats_cache: TTLCache[list[str]] = TTLCache(
    ttl_seconds=settings.seats_cache_ttl_seconds,
)

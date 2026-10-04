"""Redis clients: cache + rate-limit/pubsub."""
from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.core.config import settings

_cache: Redis | None = None


def get_redis() -> Redis:
    global _cache
    if _cache is None:
        _cache = from_url(str(settings.redis_cache_url or settings.redis_url), decode_responses=True)
    return _cache


async def close_redis() -> None:
    global _cache
    if _cache is not None:
        await _cache.aclose()
        _cache = None

"""
Redis-based SHA256 result caching for the Transform Agent.
Cache key = SHA256(source_format + target_format + data).
TTL: 1 hour by default.
"""

import hashlib
import os
import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis | None:
    global _redis
    if _redis is None:
        url = os.environ.get("REDIS_URL")
        if not url:
            return None
        _redis = aioredis.from_url(url, decode_responses=True)
    return _redis


def make_cache_key(source_format: str, target_format: str, data: str) -> str:
    """Compute a deterministic SHA256 cache key."""
    payload = f"{source_format}:{target_format}:{data}"
    return "transform:" + hashlib.sha256(payload.encode()).hexdigest()


async def cache_get(key: str) -> str | None:
    """Return cached value or None."""
    client = _get_client()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """Store a value with TTL (seconds)."""
    client = _get_client()
    if client is None:
        return
    try:
        await client.setex(key, ttl, value)
    except Exception:
        pass

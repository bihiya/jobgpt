"""Redis client with pooling, namespacing, and resilience helpers."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_pool: ConnectionPool | None = None
_client: Redis | None = None

KEY_PREFIX = "jobpilot"


def ns(*parts: str) -> str:
    """Key namespacing: jobpilot:cache:jobs:user123"""
    return ":".join((KEY_PREFIX, *parts))


async def get_redis() -> Redis:
    global _pool, _client
    if _client is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
        _client = Redis(connection_pool=_pool)
        logger.info("redis_connected", url=settings.redis_url.split("@")[-1])
    return _client


async def close_redis() -> None:
    global _pool, _client
    if _client is not None:
        await _client.aclose()
        _client = None
    if _pool is not None:
        await _pool.aclose()
        _pool = None
    logger.info("redis_disconnected")


async def ping_redis() -> bool:
    try:
        client = await get_redis()
        return bool(await client.ping())
    except Exception:  # noqa: BLE001
        return False


async def cache_get_json(key: str) -> Any | None:
    client = await get_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_set_json(key: str, value: Any, ttl: int | None = None) -> None:
    client = await get_redis()
    payload = json.dumps(value, default=str)
    if ttl:
        await client.set(key, payload, ex=ttl)
    else:
        await client.set(key, payload)


async def cache_delete(*keys: str) -> None:
    if not keys:
        return
    client = await get_redis()
    await client.delete(*keys)


async def cache_delete_pattern(pattern: str) -> int:
    """Invalidate by pattern (use sparingly)."""
    client = await get_redis()
    deleted = 0
    async for key in client.scan_iter(match=pattern, count=200):
        deleted += await client.delete(key)
    return deleted


async def pipeline_set_many(items: dict[str, Any], ttl: int | None = None) -> None:
    client = await get_redis()
    pipe = client.pipeline()
    for key, value in items.items():
        payload = json.dumps(value, default=str)
        if ttl:
            pipe.set(key, payload, ex=ttl)
        else:
            pipe.set(key, payload)
    await pipe.execute()

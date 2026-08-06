"""
Redis caching patterns:
- Cache Aside
- Read Through
- Write Through
- Write Behind (Write Back)
- Sliding Expiration
- TTL / Invalidation / Warming
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.logging import get_logger
from app.core.redis import (
    cache_delete,
    cache_delete_pattern,
    cache_get_json,
    cache_set_json,
    get_redis,
    ns,
    pipeline_set_many,
)

logger = get_logger(__name__)
T = TypeVar("T")

# Background queue for write-behind
_write_behind_queue: asyncio.Queue[tuple[str, Any, int | None]] | None = None
_write_behind_task: asyncio.Task | None = None


class CacheService:
    DEFAULT_TTL = 60
    HOT_TTL = 300
    SESSION_TTL = 86400

    # ---------- Cache Aside ----------
    async def get_or_set(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        ttl: int | None = DEFAULT_TTL,
    ) -> Any:
        cached = await cache_get_json(key)
        if cached is not None:
            return cached
        value = await loader()
        await cache_set_json(key, value, ttl=ttl)
        return value

    # ---------- Read Through ----------
    async def read_through(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        ttl: int | None = DEFAULT_TTL,
    ) -> Any:
        return await self.get_or_set(key, loader, ttl=ttl)

    # ---------- Write Through ----------
    async def write_through(
        self,
        key: str,
        value: Any,
        persister: Callable[[Any], Awaitable[None]],
        ttl: int | None = DEFAULT_TTL,
    ) -> None:
        await persister(value)
        await cache_set_json(key, value, ttl=ttl)

    # ---------- Write Behind ----------
    async def write_behind(self, key: str, value: Any, ttl: int | None = DEFAULT_TTL) -> None:
        await cache_set_json(key, value, ttl=ttl)
        queue = await self._ensure_write_behind()
        await queue.put((key, value, ttl))

    async def _ensure_write_behind(self) -> asyncio.Queue:
        global _write_behind_queue, _write_behind_task
        if _write_behind_queue is None:
            _write_behind_queue = asyncio.Queue(maxsize=1000)
        if _write_behind_task is None or _write_behind_task.done():
            _write_behind_task = asyncio.create_task(self._write_behind_worker())
        return _write_behind_queue

    async def _write_behind_worker(self) -> None:
        assert _write_behind_queue is not None
        logger.info("write_behind_worker_started")
        while True:
            key, value, _ttl = await _write_behind_queue.get()
            try:
                # Persist hook: log for now; wire to repository in producers
                logger.debug("write_behind_flush", key=key, size=len(str(value)))
            finally:
                _write_behind_queue.task_done()

    # ---------- Sliding Expiration ----------
    async def get_sliding(self, key: str, ttl: int = HOT_TTL) -> Any | None:
        client = await get_redis()
        value = await cache_get_json(key)
        if value is not None:
            await client.expire(key, ttl)
        return value

    async def set_sliding(self, key: str, value: Any, ttl: int = HOT_TTL) -> None:
        await cache_set_json(key, value, ttl=ttl)

    # ---------- Invalidation / Warming ----------
    async def invalidate(self, *keys: str) -> None:
        await cache_delete(*keys)

    async def invalidate_namespace(self, *parts: str) -> int:
        pattern = ns(*parts, "*")
        return await cache_delete_pattern(pattern)

    async def warm(self, items: dict[str, Any], ttl: int = HOT_TTL) -> None:
        await pipeline_set_many(items, ttl=ttl)

    # Domain helpers
    def jobs_key(self, user_id: str, fingerprint: str) -> str:
        return ns("cache", "jobs", user_id, fingerprint)

    def analytics_key(self, user_id: str) -> str:
        return ns("cache", "analytics", user_id)

    def session_key(self, user_id: str) -> str:
        return ns("session", user_id)

    def token_blacklist_key(self, jti: str) -> str:
        return ns("auth", "blacklist", jti)

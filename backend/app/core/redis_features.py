"""
Redis feature helpers:
distributed locks, rate limiting, pub/sub, sorted sets (leaderboards),
counters, token blacklist, HyperLogLog, geospatial, streams, Bloom (set approx).
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from app.core.redis import get_redis, ns

# Lua script: release lock only if token matches (safe unlock)
RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
else
  return 0
end
"""

# Sliding window rate limit
RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
local count = redis.call("ZCARD", key)
if count >= limit then
  return 0
end
redis.call("ZADD", key, now, ARGV[4])
redis.call("EXPIRE", key, window)
return 1
"""


class DistributedLock:
    def __init__(self, name: str, ttl_seconds: int = 30) -> None:
        self.key = ns("lock", name)
        self.ttl = ttl_seconds
        self.token = str(uuid.uuid4())

    async def acquire(self) -> bool:
        client = await get_redis()
        return bool(await client.set(self.key, self.token, nx=True, ex=self.ttl))

    async def release(self) -> None:
        client = await get_redis()
        await client.eval(RELEASE_LOCK_LUA, 1, self.key, self.token)

    @asynccontextmanager
    async def hold(self) -> AsyncIterator[bool]:
        ok = await self.acquire()
        try:
            yield ok
        finally:
            if ok:
                await self.release()


async def rate_limit_allow(bucket: str, limit: int, window_seconds: int) -> bool:
    client = await get_redis()
    key = ns("ratelimit", bucket)
    now = time.time()
    member = f"{now}:{uuid.uuid4().hex}"
    allowed = await client.eval(RATE_LIMIT_LUA, 1, key, now, window_seconds, limit, member)
    return bool(allowed)


async def incr_counter(name: str, amount: int = 1, ttl: int | None = None) -> int:
    client = await get_redis()
    key = ns("counter", name)
    value = await client.incrby(key, amount)
    if ttl:
        await client.expire(key, ttl)
    return int(value)


async def leaderboard_add(board: str, member: str, score: float) -> None:
    client = await get_redis()
    await client.zadd(ns("leaderboard", board), {member: score})


async def leaderboard_top(board: str, n: int = 10) -> list[tuple[str, float]]:
    client = await get_redis()
    rows = await client.zrevrange(ns("leaderboard", board), 0, n - 1, withscores=True)
    return [(m, float(s)) for m, s in rows]


async def publish(channel: str, message: str) -> int:
    client = await get_redis()
    return int(await client.publish(ns("pubsub", channel), message))


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    client = await get_redis()
    await client.set(ns("auth", "blacklist", jti), "1", ex=max(ttl_seconds, 1))


async def is_token_blacklisted(jti: str) -> bool:
    client = await get_redis()
    return bool(await client.exists(ns("auth", "blacklist", jti)))


async def hll_add(name: str, *values: str) -> None:
    client = await get_redis()
    if values:
        await client.pfadd(ns("hll", name), *values)


async def hll_count(name: str) -> int:
    client = await get_redis()
    return int(await client.pfcount(ns("hll", name)))


async def geo_add(index: str, lon: float, lat: float, member: str) -> None:
    client = await get_redis()
    await client.geoadd(ns("geo", index), (lon, lat, member))


async def geo_radius_km(index: str, lon: float, lat: float, radius_km: float) -> list[str]:
    client = await get_redis()
    result = await client.geosearch(
        ns("geo", index),
        longitude=lon,
        latitude=lat,
        radius=radius_km,
        unit="km",
    )
    return list(result)


async def stream_add(stream: str, fields: dict[str, Any]) -> str:
    client = await get_redis()
    return str(await client.xadd(ns("stream", stream), fields))


async def bloom_add(name: str, value: str) -> None:
    """Approximate Bloom via Redis SET + membership (swap for RedisBloom module in prod)."""
    client = await get_redis()
    await client.sadd(ns("bloom", name), value)


async def bloom_might_contain(name: str, value: str) -> bool:
    client = await get_redis()
    return bool(await client.sismember(ns("bloom", name), value))


async def set_session(user_id: str, payload: dict[str, Any], ttl: int = 86400) -> None:
    client = await get_redis()
    import json

    await client.set(ns("session", user_id), json.dumps(payload), ex=ttl)


async def get_session(user_id: str) -> dict[str, Any] | None:
    client = await get_redis()
    import json

    raw = await client.get(ns("session", user_id))
    return json.loads(raw) if raw else None

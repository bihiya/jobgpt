"""
Realtime fan-out via WebSockets + Redis pub/sub.

Workers and API services call `emit_realtime(...)`. Messages are published to
Redis channel `jobpilot:pubsub:user:{user_id}`. The API process runs a
subscriber bridge that delivers to locally connected WebSocket clients.

If Redis is unavailable, events still fan out to in-process sockets.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import get_logger
from app.core.redis import get_redis, ns

logger = get_logger(__name__)


class ConnectionManager:
    """In-memory user → WebSocket registry (one API process)."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(user_id, set()).add(websocket)
        logger.info("ws_connected", user_id=user_id, sockets=len(self._rooms.get(user_id, ())))

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        async with self._lock:
            sockets = self._rooms.get(user_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._rooms.pop(user_id, None)
        logger.info("ws_disconnected", user_id=user_id)

    async def send_raw(self, user_id: str, payload: str) -> int:
        async with self._lock:
            sockets = list(self._rooms.get(user_id, ()))
        delivered = 0
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                    delivered += 1
                else:
                    dead.append(ws)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws, user_id)
        return delivered

    def connected_users(self) -> int:
        return len(self._rooms)


hub = ConnectionManager()

_bridge_task: asyncio.Task | None = None


def user_channel(user_id: str) -> str:
    return f"user:{user_id}"


def build_event(
    event: str,
    user_id: str,
    data: dict[str, Any] | None = None,
    *,
    title: str | None = None,
    body: str | None = None,
    severity: str = "info",
) -> dict[str, Any]:
    return {
        "event": event,
        "user_id": user_id,
        "ts": datetime.now(UTC).isoformat(),
        "title": title,
        "body": body,
        "severity": severity,
        "data": data or {},
    }


async def emit_realtime(
    user_id: str,
    event: str,
    data: dict[str, Any] | None = None,
    *,
    title: str | None = None,
    body: str | None = None,
    severity: str = "info",
) -> None:
    """Publish a realtime event for a user (Redis + local fallback)."""
    if not user_id:
        return
    message = build_event(event, user_id, data, title=title, body=body, severity=severity)
    raw = json.dumps(message, default=str)
    published = False
    try:
        from app.core.redis_features import publish

        await publish(user_channel(user_id), raw)
        published = True
    except Exception as exc:  # noqa: BLE001
        logger.debug("realtime_redis_publish_failed", error=str(exc))
    if not published:
        await hub.send_raw(user_id, raw)


async def _bridge_loop() -> None:
    """Subscribe to all user channels and fan out to local WebSockets."""
    pattern = ns("pubsub", "user", "*")
    while True:
        try:
            client = await get_redis()
            pubsub = client.pubsub()
            await pubsub.psubscribe(pattern)
            logger.info("realtime_bridge_subscribed", pattern=pattern)
            async for item in pubsub.listen():
                if item is None:
                    continue
                if item.get("type") not in {"pmessage", "message"}:
                    continue
                channel = str(item.get("channel") or "")
                # channel: jobpilot:pubsub:user:{user_id}
                parts = channel.split(":")
                if len(parts) < 4:
                    continue
                user_id = parts[-1]
                data = item.get("data")
                if not isinstance(data, str):
                    continue
                await hub.send_raw(user_id, data)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("realtime_bridge_error", error=str(exc))
            await asyncio.sleep(2)


async def start_realtime_bridge() -> None:
    global _bridge_task
    if _bridge_task and not _bridge_task.done():
        return
    _bridge_task = asyncio.create_task(_bridge_loop(), name="realtime-bridge")


async def stop_realtime_bridge() -> None:
    global _bridge_task
    if _bridge_task:
        _bridge_task.cancel()
        try:
            await _bridge_task
        except asyncio.CancelledError:
            pass
        _bridge_task = None

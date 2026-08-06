"""Authenticated WebSocket endpoint for realtime JobPilot events."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.security import decode_token
from app.events.realtime import hub
from app.repository.user_repository import UserRepository

logger = get_logger(__name__)
router = APIRouter(tags=["realtime"])


async def _authenticate(token: str) -> str | None:
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    jti = payload.get("jti")
    if jti:
        try:
            from app.core.redis_features import is_token_blacklisted

            if await is_token_blacklisted(jti):
                return None
        except Exception:  # noqa: BLE001
            pass
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await UserRepository().get_by_id(user_id)
    if not user or not user.is_active:
        return None
    return str(user.id)


@router.websocket("/ws")
async def realtime_socket(websocket: WebSocket, token: str = Query(...)) -> None:
    user_id = await _authenticate(token)
    if not user_id:
        await websocket.close(code=4401)
        return

    await hub.connect(websocket, user_id)
    await websocket.send_text(
        json.dumps(
            {
                "event": "connected",
                "user_id": user_id,
                "severity": "info",
                "title": "Live updates on",
                "body": "Realtime channel connected",
                "data": {},
            }
        )
    )
    try:
        while True:
            message = await websocket.receive_text()
            if message in {"ping", '{"type":"ping"}'}:
                await websocket.send_text(json.dumps({"event": "pong"}))
                continue
            try:
                parsed = json.loads(message)
            except json.JSONDecodeError:
                continue
            if parsed.get("type") == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        await hub.disconnect(websocket, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ws_error", user_id=user_id, error=str(exc))
        await hub.disconnect(websocket, user_id)

"""Idempotency-Key middleware for safe retries on mutating requests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.redis import cache_get_json, cache_set_json, ns


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)

        key = request.headers.get("Idempotency-Key")
        if not key:
            return await call_next(request)

        cache_key = ns("idempotency", hashlib.sha256(key.encode()).hexdigest())
        try:
            cached = await cache_get_json(cache_key)
            if cached is not None:
                return JSONResponse(
                    status_code=cached.get("status_code", 200),
                    content=cached.get("body"),
                    headers={"X-Idempotent-Replay": "true"},
                )
        except Exception:  # noqa: BLE001
            return await call_next(request)

        response = await call_next(request)
        if 200 <= response.status_code < 300:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk if isinstance(chunk, bytes) else chunk.encode()
            try:
                import json

                parsed = json.loads(body.decode() or "null")
                await cache_set_json(
                    cache_key,
                    {"status_code": response.status_code, "body": parsed},
                    ttl=86400,
                )
            except Exception:  # noqa: BLE001
                pass
            headers = dict(response.headers)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )
        return response

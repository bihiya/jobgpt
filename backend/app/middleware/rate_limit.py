"""Simple in-memory rate limiter middleware (Redis-ready interface)."""

import time
from collections import defaultdict
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/health") or request.url.path.startswith("/metrics"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = time.time()
        window = settings.rate_limit_window_seconds
        self._hits[key] = [t for t in self._hits[key] if now - t < window]
        if len(self._hits[key]) >= settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "code": "RATE_LIMIT",
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        self._hits[key].append(now)
        return await call_next(request)

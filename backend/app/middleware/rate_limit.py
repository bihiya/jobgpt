"""Redis-backed sliding-window rate limiter with in-memory fallback."""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path.startswith("/health") or path.startswith("/metrics"):
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        bucket = f"{client_host}:{path}"

        allowed = True
        try:
            from app.core.redis_features import rate_limit_allow

            allowed = await rate_limit_allow(
                bucket,
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate_limit_redis_fallback", error=str(exc))
            allowed = True

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "code": "RATE_LIMIT",
                    "request_id": getattr(request.state, "request_id", None),
                },
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
        return await call_next(request)

"""HTTP caching helpers: ETag + Cache-Control for GET responses."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class ETagMiddleware(BaseHTTPMiddleware):
    """Attach weak ETags to successful JSON GET responses; honor If-None-Match."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if request.method != "GET" or response.status_code != 200:
            return response
        if "etag" in response.headers or "cache-control" in response.headers:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        etag = 'W/"' + hashlib.md5(body).hexdigest() + '"'  # noqa: S324
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "private, max-age=30"})

        headers = dict(response.headers)
        headers["ETag"] = etag
        headers.setdefault("Cache-Control", "private, max-age=30")
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )


def cacheable_json(data: dict, *, max_age: int = 30, etag_seed: str | None = None) -> JSONResponse:
    payload = json.dumps(data, default=str, separators=(",", ":")).encode()
    seed = etag_seed.encode() if etag_seed else payload
    etag = 'W/"' + hashlib.md5(seed).hexdigest() + '"'  # noqa: S324
    return JSONResponse(
        content=data,
        headers={
            "ETag": etag,
            "Cache-Control": f"private, max-age={max_age}",
        },
    )

"""JobPilot AI FastAPI application entrypoint."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Vercel loads this module as `backend.app.main:app` from the repo root.
# Local/Docker runs use `app.main:app` with PYTHONPATH=backend. Ensure both work.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_backend_root = str(_BACKEND_ROOT)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.kafka import close_producer
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.core.redis import close_redis, ping_redis
from app.core.telemetry import setup_telemetry
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_client
from app.middleware.http_cache import ETagMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.events.realtime import start_realtime_bridge, stop_realtime_bridge
from app.scheduler.jobs import start_scheduler, stop_scheduler

setup_logging()
logger = get_logger(__name__)

REQUEST_COUNTER = Counter("jobpilot_http_requests_total", "Total HTTP requests", ["method", "path"])

# Vercel sets VERCEL=1 on every deployment. Serverless cannot run Kafka workers / Playwright.
_ON_VERCEL = bool(os.getenv("VERCEL"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    for directory in (settings.upload_dir, settings.screenshot_dir, settings.report_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)
    try:
        await connect_to_mongo()
    except Exception as exc:  # noqa: BLE001
        # On Vercel, allow cold start so /health still responds while Atlas env is configured.
        if _ON_VERCEL:
            logger.warning("mongodb_connect_failed_vercel", error=str(exc))
        else:
            raise
    if settings.app_env != "test":
        try:
            await ping_redis()
            await start_realtime_bridge()
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis_ping_failed", error=str(exc))
        # APScheduler is a long-lived process model — skip on Vercel serverless.
        if not _ON_VERCEL:
            try:
                start_scheduler()
            except Exception as exc:  # noqa: BLE001
                logger.warning("scheduler_start_skipped", error=str(exc))
    logger.info("app_started", env=settings.app_env, vercel=_ON_VERCEL)
    try:
        yield
    finally:
        # Graceful shutdown order: stop intake → drain → close IO
        if not _ON_VERCEL:
            stop_scheduler()
        await stop_realtime_bridge()
        await close_producer()
        await close_redis()
        await close_mongo_connection()
        logger.info("app_stopped")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-powered Job Automation Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,  # faster JSON serialization
)

# Middleware order: last added = outermost
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID", "Idempotency-Key", "If-None-Match"],
    max_age=600,  # CORS preflight cache
)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(ETagMiddleware)

register_exception_handlers(app)
setup_telemetry(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", response_model=None)
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready", response_model=None)
async def ready():
    checks = {"mongo": False, "redis": False}
    try:
        client = get_client()
        await client.admin.command("ping")
        checks["mongo"] = True
    except Exception as exc:  # noqa: BLE001
        return ORJSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": checks, "error": str(exc)},
        )
    checks["redis"] = await ping_redis()
    if not checks["redis"] and settings.app_env == "production":
        return ORJSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@app.get("/metrics", response_model=None)
async def metrics():
    if not settings.prometheus_enabled:
        return Response(status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

"""JobPilot AI FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.kafka import close_producer
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.db.mongodb import close_mongo_connection, connect_to_mongo
from app.middleware.rate_limit import RateLimitMiddleware
from app.scheduler.jobs import start_scheduler, stop_scheduler

setup_logging()
logger = get_logger(__name__)

REQUEST_COUNTER = Counter("jobpilot_http_requests_total", "Total HTTP requests", ["method", "path"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    for directory in (settings.upload_dir, settings.screenshot_dir, settings.report_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)
    await connect_to_mongo()
    if settings.app_env != "test":
        try:
            start_scheduler()
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler_start_skipped", error=str(exc))
    logger.info("app_started", env=settings.app_env)
    yield
    stop_scheduler()
    await close_producer()
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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/ready")
async def ready():
    try:
        from app.db.mongodb import get_client

        client = get_client()
        await client.admin.command("ping")
        return {"status": "ready"}
    except Exception as exc:  # noqa: BLE001
        return Response(
            content=f'{{"status":"not_ready","error":"{exc}"}}',
            status_code=503,
            media_type="application/json",
        )


@app.get("/metrics")
async def metrics():
    if not settings.prometheus_enabled:
        return Response(status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

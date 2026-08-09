"""Typed Kafka event producers with local/dev inline fallbacks."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.kafka import publish
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _inline_fetch(payload: dict[str, Any]) -> None:
    try:
        from app.workers.fetch_worker import FetchWorker

        await FetchWorker().handle("job.fetch", payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inline_fetch_failed", error=str(exc), user_id=payload.get("user_id"))
        user_id = payload.get("user_id")
        if user_id:
            try:
                from app.services.automation_log_service import write_automation_log

                await write_automation_log(
                    str(user_id),
                    action="fetch.failed",
                    level="error",
                    message=f"fetch worker failed: {exc}",
                    metadata={"error": str(exc), "source": payload.get("source", "inline")},
                )
            except Exception:  # noqa: BLE001
                pass


async def publish_job_fetch(user_id: str, **extra: Any) -> str:
    """Queue a fetch. Returns 'kafka' or 'inline' (dev fallback when Kafka is down)."""
    payload = {"user_id": user_id, **extra}
    try:
        await publish("job.fetch", payload, key=user_id)
        return "kafka"
    except ServiceUnavailableError as exc:
        can_fallback = settings.app_env in {"development", "test"} or not settings.kafka_enabled
        if not can_fallback:
            raise

        from app.services.azure_jobs import azure_jobs_configured, start_container_app_job

        if azure_jobs_configured():
            portal = payload.get("portal")
            await start_container_app_job(
                "fetch",
                user_id=user_id,
                portal=str(portal) if portal else None,
            )
            logger.info("job_fetch_azure_job", user_id=user_id, portal=portal)
            return "azure-job"

        from app.automation.playwright_runtime import (
            playwright_available,
            playwright_unavailable_message,
        )

        if not playwright_available():
            message = playwright_unavailable_message()
            logger.warning(
                "job_fetch_playwright_unavailable",
                error=message,
                user_id=user_id,
            )
            try:
                from app.services.automation_log_service import write_automation_log

                await write_automation_log(
                    user_id,
                    action="fetch.failed",
                    level="error",
                    message=message,
                    metadata={"error": "PLAYWRIGHT_UNAVAILABLE", "source": payload.get("source")},
                )
            except Exception:  # noqa: BLE001
                pass
            raise ServiceUnavailableError(message, code="PLAYWRIGHT_UNAVAILABLE") from exc

        logger.warning(
            "job_fetch_inline_fallback",
            error=str(exc.message),
            user_id=user_id,
        )
        asyncio.create_task(_inline_fetch(payload))
        return "inline"


async def publish_job_match(user_id: str, job_id: str, **extra: Any) -> None:
    await publish("job.match", {"user_id": user_id, "job_id": job_id, **extra}, key=user_id)


async def publish_job_apply(user_id: str, job_id: str, **extra: Any) -> None:
    await publish("job.apply", {"user_id": user_id, "job_id": job_id, **extra}, key=user_id)


async def publish_notification(user_id: str, title: str, body: str, type_: str = "info") -> None:
    await publish(
        "notifications",
        {"user_id": user_id, "title": title, "body": body, "type": type_},
        key=user_id,
    )

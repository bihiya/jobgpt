"""Typed Kafka event producers with Azure Job / inline fallbacks."""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.kafka import publish
from app.core.logging import get_logger

logger = get_logger(__name__)


def can_use_worker_fallback() -> bool:
    """Kafka-off (Azure/Vercel) and local/test can run workers without a broker."""
    return settings.app_env in {"development", "test"} or not settings.kafka_enabled


async def _inline_fetch(payload: dict[str, Any]) -> None:
    try:
        from app.workers.fetch_worker import FetchWorker

        await FetchWorker().handle("job.fetch", payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inline_fetch_failed", error=str(exc), user_id=payload.get("user_id"))
        user_id = payload.get("user_id")
        portal_id = payload.get("portal_id")
        portal_name = payload.get("portal")
        if user_id:
            try:
                from app.services.automation_log_service import write_automation_log

                await write_automation_log(
                    str(user_id),
                    action="fetch.failed",
                    level="error",
                    portal=str(portal_name) if portal_name else "",
                    message=f"fetch worker failed: {exc}",
                    metadata={"error": str(exc), "source": payload.get("source", "inline")},
                )
            except Exception:  # noqa: BLE001
                pass
        # Clear sync marker + record health failure for the targeted portal.
        try:
            from app.repository.portal_repository import PortalRepository
            from app.services.portal_health_service import PortalHealthService

            portals = PortalRepository()
            health = PortalHealthService()
            portal = None
            if portal_id:
                portal = await portals.get_by_id(str(portal_id))
            elif user_id and portal_name:
                for item in await portals.list_for_user(str(user_id)):
                    if item.name.value == portal_name:
                        portal = item
                        break
            if portal:
                if getattr(portal, "sync_started_at", None):
                    portal.sync_started_at = None
                await health.record_failure(portal, str(exc))
        except Exception as cleanup_exc:  # noqa: BLE001
            logger.warning("inline_fetch_cleanup_failed", error=str(cleanup_exc))


async def publish_job_fetch(user_id: str, **extra: Any) -> str:
    """Queue a fetch. Returns 'kafka' or 'inline' (dev fallback when Kafka is down)."""
    payload = {"user_id": user_id, **extra}
    try:
        await publish("job.fetch", payload, key=user_id)
        return "kafka"
    except ServiceUnavailableError as exc:
        if not can_use_worker_fallback():
            raise

        from app.services.azure_jobs import azure_job_available, start_container_app_job

        if azure_job_available("fetch"):
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


async def _inline_match(payload: dict[str, Any]) -> None:
    try:
        from app.workers.match_worker import MatchWorker

        await MatchWorker().handle("job.match", payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inline_match_failed", error=str(exc), user_id=payload.get("user_id"))


async def _inline_apply(payload: dict[str, Any]) -> None:
    try:
        from app.workers.apply_worker import ApplyWorker

        await ApplyWorker().handle("job.apply", payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inline_apply_failed", error=str(exc), user_id=payload.get("user_id"))
        user_id = payload.get("user_id")
        if not user_id:
            return
        try:
            from app.services.automation_log_service import write_automation_log

            await write_automation_log(
                str(user_id),
                action="apply.failed",
                level="error",
                message=f"apply worker failed: {exc}",
                metadata={"error": str(exc), "job_id": payload.get("job_id")},
            )
        except Exception:  # noqa: BLE001
            pass


async def publish_job_match(user_id: str, job_id: str, *, wait: bool = False, **extra: Any) -> str:
    """Queue a match. Falls back to an inline worker when Kafka is off."""
    payload = {"user_id": user_id, "job_id": job_id, **extra}
    try:
        await publish("job.match", payload, key=user_id)
        return "kafka"
    except ServiceUnavailableError:
        if not can_use_worker_fallback():
            raise
        logger.warning("job_match_inline_fallback", user_id=user_id, job_id=job_id)
        if wait:
            await _inline_match(payload)
        else:
            asyncio.create_task(_inline_match(payload))
        return "inline"


async def publish_job_apply(user_id: str, job_id: str, **extra: Any) -> str:
    """Queue an apply. Azure Jobs, then local Playwright, when Kafka is off."""
    payload = {"user_id": user_id, "job_id": job_id, **extra}
    try:
        await publish("job.apply", payload, key=user_id)
        return "kafka"
    except ServiceUnavailableError as exc:
        if not can_use_worker_fallback():
            raise

        from app.services.azure_jobs import azure_job_available, start_container_app_job

        application_id = payload.get("application_id")
        if azure_job_available("apply"):
            await start_container_app_job(
                "apply",
                user_id=user_id,
                job_id=job_id,
                application_id=str(application_id) if application_id else None,
            )
            logger.info("job_apply_azure_job", user_id=user_id, job_id=job_id)
            return "azure-job"

        from app.automation.playwright_runtime import (
            playwright_available,
            playwright_unavailable_message,
        )

        if not playwright_available():
            message = playwright_unavailable_message()
            logger.warning("job_apply_playwright_unavailable", user_id=user_id, job_id=job_id)
            raise ServiceUnavailableError(message, code="PLAYWRIGHT_UNAVAILABLE") from exc

        logger.warning(
            "job_apply_inline_fallback",
            error=str(exc.message),
            user_id=user_id,
            job_id=job_id,
        )
        asyncio.create_task(_inline_apply(payload))
        return "inline"


async def publish_notification(user_id: str, title: str, body: str, type_: str = "info") -> None:
    await publish(
        "notifications",
        {"user_id": user_id, "title": title, "body": body, "type": type_},
        key=user_id,
    )

"""APScheduler job definitions."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.kafka import publish
from app.core.logging import get_logger

logger = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def publish_fetch_tick() -> None:
    logger.info("scheduler_fetch_tick")
    await publish("job.fetch", {"source": "scheduler"}, key="system")


async def publish_report_tick() -> None:
    logger.info("scheduler_report_tick")
    await publish("reports", {"source": "scheduler", "type": "daily"}, key="system")


async def publish_email_sync_tick() -> None:
    """Poll all enabled IMAP accounts and classify recruiting mail."""
    logger.info("scheduler_email_sync_tick")
    try:
        from app.services.email_inbox_service import EmailInboxService

        result = await EmailInboxService().sync_all()
        logger.info("scheduler_email_sync_done", **result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("scheduler_email_sync_failed", error=str(exc))


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        publish_fetch_tick,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        id="job_fetch_tick",
        replace_existing=True,
    )
    scheduler.add_job(
        publish_report_tick,
        "interval",
        seconds=max(settings.scheduler_interval_seconds * 6, 21600),
        id="report_tick",
        replace_existing=True,
    )
    scheduler.add_job(
        publish_email_sync_tick,
        "interval",
        seconds=max(int(getattr(settings, "email_sync_interval_seconds", 300) or 300), 60),
        id="email_sync_tick",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

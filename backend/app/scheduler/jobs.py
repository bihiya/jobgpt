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
    scheduler.start()
    logger.info("scheduler_started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

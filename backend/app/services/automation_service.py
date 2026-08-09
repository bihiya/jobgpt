"""Automation status and manual trigger service."""

from __future__ import annotations

import asyncio
from math import ceil

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.kafka import publish
from app.core.logging import get_logger
from app.events.realtime import emit_realtime
from app.repository.report_repository import AutomationLogRepository
from app.schemas.common import PaginatedResponse

logger = get_logger(__name__)

_TOPIC_MAP = {
    "fetch": "job.fetch",
    "match": "job.match",
    "apply": "job.apply",
    "report": "reports",
}


async def _run_worker_inline(job_type: str, user_id: str, topic: str) -> None:
    """Dev fallback when Kafka is down — invoke the worker handler directly."""
    from app.services.automation_log_service import write_automation_log

    payload = {"user_id": user_id, "source": "manual-inline"}
    try:
        if job_type == "fetch":
            from app.workers.fetch_worker import FetchWorker

            await FetchWorker().handle(topic, payload)
        elif job_type == "match":
            from app.models.enums import JobStatus
            from app.models.job import Job
            from app.workers.match_worker import MatchWorker

            # Manual "Run match" without a job_id: score all NEW jobs for the user.
            jobs = await Job.find({"user_id": user_id, "status": JobStatus.NEW}).limit(50).to_list()
            if not jobs:
                await write_automation_log(
                    user_id,
                    action="match.skipped",
                    level="warning",
                    message="No new jobs to match. Run fetch first.",
                )
            else:
                await write_automation_log(
                    user_id,
                    action="match.start",
                    level="info",
                    message=f"Matching {len(jobs)} new job(s)…",
                )
                worker = MatchWorker()
                matched = 0
                for job in jobs:
                    await worker.handle(topic, {"user_id": user_id, "job_id": str(job.id)})
                    matched += 1
                await write_automation_log(
                    user_id,
                    action="match.done",
                    level="success",
                    message=f"Matched {matched} job(s)",
                    metadata={"count": matched},
                )
        elif job_type == "apply":
            from app.services.automation_log_service import write_automation_log as _log

            await _log(
                user_id,
                action="apply.skipped",
                level="warning",
                message="Apply needs a specific job. Approve a match from Approvals or Pipeline.",
            )
        elif job_type == "report":
            from app.models.enums import ReportFormat, ReportStatus
            from app.models.report import Report
            from app.services.report_service import ReportService

            report = Report(
                user_id=user_id,
                type="custom",
                format=ReportFormat.CSV,
                status=ReportStatus.PENDING,
            )
            await report.insert()
            await write_automation_log(
                user_id,
                action="report.start",
                level="info",
                message=f"Generating report {report.id}…",
            )
            await ReportService().generate_csv(user_id, report)
            await write_automation_log(
                user_id,
                action="report.done",
                level="success",
                message=f"Report {report.id} ready",
            )
        else:
            logger.warning("inline_worker_unknown_type", job_type=job_type)
            return
        logger.info("inline_worker_finished", job_type=job_type, user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        from app.services.automation_log_service import write_automation_log as _log

        await _log(
            user_id,
            action=f"{job_type}.failed",
            level="error",
            message=f"{job_type} worker failed: {exc}",
            metadata={"error": str(exc)},
        )
        logger.warning(
            "inline_worker_failed",
            job_type=job_type,
            user_id=user_id,
            error=str(exc),
        )


class AutomationService:
    def __init__(self, logs: AutomationLogRepository | None = None) -> None:
        self.logs = logs or AutomationLogRepository()

    async def status(self, user_id: str) -> dict:
        from app.automation.playwright_runtime import (
            playwright_available,
            playwright_unavailable_message,
        )

        total_logs = await self.logs.count({"user_id": user_id})
        recent, _ = await self.logs.list_for_user(user_id, page=1, page_size=5)
        browser_ok = playwright_available()
        return {
            "user_id": user_id,
            "workers": {
                "fetch": "idle",
                "match": "idle",
                "apply": "idle",
                "notification": "idle",
                "report": "idle",
            },
            "playwright_available": browser_ok,
            "playwright_message": None if browser_ok else playwright_unavailable_message(),
            "kafka_enabled": settings.kafka_enabled,
            "total_logs": total_logs,
            "recent": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "level": log.level,
                    "message": log.message,
                    "portal": log.portal,
                    "created_at": log.created_at.isoformat(),
                }
                for log in recent
            ],
        }

    async def list_logs(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[dict]:
        items, total = await self.logs.list_for_user(user_id, page, page_size)
        pages = ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[
                {
                    "id": str(log.id),
                    "action": log.action,
                    "level": log.level,
                    "message": log.message,
                    "portal": log.portal,
                    "job_id": log.job_id,
                    "correlation_id": log.correlation_id,
                    "created_at": log.created_at.isoformat(),
                }
                for log in items
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def run(self, user_id: str, job_type: str = "fetch") -> dict:
        from app.services.audit_service import audit_event
        from app.services.automation_log_service import write_automation_log

        topic = _TOPIC_MAP.get(job_type, "job.fetch")
        mode = "kafka"
        warning: str | None = None

        await write_automation_log(
            user_id,
            action="automation.trigger",
            level="info",
            message=f"Triggered {job_type} worker",
            metadata={"job_type": job_type, "topic": topic},
        )

        try:
            await publish(topic, {"user_id": user_id, "source": "manual"}, key=user_id)
        except ServiceUnavailableError as exc:
            # Prefer Azure Container Apps Jobs (pay-per-use), then local inline.
            can_fallback = settings.app_env in {"development", "test"} or not settings.kafka_enabled
            if not can_fallback:
                raise

            from app.services.azure_jobs import azure_jobs_configured, start_container_app_job

            if azure_jobs_configured() and job_type in {"fetch", "match", "apply"}:
                mode = "azure-job"
                warning = str(exc.message)
                try:
                    started = await start_container_app_job(job_type, user_id=user_id)
                except ServiceUnavailableError:
                    await write_automation_log(
                        user_id,
                        action=f"{job_type}.failed",
                        level="error",
                        message="Failed to start Azure Container Apps Job",
                        metadata={"job_type": job_type},
                    )
                    raise
                await write_automation_log(
                    user_id,
                    action="automation.azure_job",
                    level="info",
                    message=f"Kafka unavailable — started Azure job for {job_type}",
                    metadata={"job_type": job_type, **started},
                )
            else:
                from app.automation.playwright_runtime import (
                    job_requires_playwright,
                    playwright_available,
                    playwright_unavailable_message,
                )

                if job_requires_playwright(job_type) and not playwright_available():
                    message = playwright_unavailable_message()
                    await write_automation_log(
                        user_id,
                        action=f"{job_type}.failed",
                        level="error",
                        message=message,
                        metadata={"job_type": job_type, "error": "PLAYWRIGHT_UNAVAILABLE"},
                    )
                    raise ServiceUnavailableError(message, code="PLAYWRIGHT_UNAVAILABLE") from exc

                mode = "inline"
                warning = str(exc.message)
                logger.warning(
                    "automation_kafka_fallback_inline",
                    job_type=job_type,
                    error=exc.message,
                )
                await write_automation_log(
                    user_id,
                    action="automation.inline",
                    level="info",
                    message=f"Kafka unavailable — running {job_type} inline",
                    metadata={"job_type": job_type},
                )
                asyncio.create_task(_run_worker_inline(job_type, user_id, topic))

        await emit_realtime(
            user_id,
            "automation.triggered",
            {"job_type": job_type, "topic": topic, "mode": mode},
            title="Automation started",
            body=f"Triggered {job_type} worker",
            severity="info",
        )

        await audit_event(
            user_id,
            "automation.triggered",
            message=f"started the {job_type} worker ({mode})",
            resource_type="automation",
            source="user",
            severity="info",
            metadata={
                "job_type": job_type,
                "topic": topic,
                "mode": mode,
                "outcome": "In progress",
                "next_step": "Open Automation to see whether each step passed or failed.",
            },
        )
        result = {"detail": f"Triggered {job_type}", "topic": topic, "mode": mode}
        if warning:
            result["warning"] = warning
        return result

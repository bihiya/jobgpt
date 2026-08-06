"""Report generation worker."""

from typing import Any

from app.core.logging import get_logger
from app.models.enums import ReportStatus
from app.models.report import Report
from app.services.report_service import ReportService
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class ReportWorker(BaseWorker):
    topics = ["reports"]
    group_id = "jobpilot-reports"

    def __init__(self) -> None:
        super().__init__()
        self.reports = ReportService()

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        report_id = payload.get("report_id")
        if not user_id or not report_id:
            logger.info("report_tick_skipped", reason="missing ids")
            return

        report = await Report.get(report_id)
        if not report:
            return
        try:
            await self.reports.generate_csv(user_id, report)
            logger.info("report_ready", report_id=report_id)
        except Exception as exc:  # noqa: BLE001
            report.status = ReportStatus.FAILED
            await report.save()
            logger.exception("report_failed", report_id=report_id, error=str(exc))


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(ReportWorker().start)

"""Match jobs worker with LLM ranking + human-in-the-loop gate."""

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.events.realtime import emit_realtime
from app.models.enums import JobStatus
from app.producers.events import publish_job_apply
from app.repository.job_repository import JobRepository
from app.repository.settings_repository import SettingsRepository
from app.services.approval_service import ApprovalService
from app.services.job_service import JobService
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class MatchWorker(BaseWorker):
    topics = ["job.match"]
    group_id = "jobpilot-match"

    def __init__(self) -> None:
        super().__init__()
        self.jobs = JobRepository()
        self.job_service = JobService()
        self.settings_repo = SettingsRepository()
        self.approvals = ApprovalService()

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload["user_id"]
        job_id = payload["job_id"]
        job = await self.jobs.get_by_id(job_id)
        if not job or job.user_id != user_id:
            return

        job = await self.job_service.match_job(user_id, job)
        user_settings = await self.settings_repo.get_or_create(user_id)
        threshold = user_settings.match_threshold or settings.match_threshold

        logger.info(
            "job_matched",
            job_id=job_id,
            score=job.match_score,
            threshold=threshold,
            reasons=job.match_breakdown.reasons[:3] if job.match_breakdown else [],
        )
        await emit_realtime(
            user_id,
            "job.matched",
            {
                "job_id": job_id,
                "match_score": job.match_score,
                "title": job.title,
                "company": job.company,
            },
        )

        if job.match_score < threshold:
            return

        require_approval = getattr(user_settings, "require_approval", True)
        auto_apply = user_settings.auto_apply and not require_approval

        if require_approval or not user_settings.auto_apply:
            summary = "; ".join(job.match_breakdown.reasons[:3]) if job.match_breakdown else ""
            await self.approvals.enqueue(user_id, job, summary=summary)
            return

        if auto_apply:
            job.status = JobStatus.APPLYING
            await job.save()
            await publish_job_apply(user_id, job_id, auto=True)


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(MatchWorker().start)

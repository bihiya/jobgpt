"""Match jobs worker."""

from typing import Any

from app.core.config import settings
from app.core.kafka import publish
from app.core.logging import get_logger
from app.models.enums import JobStatus
from app.repository.job_repository import JobRepository
from app.repository.settings_repository import SettingsRepository
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

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload["user_id"]
        job_id = payload["job_id"]
        job = await self.jobs.get_by_id(job_id)
        if not job or job.user_id != user_id:
            return

        job = await self.job_service.match_job(user_id, job)
        user_settings = await self.settings_repo.get_or_create(user_id)
        threshold = user_settings.match_threshold or settings.match_threshold

        logger.info("job_matched", job_id=job_id, score=job.match_score, threshold=threshold)
        if user_settings.auto_apply and job.match_score >= threshold:
            job.status = JobStatus.APPLYING
            await job.save()
            await publish(
                "job.apply",
                {"user_id": user_id, "job_id": job_id, "auto": True},
                key=user_id,
            )


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(MatchWorker().start)

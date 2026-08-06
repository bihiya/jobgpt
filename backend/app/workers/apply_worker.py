"""Apply jobs worker using Playwright + question bank + S3 screenshots."""

from datetime import datetime, timedelta
from typing import Any

from app.automation.portals.registry import get_portal_adapter
from app.core.kafka import publish
from app.core.logging import get_logger
from app.events.realtime import emit_realtime
from app.models.application import Application
from app.models.automation_log import AutomationLog
from app.models.enums import ApplicationStatus, JobStatus
from app.repository.job_repository import JobRepository
from app.repository.portal_repository import PortalRepository
from app.repository.resume_repository import ResumeRepository
from app.repository.settings_repository import SettingsRepository
from app.repository.user_repository import UserRepository
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.portal_health_service import PortalHealthService
from app.services.question_bank_service import QuestionBankService
from app.services.reminder_service import ReminderService
from app.services.storage_service import StorageService
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class ApplyWorker(BaseWorker):
    topics = ["job.apply"]
    group_id = "jobpilot-apply"

    def __init__(self) -> None:
        super().__init__()
        self.jobs = JobRepository()
        self.portals = PortalRepository()
        self.resumes = ResumeRepository()
        self.users = UserRepository()
        self.settings = SettingsRepository()
        self.questions = QuestionBankService()
        self.storage = StorageService()
        self.health = PortalHealthService()
        self.reminders = ReminderService()
        self.notifier = NotificationDispatcher()

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload["user_id"]
        job_id = payload["job_id"]
        application_id = payload.get("application_id")

        job = await self.jobs.get_by_id(job_id)
        if not job:
            return

        app = None
        if application_id:
            app = await Application.get(application_id)
        if not app:
            app = Application(user_id=user_id, job_id=job_id, status=ApplicationStatus.IN_PROGRESS)
            await app.insert()

        app.status = ApplicationStatus.IN_PROGRESS
        app.attempts += 1
        await app.save()

        resume = None
        if app.resume_id:
            resume = await self.resumes.get_by_id(app.resume_id)
        if not resume:
            resume = await self.resumes.get_default(user_id)
        if not resume:
            await self._fail(app, job, "No resume available")
            return

        portal_doc = await self.portals.find_one({"user_id": user_id, "name": job.portal})
        if portal_doc and not self.health.is_usable(portal_doc):
            await self._fail(app, job, "Portal auto-paused due to health score")
            return

        credentials = portal_doc.credentials.model_dump() if portal_doc else {}
        proxy = portal_doc.proxy.model_dump() if portal_doc and portal_doc.proxy.server else None
        adapter = get_portal_adapter(job.portal, credentials=credentials, proxy=proxy)

        from app.automation.base.portal import ExtractedJob

        extracted = ExtractedJob(
            external_id=job.external_id,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            skills=job.skills,
            apply_url=job.apply_url,
        )

        user = await self.users.get_by_id(user_id)
        bank = await self.questions.resolve_answers(
            user_id,
            [
                "How many years of experience do you have?",
                "What is your notice period?",
                "What is your current location?",
                "Are you authorized to work?",
                "Do you require sponsorship?",
            ],
        )
        answers = {
            "years": bank.get(
                "How many years of experience do you have?",
                str(user.profile.experience_years) if user else "0",
            ),
            "notice": bank.get(
                "What is your notice period?",
                str(user.profile.notice_period_days) if user else "0",
            ),
            "location": bank.get(
                "What is your current location?",
                user.profile.location if user else "",
            ),
            **{k: v for k, v in bank.items()},
        }

        await AutomationLog(
            user_id=user_id,
            job_id=job_id,
            application_id=str(app.id),
            portal=job.portal,
            action="apply",
            level="info",
            message="Starting application",
        ).insert()
        await emit_realtime(
            user_id,
            "application.started",
            {
                "job_id": job_id,
                "application_id": str(app.id),
                "portal": job.portal,
                "title": job.title,
            },
            title="Applying…",
            body=f"Starting application for {job.title}",
            severity="info",
        )
        await emit_realtime(
            user_id,
            "automation.log",
            {
                "action": "apply",
                "level": "info",
                "message": "Starting application",
                "job_id": job_id,
                "portal": job.portal,
            },
        )

        result = await adapter.apply_with_retry(extracted, resume.file_path, answers)
        if result.success:
            screenshot_url = ""
            if result.screenshot_path:
                stored = await self.storage.save_file(
                    result.screenshot_path,
                    folder=f"screenshots/{user_id}",
                    content_type="image/png",
                )
                screenshot_url = stored["url"]
                app.screenshot_path = stored["path"]
                app.screenshot_url = screenshot_url

            app.status = ApplicationStatus.SUCCESS
            app.applied_at = datetime.utcnow()
            app.error_message = ""
            await app.save()
            job.status = JobStatus.APPLIED
            await job.save()
            if portal_doc:
                await self.health.record_success(portal_doc)

            user_settings = await self.settings.get_or_create(user_id)
            await self.reminders.schedule_follow_up(
                user_id, app, days=getattr(user_settings, "follow_up_days", 7)
            )

            await self.notifier.dispatch(
                user_id,
                event="job.success",
                title="Application submitted",
                body=f"Applied to {job.title} at {job.company}",
                type_="success",
                metadata={"job_id": job_id, "application_id": str(app.id)},
            )
            await publish(
                "job.success",
                {"user_id": user_id, "job_id": job_id, "application_id": str(app.id)},
                key=user_id,
            )
            logger.info("apply_success", job_id=job_id)
        else:
            if portal_doc:
                await self.health.record_failure(portal_doc, result.message)
            await self._fail(app, job, result.message, screenshot=result.screenshot_path)

    async def _fail(self, app: Application, job, message: str, screenshot: str = "") -> None:
        app.status = ApplicationStatus.FAILED
        app.error_message = message
        app.screenshot_path = screenshot
        delay = min(2 ** app.attempts * 60, 3600)
        app.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        await app.save()
        job.status = JobStatus.FAILED
        await job.save()
        await self.notifier.dispatch(
            app.user_id,
            event="job.failed",
            title="Application failed",
            body=message,
            type_="error",
            metadata={"job_id": app.job_id, "application_id": str(app.id)},
        )
        await publish(
            "job.failed",
            {
                "user_id": app.user_id,
                "job_id": app.job_id,
                "application_id": str(app.id),
                "error": message,
            },
            key=app.user_id,
        )
        logger.warning("apply_failed", job_id=app.job_id, error=message)


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(ApplyWorker().start)

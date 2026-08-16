"""Apply jobs worker using Playwright + question bank + session vault."""

from datetime import datetime, timedelta
from typing import Any

from app.automation.portals.registry import get_portal_adapter
from app.automation.session_identity import apply_identity_to_portal
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
from app.services.apply_rate_limit import ApplyRateLimiter
from app.services.audit_service import audit_event
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.portal_health_service import PortalHealthService
from app.services.question_bank_service import QuestionBankService
from app.services.reminder_service import ReminderService
from app.services.session_vault import SessionVault
from app.services.storage_service import StorageService
from app.workers.base import BaseWorker

logger = get_logger(__name__)


def _otp_code_from_payload(payload: dict[str, Any], app: Application) -> str:
    """Read a one-shot OTP from the event payload or a prior session step."""
    code = str(payload.get("otp_code") or "")
    if code:
        return code
    for step in reversed(app.session_steps or []):
        if step.get("key") != "otp_provided":
            continue
        meta = step.get("metadata") or {}
        code = str(meta.get("otp_code") or "")
        if code:
            meta.pop("otp_code", None)
            step["metadata"] = meta
        return code
    return ""


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
        self.vault = SessionVault()
        self.rate_limiter = ApplyRateLimiter()

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
            from app.repository.application_repository import ApplicationRepository

            app = await ApplicationRepository().find_active_for_job(user_id, job_id)
        if not app:
            app = Application(user_id=user_id, job_id=job_id, status=ApplicationStatus.IN_PROGRESS)
            await app.insert()

        user_settings = await self.settings.get_or_create(user_id)
        limit = await self.rate_limiter.check(user_id, user_settings, portal=job.portal)
        if not limit.allowed:
            app.status = ApplicationStatus.PENDING
            app.error_message = limit.reason
            app.next_retry_at = datetime.utcnow() + timedelta(seconds=max(limit.retry_after_seconds, 60))
            app.updated_at = datetime.utcnow()
            await app.save()
            await emit_realtime(
                user_id,
                "application.rate_limited",
                {
                    "job_id": job_id,
                    "application_id": str(app.id),
                    "reason": limit.reason,
                    "applied_today": limit.applied_today,
                    "max_per_day": limit.max_per_day,
                },
                title="Apply delayed",
                body=limit.reason,
                severity="warning",
            )
            logger.info("apply_rate_limited", job_id=job_id, reason=limit.reason)
            return

        app.status = ApplicationStatus.IN_PROGRESS
        app.attempts += 1
        app.blocker_type = ""
        app.unknown_questions = []
        app.updated_at = datetime.utcnow()
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
        cookies = self.vault.load_cookies(portal_doc) if portal_doc else []
        totp_secret = self.vault.load_totp_secret(portal_doc) if portal_doc else ""
        selector_version = getattr(portal_doc, "selector_version", 1) if portal_doc else 1
        headless = bool(getattr(user_settings, "headless", True))

        adapter = get_portal_adapter(
            job.portal,
            credentials=credentials,
            cookies=cookies,
            proxy=proxy,
            headless=headless,
            totp_secret=totp_secret,
            otp_code=_otp_code_from_payload(payload, app),
            selector_version=selector_version,
        )

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
        question_prompts = [
            "How many years of experience do you have?",
            "What is your notice period?",
            "What is your current location?",
            "Are you authorized to work?",
            "Do you require sponsorship?",
            "Expected salary",
        ]
        bank = await self.questions.resolve_answers(user_id, question_prompts)
        # Also load full bank for form label matching
        for item in await self.questions.list(user_id):
            bank.setdefault(item["question"], item["answer"])

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
            correlation_id=adapter.recorder.correlation_id,
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

        result = None
        resume_local = None
        crash = ""
        try:
            resume_local = await self.storage.as_local_file(resume.file_path)
            result = await adapter.apply_with_retry(extracted, resume_local, answers)
        except Exception as exc:  # noqa: BLE001
            crash = str(exc) or exc.__class__.__name__
            logger.exception("apply_worker_crashed", job_id=job_id, error=crash)
        finally:
            await self.storage.cleanup_temp(resume_local, original=resume.file_path)

        if crash or result is None:
            await self._fail(app, job, crash or "Apply worker returned no result")
            return

        # Persist refreshed session cookies + who this session belongs to
        if portal_doc:
            apply_identity_to_portal(portal_doc, getattr(adapter, "session_identity", None))
            if result.cookies:
                self.vault.save_cookies(portal_doc, result.cookies)
            portal_doc.updated_at = datetime.utcnow()
            await portal_doc.save()

        app.session_steps = result.steps or []
        app.correlation_id = result.correlation_id or ""
        app.updated_at = datetime.utcnow()

        # Persist step logs
        for step in app.session_steps:
            await AutomationLog(
                user_id=user_id,
                job_id=job_id,
                application_id=str(app.id),
                portal=job.portal,
                action=str(step.get("key") or "step"),
                level="error" if step.get("status") == "error" else "info",
                message=str(step.get("label") or ""),
                metadata=step,
                correlation_id=app.correlation_id,
            ).insert()

        if result.needs_input:
            await self._pause_for_input(app, job, result)
            return
        if result.needs_otp:
            await self._pause_for_otp(app, job, result)
            return

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
            app.blocker_type = ""
            await app.save()
            job.status = JobStatus.APPLIED
            await job.save()
            if portal_doc:
                await self.health.record_success(portal_doc)

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
            await emit_realtime(
                user_id,
                "application.session",
                {"application_id": str(app.id), "job_id": job_id, "steps": app.session_steps},
                title="Apply session complete",
                body=job.title,
                severity="success",
            )
            await audit_event(
                user_id,
                "application.succeeded",
                message=f"Applied to {job.title} at {job.company}",
                job_id=job_id,
                application_id=str(app.id),
                resource_type="application",
                resource_id=str(app.id),
                source="worker",
                severity="success",
                metadata={"steps": len(app.session_steps)},
            )
            logger.info("apply_success", job_id=job_id)
        else:
            if portal_doc:
                await self.health.record_failure(portal_doc, result.message)
            app.fail_proof_html = (result.fail_proof_html or "")[:120_000]
            app.fail_proof_path = result.fail_proof_path or ""
            await self._fail(app, job, result.message, screenshot=result.screenshot_path)

    async def _pause_for_input(self, app: Application, job, result) -> None:
        app.status = ApplicationStatus.NEEDS_INPUT
        app.blocker_type = "unknown_question"
        app.unknown_questions = list(result.unknown_questions or [])
        app.error_message = result.message or "Answer unknown questions to resume"
        if result.screenshot_path:
            stored = await self._store_screenshot(app.user_id, result.screenshot_path)
            app.screenshot_path = stored["path"]
            app.screenshot_url = stored["url"]
        await app.save()
        job.status = JobStatus.APPLYING
        await job.save()
        await self.notifier.dispatch(
            app.user_id,
            event="application.needs_input",
            title="Answer needed to continue apply",
            body=f"{len(app.unknown_questions)} question(s) for {job.title}",
            type_="warning",
            metadata={
                "job_id": app.job_id,
                "application_id": str(app.id),
                "questions": app.unknown_questions,
            },
        )
        await emit_realtime(
            app.user_id,
            "application.needs_input",
            {
                "job_id": app.job_id,
                "application_id": str(app.id),
                "questions": app.unknown_questions,
                "steps": app.session_steps,
            },
            title="Question bank needed",
            body=job.title,
            severity="warning",
        )
        await audit_event(
            app.user_id,
            "application.needs_input",
            message="Paused apply for unknown questions",
            job_id=app.job_id,
            application_id=str(app.id),
            resource_type="application",
            resource_id=str(app.id),
            source="worker",
            severity="warning",
            metadata={"questions": app.unknown_questions},
        )

    async def _pause_for_otp(self, app: Application, job, result) -> None:
        app.status = ApplicationStatus.NEEDS_OTP
        app.blocker_type = "otp"
        app.error_message = result.message or "Enter portal OTP to continue"
        if result.screenshot_path:
            stored = await self._store_screenshot(app.user_id, result.screenshot_path)
            app.screenshot_path = stored["path"]
            app.screenshot_url = stored["url"]
        await app.save()
        job.status = JobStatus.APPLYING
        await job.save()
        await self.notifier.dispatch(
            app.user_id,
            event="application.needs_otp",
            title="OTP needed",
            body=f"{job.portal} requires your 2FA code for {job.title}",
            type_="warning",
            metadata={"job_id": app.job_id, "application_id": str(app.id), "portal": job.portal},
        )
        await emit_realtime(
            app.user_id,
            "application.needs_otp",
            {
                "job_id": app.job_id,
                "application_id": str(app.id),
                "portal": job.portal,
                "steps": app.session_steps,
            },
            title="OTP required",
            body=job.title,
            severity="warning",
        )
        await audit_event(
            app.user_id,
            "application.needs_otp",
            message="Paused apply — portal OTP required",
            job_id=app.job_id,
            application_id=str(app.id),
            resource_type="application",
            resource_id=str(app.id),
            source="worker",
            severity="warning",
        )

    async def _store_screenshot(self, user_id: str, local_path: str) -> dict[str, str]:
        if not local_path:
            return {"path": "", "url": ""}
        try:
            return await self.storage.save_file(
                local_path,
                folder=f"screenshots/{user_id}",
                content_type="image/png",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("screenshot_store_failed", error=str(exc), path=local_path)
            return {"path": local_path, "url": ""}

    async def _fail(self, app: Application, job, message: str, screenshot: str = "") -> None:
        app.status = ApplicationStatus.FAILED
        app.error_message = message
        if screenshot:
            stored = await self._store_screenshot(app.user_id, screenshot)
            app.screenshot_path = stored["path"]
            app.screenshot_url = stored.get("url") or ""
        delay = min(2 ** app.attempts * 60, 3600)
        app.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        app.updated_at = datetime.utcnow()
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
        await audit_event(
            app.user_id,
            "application.failed",
            message=message or "Application failed",
            job_id=app.job_id,
            application_id=str(app.id),
            resource_type="application",
            resource_id=str(app.id),
            source="worker",
            severity="error",
            metadata={"steps": app.session_steps},
        )
        logger.warning("apply_failed", job_id=app.job_id, error=message)


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(ApplyWorker().start)

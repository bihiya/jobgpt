"""Application orchestration service."""

from __future__ import annotations

from datetime import datetime
from math import ceil

from app.core.exceptions import NotFoundError
from app.events.realtime import emit_realtime
from app.models.application import Application
from app.models.enums import ApplicationStatus, JobStatus
from app.producers.events import publish_job_apply
from app.repository.application_repository import ApplicationRepository
from app.repository.job_repository import JobRepository
from app.schemas.application import ApplicationCreate, ApplicationResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import audit_event


class ApplicationService:
    def __init__(
        self,
        applications: ApplicationRepository | None = None,
        jobs: JobRepository | None = None,
    ) -> None:
        self.applications = applications or ApplicationRepository()
        self.jobs = jobs or JobRepository()

    def _to_response(self, app: Application) -> ApplicationResponse:
        return ApplicationResponse(
            id=str(app.id),
            job_id=app.job_id,
            resume_id=app.resume_id,
            status=app.status,
            attempts=app.attempts,
            screenshot_path=app.screenshot_path,
            screenshot_url=getattr(app, "screenshot_url", "") or "",
            error_message=app.error_message,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            created_at=app.created_at.isoformat(),
            session_steps=list(getattr(app, "session_steps", None) or []),
            unknown_questions=list(getattr(app, "unknown_questions", None) or []),
            blocker_type=getattr(app, "blocker_type", "") or "",
            correlation_id=getattr(app, "correlation_id", "") or "",
        )

    async def list(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: ApplicationStatus | None = None,
    ) -> PaginatedResponse[ApplicationResponse]:
        items, total = await self.applications.list_for_user(user_id, status, page, page_size)
        pages = ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[self._to_response(a) for a in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get(self, user_id: str, application_id: str) -> ApplicationResponse:
        app = await self._owned(user_id, application_id)
        return self._to_response(app)

    async def queue(self, user_id: str, payload: ApplicationCreate) -> ApplicationResponse:
        job = await self.jobs.get_by_id(payload.job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Job not found")

        existing = await self.applications.find_active_for_job(user_id, str(job.id))
        if existing:
            if payload.resume_id and existing.resume_id != payload.resume_id:
                existing.resume_id = payload.resume_id
            if job.status != JobStatus.APPLYING:
                job.status = JobStatus.APPLYING
                job.updated_at = datetime.utcnow()
                await job.save()
            if existing.status == ApplicationStatus.PENDING:
                await existing.save()
                await publish_job_apply(
                    user_id,
                    str(job.id),
                    application_id=str(existing.id),
                    resume_id=existing.resume_id,
                )
            else:
                await existing.save()
            return self._to_response(existing)

        app = await self.applications.create(
            {
                "user_id": user_id,
                "job_id": str(job.id),
                "resume_id": payload.resume_id,
                "status": ApplicationStatus.PENDING,
            }
        )
        job.status = JobStatus.APPLYING
        job.updated_at = datetime.utcnow()
        await job.save()

        await publish_job_apply(
            user_id,
            str(job.id),
            application_id=str(app.id),
            resume_id=payload.resume_id,
        )
        await emit_realtime(
            user_id,
            "application.queued",
            {"job_id": str(job.id), "application_id": str(app.id)},
            title="Application queued",
            body=f"Queued apply for {job.title}",
            severity="info",
        )
        await audit_event(
            user_id,
            "application.queued",
            message=f"Queued application for {job.title}",
            job_id=str(job.id),
            application_id=str(app.id),
            resource_type="application",
            resource_id=str(app.id),
            severity="info",
        )
        return self._to_response(app)

    async def retry(self, user_id: str, application_id: str) -> ApplicationResponse:
        app = await self._owned(user_id, application_id)
        app.status = ApplicationStatus.RETRYING
        app.attempts += 1
        app.updated_at = datetime.utcnow()
        await app.save()
        await publish_job_apply(
            user_id,
            app.job_id,
            application_id=str(app.id),
            resume_id=app.resume_id,
            attempt=app.attempts,
        )
        await emit_realtime(
            user_id,
            "application.queued",
            {"job_id": app.job_id, "application_id": str(app.id), "attempt": app.attempts},
            title="Retry queued",
            body="Application retry scheduled",
            severity="info",
        )
        await audit_event(
            user_id,
            "application.retry",
            message="Application retry queued",
            job_id=app.job_id,
            application_id=str(app.id),
            resource_type="application",
            resource_id=str(app.id),
            metadata={"attempt": app.attempts},
        )
        return self._to_response(app)

    async def cancel_active_for_job(self, user_id: str, job_id: str) -> ApplicationResponse | None:
        active = await self.applications.find_active_for_job(user_id, job_id)
        if not active:
            return None
        return await self.cancel(user_id, str(active.id))

    async def cancel(self, user_id: str, application_id: str) -> ApplicationResponse:
        """Cancel a queued / in-progress / paused apply (best-effort)."""
        app = await self._owned(user_id, application_id)
        cancellable = {
            ApplicationStatus.PENDING,
            ApplicationStatus.IN_PROGRESS,
            ApplicationStatus.RETRYING,
            ApplicationStatus.NEEDS_INPUT,
            ApplicationStatus.NEEDS_OTP,
        }
        if app.status not in cancellable:
            raise NotFoundError("Application cannot be cancelled in its current state")
        app.status = ApplicationStatus.CANCELLED
        app.blocker_type = ""
        app.error_message = "Cancelled by user"
        app.session_steps = list(app.session_steps or []) + [
            {
                "key": "cancelled",
                "label": "Cancelled by user",
                "status": "warn",
                "detail": "",
            }
        ]
        app.updated_at = datetime.utcnow()
        await app.save()
        job = await self.jobs.get_by_id(app.job_id)
        if job and job.status == JobStatus.APPLYING:
            job.status = JobStatus.APPROVED
            job.updated_at = datetime.utcnow()
            await job.save()
        await emit_realtime(
            user_id,
            "application.cancelled",
            {"job_id": app.job_id, "application_id": str(app.id)},
            title="Apply cancelled",
            body="Application cancelled",
            severity="info",
        )
        await audit_event(
            user_id,
            "application.cancelled",
            message="Application cancelled",
            job_id=app.job_id,
            application_id=str(app.id),
            resource_type="application",
            resource_id=str(app.id),
            severity="warning",
        )
        return self._to_response(app)

    async def _owned(self, user_id: str, application_id: str) -> Application:
        app = await self.applications.get_by_id(application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        return app

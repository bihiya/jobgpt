"""Application orchestration service."""

from __future__ import annotations

from datetime import datetime
from math import ceil

from app.core.exceptions import NotFoundError
from app.core.kafka import publish
from app.events.realtime import emit_realtime
from app.services.audit_service import audit_event
from app.models.application import Application
from app.models.enums import ApplicationStatus, JobStatus
from app.repository.application_repository import ApplicationRepository
from app.repository.job_repository import JobRepository
from app.schemas.application import ApplicationCreate, ApplicationResponse
from app.schemas.common import PaginatedResponse


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
            error_message=app.error_message,
            applied_at=app.applied_at.isoformat() if app.applied_at else None,
            created_at=app.created_at.isoformat(),
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

        await publish(
            "job.apply",
            {
                "user_id": user_id,
                "job_id": str(job.id),
                "application_id": str(app.id),
                "resume_id": payload.resume_id,
            },
            key=user_id,
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
        await publish(
            "job.apply",
            {
                "user_id": user_id,
                "job_id": app.job_id,
                "application_id": str(app.id),
                "resume_id": app.resume_id,
                "attempt": app.attempts,
            },
            key=user_id,
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

    async def _owned(self, user_id: str, application_id: str) -> Application:
        app = await self.applications.get_by_id(application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError("Application not found")
        return app

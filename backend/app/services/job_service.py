"""Job tracking service."""

from datetime import datetime
from math import ceil

from app.core.exceptions import NotFoundError
from app.core.kafka import publish
from app.models.enums import JobStatus
from app.models.job import Job
from app.repository.job_repository import JobRepository
from app.schemas.common import PaginatedResponse
from app.schemas.job import JobFilterParams, JobResponse, JobUpdateRequest
from app.services.match_service import MatchService
from app.services.user_service import UserService


class JobService:
    def __init__(
        self,
        jobs: JobRepository | None = None,
        users: UserService | None = None,
        matcher: MatchService | None = None,
    ) -> None:
        self.jobs = jobs or JobRepository()
        self.users = users or UserService()
        self.matcher = matcher or MatchService()

    def _to_response(self, job: Job) -> JobResponse:
        return JobResponse(
            id=str(job.id),
            title=job.title,
            company=job.company,
            location=job.location,
            salary=job.salary,
            experience=job.experience,
            description=job.description,
            skills=job.skills,
            apply_url=job.apply_url,
            portal=job.portal,
            status=job.status,
            match_score=job.match_score,
            fetched_at=job.fetched_at.isoformat(),
            created_at=job.created_at.isoformat(),
        )

    async def list_jobs(self, user_id: str, params: JobFilterParams) -> PaginatedResponse[JobResponse]:
        items, total = await self.jobs.search(
            user_id,
            q=params.q,
            portal=params.portal,
            company=params.company,
            status=params.status,
            min_score=params.min_score,
            page=params.page,
            page_size=params.page_size,
            sort_by=params.sort_by,
            sort_dir=params.sort_dir,
        )
        pages = ceil(total / params.page_size) if params.page_size else 0
        return PaginatedResponse(
            items=[self._to_response(j) for j in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )

    async def list_by_statuses(
        self,
        user_id: str,
        statuses: list[JobStatus],
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[JobResponse]:
        items, total = await self.jobs.by_status(user_id, statuses, page, page_size)
        pages = ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[self._to_response(j) for j in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def get(self, user_id: str, job_id: str) -> JobResponse:
        job = await self._owned(user_id, job_id)
        return self._to_response(job)

    async def update(self, user_id: str, job_id: str, payload: JobUpdateRequest) -> JobResponse:
        job = await self._owned(user_id, job_id)
        data = payload.model_dump(exclude_unset=True)
        data["updated_at"] = datetime.utcnow()
        job = await self.jobs.update(job, data)
        return self._to_response(job)

    async def track(self, user_id: str, job_id: str) -> JobResponse:
        return await self.update(user_id, job_id, JobUpdateRequest(status=JobStatus.TRACKED))

    async def ignore(self, user_id: str, job_id: str) -> JobResponse:
        return await self.update(user_id, job_id, JobUpdateRequest(status=JobStatus.IGNORED))

    async def match_job(self, user_id: str, job: Job) -> Job:
        user = await self.users.get_profile(user_id)
        score = self.matcher.score(user, job)
        job.match_score = score
        job.status = JobStatus.MATCHED if score >= 0.5 else job.status
        job.updated_at = datetime.utcnow()
        await job.save()
        return job

    async def trigger_fetch(self, user_id: str) -> None:
        await publish("job.fetch", {"user_id": user_id}, key=user_id)

    async def _owned(self, user_id: str, job_id: str) -> Job:
        job = await self.jobs.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Job not found")
        return job

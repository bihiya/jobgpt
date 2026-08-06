"""Job tracking service."""

from __future__ import annotations

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
        from app.schemas.job import MatchBreakdownSchema

        breakdown = job.match_breakdown.model_dump() if job.match_breakdown else {}
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
            match_breakdown=MatchBreakdownSchema(**breakdown),
            source=getattr(job, "source", "portal"),
            fetched_at=job.fetched_at.isoformat(),
            created_at=job.created_at.isoformat(),
        )

    async def list_jobs(self, user_id: str, params: JobFilterParams) -> PaginatedResponse[JobResponse]:
        # Cache Aside: Redis API response caching with namespaced keys + TTL
        fingerprint = (
            f"{params.q}|{params.portal}|{params.company}|{params.status}|"
            f"{params.min_score}|{params.page}|{params.page_size}|{params.sort_by}|{params.sort_dir}"
        )
        cache_key = None
        try:
            from app.core.config import settings
            from app.services.cache_service import CacheService

            cache = CacheService()
            cache_key = cache.jobs_key(user_id, fingerprint)

            async def _load():
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
                result = PaginatedResponse(
                    items=[self._to_response(j) for j in items],
                    total=total,
                    page=params.page,
                    page_size=params.page_size,
                    pages=pages,
                )
                return result.model_dump()

            cached = await cache.get_or_set(cache_key, _load, ttl=settings.redis_cache_ttl_seconds)
            return PaginatedResponse(**cached)
        except Exception:  # noqa: BLE001
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

    async def pipeline(self, user_id: str, *, per_column: int = 40) -> dict:
        """Kanban columns: Matched → Approved → Applied → Interview → Offer → Rejected."""
        columns = [
            ("matched", [JobStatus.MATCHED, JobStatus.AWAITING_APPROVAL, JobStatus.TRACKED]),
            ("approved", [JobStatus.APPROVED, JobStatus.APPLYING]),
            ("applied", [JobStatus.APPLIED]),
            ("interview", [JobStatus.INTERVIEW]),
            ("offer", [JobStatus.OFFER]),
            ("rejected", [JobStatus.REJECTED, JobStatus.FAILED, JobStatus.IGNORED]),
        ]
        result: dict[str, list] = {}
        counts: dict[str, int] = {}
        for key, statuses in columns:
            page = await self.list_by_statuses(user_id, statuses, page=1, page_size=per_column)
            result[key] = [
                {
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "portal": j.portal,
                    "status": getattr(j.status, "value", j.status),
                    "match_score": j.match_score,
                    "location": j.location,
                }
                for j in page.items
            ]
            counts[key] = page.total
        return {"columns": result, "counts": counts}

    async def get(self, user_id: str, job_id: str) -> JobResponse:
        job = await self._owned(user_id, job_id)
        return self._to_response(job)

    async def update(
        self,
        user_id: str,
        job_id: str,
        payload: JobUpdateRequest,
        *,
        audit_action: str | None = "job.updated",
        audit_message: str | None = None,
    ) -> JobResponse:
        job = await self._owned(user_id, job_id)
        data = payload.model_dump(exclude_unset=True)
        data["updated_at"] = datetime.utcnow()
        job = await self.jobs.update(job, data)
        if audit_action:
            from app.services.audit_service import audit_event

            await audit_event(
                user_id,
                audit_action,
                message=audit_message or f"Updated {job.title}",
                job_id=job_id,
                resource_type="job",
                resource_id=job_id,
                metadata={"fields": list(data.keys())},
            )
        return self._to_response(job)

    async def track(self, user_id: str, job_id: str) -> JobResponse:
        job = await self._owned(user_id, job_id)
        result = await self.update(
            user_id,
            job_id,
            JobUpdateRequest(status=JobStatus.TRACKED),
            audit_action="job.tracked",
            audit_message=f"Tracked {job.title}",
        )
        await self._invalidate_job_cache(user_id)
        return result

    async def ignore(self, user_id: str, job_id: str) -> JobResponse:
        job = await self._owned(user_id, job_id)
        result = await self.update(
            user_id,
            job_id,
            JobUpdateRequest(status=JobStatus.IGNORED),
            audit_action="job.ignored",
            audit_message=f"Ignored {job.title}",
        )
        await self._invalidate_job_cache(user_id)
        return result

    async def _invalidate_job_cache(self, user_id: str) -> None:
        try:
            from app.services.cache_service import CacheService

            await CacheService().invalidate_namespace("cache", "jobs", user_id)
        except Exception:  # noqa: BLE001
            pass

    async def match_job(self, user_id: str, job: Job) -> Job:
        from app.services.llm.ranking import LLMRankingService

        user = await self.users.get_profile(user_id)
        ranking = LLMRankingService(self.matcher)
        breakdown = await ranking.rank(user, job)
        job.match_score = breakdown.total
        job.match_breakdown = breakdown
        job.status = JobStatus.MATCHED if breakdown.total >= 0.5 else job.status
        job.updated_at = datetime.utcnow()
        await job.save()
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "job.matched",
            message=f"Matched {job.title} ({int(breakdown.total * 100)}%)",
            job_id=str(job.id),
            resource_type="job",
            resource_id=str(job.id),
            source="worker",
            metadata={"match_score": breakdown.total},
        )
        return job

    async def ingest_external(self, user_id: str, payload) -> JobResponse:
        """Ingest a job from Chrome extension or manual share."""
        from app.services.dedupe_service import DedupeService

        dedupe = DedupeService(self.jobs)
        external_id = payload.external_id or payload.apply_url
        fingerprint = dedupe.content_hash(
            payload.title, payload.company, str(payload.apply_url), str(external_id)
        )
        if await dedupe.is_duplicate(user_id, fingerprint, str(payload.apply_url)):
            existing = await self.jobs.find_one({"user_id": user_id, "content_hash": fingerprint})
            if existing:
                existing.status = JobStatus.DUPLICATE
                await existing.save()
                return self._to_response(existing)

        job = await self.jobs.create(
            {
                "user_id": user_id,
                "external_id": str(external_id),
                "title": payload.title,
                "company": payload.company,
                "location": payload.location,
                "salary": payload.salary,
                "experience": payload.experience,
                "description": payload.description,
                "skills": payload.skills,
                "apply_url": str(payload.apply_url),
                "portal": payload.portal,
                "content_hash": fingerprint,
                "source": "extension",
            }
        )
        await dedupe.remember(user_id, fingerprint)
        await publish("job.match", {"user_id": user_id, "job_id": str(job.id)}, key=user_id)
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "job.ingested",
            message=f"Ingested {job.title} at {job.company}",
            job_id=str(job.id),
            resource_type="job",
            resource_id=str(job.id),
            source="extension",
            severity="success",
            metadata={"portal": job.portal},
        )
        await self._invalidate_job_cache(user_id)
        return self._to_response(job)

    async def trigger_fetch(self, user_id: str) -> None:
        await publish("job.fetch", {"user_id": user_id}, key=user_id)

    async def _owned(self, user_id: str, job_id: str) -> Job:
        job = await self.jobs.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Job not found")
        return job

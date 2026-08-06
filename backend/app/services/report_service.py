"""Reports and analytics service."""

import csv
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.kafka import publish
from app.events.realtime import emit_realtime
from app.models.enums import ApplicationStatus, JobStatus, ReportStatus
from app.models.report import Report
from app.repository.application_repository import ApplicationRepository
from app.repository.job_repository import JobRepository
from app.repository.report_repository import ReportRepository
from app.schemas.common import PaginatedResponse
from app.schemas.report import AnalyticsResponse, ReportCreate, ReportResponse


class ReportService:
    def __init__(
        self,
        reports: ReportRepository | None = None,
        jobs: JobRepository | None = None,
        applications: ApplicationRepository | None = None,
    ) -> None:
        self.reports = reports or ReportRepository()
        self.jobs = jobs or JobRepository()
        self.applications = applications or ApplicationRepository()

    def _to_response(self, report: Report) -> ReportResponse:
        return ReportResponse(
            id=str(report.id),
            type=report.type,
            format=report.format,
            status=report.status,
            file_path=report.file_path,
            created_at=report.created_at.isoformat(),
        )

    async def list(self, user_id: str, page: int = 1, page_size: int = 20) -> PaginatedResponse[ReportResponse]:
        items, total = await self.reports.list_for_user(user_id, page, page_size)
        pages = ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[self._to_response(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def create(self, user_id: str, payload: ReportCreate) -> ReportResponse:
        report = await self.reports.create(
            {
                "user_id": user_id,
                "type": payload.type,
                "format": payload.format,
                "filters": payload.filters,
                "status": ReportStatus.PENDING,
            }
        )
        await publish(
            "reports",
            {"user_id": user_id, "report_id": str(report.id), "format": payload.format.value},
            key=user_id,
        )
        # Generate CSV synchronously for immediate UX; workers handle Excel/PDF asynchronously.
        if payload.format.value == "csv":
            await self.generate_csv(user_id, report)
        return self._to_response(report)

    async def generate_csv(self, user_id: str, report: Report) -> Report:
        root = Path(settings.report_dir) / user_id
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{report.id or uuid4().hex}.csv"
        apps, _ = await self.applications.list_for_user(user_id, page=1, page_size=1000)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["application_id", "job_id", "status", "attempts", "created_at"])
            for app in apps:
                writer.writerow(
                    [str(app.id), app.job_id, app.status.value, app.attempts, app.created_at.isoformat()]
                )
        report.file_path = str(path)
        report.status = ReportStatus.READY
        await report.save()
        await emit_realtime(
            user_id,
            "report.ready",
            {"report_id": str(report.id), "status": "ready"},
            title="Report ready",
            body="Your report is ready to download",
            severity="success",
        )
        return report

    async def get_download_path(self, user_id: str, report_id: str) -> str:
        report = await self.reports.get_by_id(report_id)
        if not report or report.user_id != user_id:
            raise NotFoundError("Report not found")
        if report.status != ReportStatus.READY or not report.file_path:
            raise NotFoundError("Report not ready")
        return report.file_path

    async def analytics(self, user_id: str) -> AnalyticsResponse:
        # Hot data caching (cache aside + sliding TTL warm path)
        try:
            from app.core.config import settings
            from app.services.cache_service import CacheService

            cache = CacheService()
            key = cache.analytics_key(user_id)

            async def _compute() -> dict:
                return (await self._compute_analytics(user_id)).model_dump()

            cached = await cache.get_sliding(key, ttl=settings.redis_hot_ttl_seconds)
            if cached is not None:
                return AnalyticsResponse(**cached)
            data = await _compute()
            await cache.set_sliding(key, data, ttl=settings.redis_hot_ttl_seconds)
            return AnalyticsResponse(**data)
        except Exception:  # noqa: BLE001
            return await self._compute_analytics(user_id)

    async def _compute_analytics(self, user_id: str) -> AnalyticsResponse:
        jobs_found = await self.jobs.count({"user_id": user_id})
        status_counts = await self.applications.count_by_status(user_id)
        applied = status_counts.get(ApplicationStatus.SUCCESS.value, 0)
        pending = status_counts.get(ApplicationStatus.PENDING.value, 0) + status_counts.get(
            ApplicationStatus.IN_PROGRESS.value, 0
        )
        failed = status_counts.get(ApplicationStatus.FAILED.value, 0)
        total_apps = max(applied + failed + pending, 1)
        success_rate = round(applied / total_apps * 100, 2)

        recent_jobs = await self.jobs.find_many({"user_id": user_id}, limit=200, sort=[("fetched_at", -1)])
        company_map: dict[str, int] = {}
        portal_map: dict[str, int] = {}
        skill_map: dict[str, int] = {}
        for job in recent_jobs:
            company_map[job.company] = company_map.get(job.company, 0) + 1
            portal_map[job.portal] = portal_map.get(job.portal, 0) + 1
            for skill in job.skills:
                skill_map[skill] = skill_map.get(skill, 0) + 1

        daily: dict[str, int] = {}
        apps, _ = await self.applications.list_for_user(user_id, page=1, page_size=500)
        for app in apps:
            day = app.created_at.strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0) + 1

        last_7 = [(datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        daily_applications = [{"date": d, "count": daily.get(d, 0)} for d in last_7]
        companies = [{"name": k, "count": v} for k, v in sorted(company_map.items(), key=lambda x: -x[1])[:10]]
        portal_stats = [{"portal": k, "count": v} for k, v in portal_map.items()]
        top_companies = companies[:5]
        skill_demand = [{"skill": k, "count": v} for k, v in sorted(skill_map.items(), key=lambda x: -x[1])[:15]]
        apps_per_day = round(sum(d["count"] for d in daily_applications) / 7, 2)

        _ = JobStatus
        return AnalyticsResponse(
            jobs_found=jobs_found,
            applied=applied,
            pending=pending,
            failed=failed,
            success_rate=success_rate,
            daily_applications=daily_applications,
            companies=companies,
            portal_stats=portal_stats,
            top_companies=top_companies,
            skill_demand=skill_demand,
            applications_per_day=apps_per_day,
        )

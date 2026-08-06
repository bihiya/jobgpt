"""Reports and analytics service."""

from __future__ import annotations

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
from app.models.approval import Approval
from app.models.enums import ApprovalStatus
from app.schemas.report import AnalyticsResponse, ReportCreate, ReportResponse, WeeklyStoryResponse


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

    async def weekly_story(self, user_id: str) -> WeeklyStoryResponse:
        """Narrative weekly digest — not chart soup."""
        week_ago = datetime.utcnow() - timedelta(days=7)
        apps, _ = await self.applications.list_for_user(user_id, page=1, page_size=500)
        week_apps = [a for a in apps if a.created_at and a.created_at >= week_ago]
        applied = sum(1 for a in week_apps if a.status == ApplicationStatus.SUCCESS)
        follow_ups = sum(1 for a in week_apps if a.status == ApplicationStatus.FOLLOW_UP)
        # "Replies" approximated by follow-ups + reminders completed would be nicer;
        # use follow_up + interviews as engagement signal.
        interview_jobs = await self.jobs.find_many(
            {"user_id": user_id, "status": JobStatus.INTERVIEW}, limit=100
        )
        offer_jobs = await self.jobs.find_many(
            {"user_id": user_id, "status": JobStatus.OFFER}, limit=100
        )
        interviews = sum(
            1
            for j in interview_jobs
            if not getattr(j, "updated_at", None) or j.updated_at >= week_ago
        )
        offers = sum(
            1 for j in offer_jobs if not getattr(j, "updated_at", None) or j.updated_at >= week_ago
        )

        replies = follow_ups + interviews
        approvals_pending = await Approval.find(
            {"user_id": user_id, "status": ApprovalStatus.PENDING}
        ).count()
        blockers = await Application.find(
            {
                "user_id": user_id,
                "status": {"$in": [ApplicationStatus.NEEDS_INPUT, ApplicationStatus.NEEDS_OTP]},
            }
        ).count()

        analytics = await self._compute_analytics(user_id)
        top_portal = ""
        if analytics.portal_stats:
            top_portal = max(analytics.portal_stats, key=lambda p: p.get("count", 0)).get("portal", "")

        highlights: list[str] = []
        if applied:
            highlights.append(f"You pushed {applied} application{'s' if applied != 1 else ''} this week.")
        if replies:
            highlights.append(f"{replies} reply signal{'s' if replies != 1 else ''} (follow-ups / interviews).")
        if interviews:
            highlights.append(f"{interviews} interview stage move{'s' if interviews != 1 else ''}.")
        if offers:
            highlights.append(f"{offers} offer{'s' if offers != 1 else ''} — nice work.")
        if approvals_pending:
            highlights.append(f"{approvals_pending} match{'es' if approvals_pending != 1 else ''} waiting for your yes/no.")
        if blockers:
            highlights.append(f"{blockers} apply blocker{'s' if blockers != 1 else ''} need a quick fix.")
        if top_portal:
            highlights.append(f"Most activity came from {top_portal}.")
        if not highlights:
            highlights.append("Quiet week so far — approve a few digest matches to get momentum.")

        headline = f"{applied} applied · {replies} replies · {interviews} interviews"
        narrative = (
            f"This week you applied to {applied} role{'s' if applied != 1 else ''}. "
            f"{replies} engagement signal{'s' if replies != 1 else ''} showed up"
            f"{' and ' + str(interviews) + ' moved to interview' if interviews else ''}"
            f"{', with ' + str(offers) + ' offer' + ('s' if offers != 1 else '') if offers else ''}. "
            f"{'Clear ' + str(approvals_pending) + ' pending approvals to keep the pipeline moving.' if approvals_pending else 'Pipeline looks clear on approvals.'}"
        )
        return WeeklyStoryResponse(
            headline=headline,
            narrative=narrative,
            applied=applied,
            replies=replies,
            interviews=interviews,
            offers=offers,
            approvals_pending=approvals_pending,
            blockers=blockers,
            top_portal=top_portal,
            period_label="This week",
            highlights=highlights,
        )

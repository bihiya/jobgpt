"""Application repository."""

from __future__ import annotations

from typing import Any

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.repository.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self) -> None:
        super().__init__(Application)

    async def list_for_user(
        self,
        user_id: str,
        status: ApplicationStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        job_id: str | None = None,
    ) -> tuple[list[Application], int]:
        filters: dict[str, Any] = {"user_id": user_id}
        if status:
            filters["status"] = status
        if job_id:
            filters["job_id"] = job_id
        skip = (page - 1) * page_size
        total = await self.count(filters)
        sort = [("updated_at", -1)] if job_id else [("created_at", -1)]
        items = await self.find_many(filters, skip=skip, limit=page_size, sort=sort)
        return items, total

    async def latest_for_jobs(self, user_id: str, job_ids: list[str]) -> dict[str, Application]:
        """Most recently updated application per job (for pipeline live cards)."""
        ids = [job_id for job_id in job_ids if job_id]
        if not ids:
            return {}
        items = await self.find_many(
            {"user_id": user_id, "job_id": {"$in": ids}},
            skip=0,
            limit=max(len(ids) * 10, 50),
            sort=[("updated_at", -1)],
        )
        latest: dict[str, Application] = {}
        for app in items:
            if app.job_id not in latest:
                latest[app.job_id] = app
        return latest

    async def find_active_for_job(self, user_id: str, job_id: str) -> Application | None:
        active = [
            ApplicationStatus.PENDING,
            ApplicationStatus.IN_PROGRESS,
            ApplicationStatus.RETRYING,
            ApplicationStatus.NEEDS_INPUT,
            ApplicationStatus.NEEDS_OTP,
            ApplicationStatus.NEEDS_ACCOUNT,
        ]
        return await self.find_one(
            {
                "user_id": user_id,
                "job_id": job_id,
                "status": {"$in": [status.value for status in active]},
            }
        )

    async def count_by_status(self, user_id: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for status in ApplicationStatus:
            result[status.value] = await self.count({"user_id": user_id, "status": status})
        return result

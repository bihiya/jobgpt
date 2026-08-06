"""Job repository."""

from typing import Any

from app.models.enums import JobStatus
from app.models.job import Job
from app.repository.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    def __init__(self) -> None:
        super().__init__(Job)

    async def upsert_job(self, user_id: str, external_id: str, portal: str, data: dict) -> Job:
        existing = await self.find_one(
            {"user_id": user_id, "external_id": external_id, "portal": portal}
        )
        if existing:
            return await self.update(existing, data)
        return await self.create({"user_id": user_id, "external_id": external_id, "portal": portal, **data})

    async def search(
        self,
        user_id: str,
        *,
        q: str | None = None,
        portal: str | None = None,
        company: str | None = None,
        status: JobStatus | None = None,
        min_score: float | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "fetched_at",
        sort_dir: str = "desc",
    ) -> tuple[list[Job], int]:
        filters: dict[str, Any] = {"user_id": user_id}
        if portal:
            filters["portal"] = portal
        if company:
            filters["company"] = {"$regex": company, "$options": "i"}
        if status:
            filters["status"] = status
        if min_score is not None:
            filters["match_score"] = {"$gte": min_score}
        if q:
            filters["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"company": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]

        sort_field = sort_by if sort_by in {"fetched_at", "match_score", "created_at", "title"} else "fetched_at"
        direction = -1 if sort_dir == "desc" else 1
        skip = (page - 1) * page_size
        total = await self.count(filters)
        items = await self.find_many(filters, skip=skip, limit=page_size, sort=[(sort_field, direction)])
        return items, total

    async def by_status(self, user_id: str, statuses: list[JobStatus], page: int = 1, page_size: int = 20):
        filters = {"user_id": user_id, "status": {"$in": [s.value for s in statuses]}}
        skip = (page - 1) * page_size
        total = await self.count(filters)
        items = await self.find_many(filters, skip=skip, limit=page_size, sort=[("fetched_at", -1)])
        return items, total

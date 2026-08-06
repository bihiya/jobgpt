"""Application repository."""

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
    ) -> tuple[list[Application], int]:
        filters: dict[str, Any] = {"user_id": user_id}
        if status:
            filters["status"] = status
        skip = (page - 1) * page_size
        total = await self.count(filters)
        items = await self.list(filters, skip=skip, limit=page_size, sort=[("created_at", -1)])
        return items, total

    async def count_by_status(self, user_id: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for status in ApplicationStatus:
            result[status.value] = await self.count({"user_id": user_id, "status": status})
        return result

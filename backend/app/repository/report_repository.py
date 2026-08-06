"""Report and automation log repositories."""

from app.models.automation_log import AutomationLog
from app.models.report import Report
from app.repository.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    def __init__(self) -> None:
        super().__init__(Report)

    async def list_for_user(self, user_id: str, page: int = 1, page_size: int = 20):
        filters = {"user_id": user_id}
        skip = (page - 1) * page_size
        total = await self.count(filters)
        items = await self.list(filters, skip=skip, limit=page_size, sort=[("created_at", -1)])
        return items, total


class AutomationLogRepository(BaseRepository[AutomationLog]):
    def __init__(self) -> None:
        super().__init__(AutomationLog)

    async def list_for_user(self, user_id: str, page: int = 1, page_size: int = 50):
        filters = {"user_id": user_id}
        skip = (page - 1) * page_size
        total = await self.count(filters)
        items = await self.list(filters, skip=skip, limit=page_size, sort=[("created_at", -1)])
        return items, total

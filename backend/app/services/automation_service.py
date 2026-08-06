"""Automation status and manual trigger service."""

from math import ceil

from app.core.kafka import publish
from app.repository.report_repository import AutomationLogRepository
from app.schemas.common import PaginatedResponse


class AutomationService:
    def __init__(self, logs: AutomationLogRepository | None = None) -> None:
        self.logs = logs or AutomationLogRepository()

    async def status(self, user_id: str) -> dict:
        total_logs = await self.logs.count({"user_id": user_id})
        recent, _ = await self.logs.list_for_user(user_id, page=1, page_size=5)
        return {
            "user_id": user_id,
            "workers": {
                "fetch": "idle",
                "match": "idle",
                "apply": "idle",
                "notification": "idle",
                "report": "idle",
            },
            "total_logs": total_logs,
            "recent": [
                {
                    "id": str(log.id),
                    "action": log.action,
                    "level": log.level,
                    "message": log.message,
                    "portal": log.portal,
                    "created_at": log.created_at.isoformat(),
                }
                for log in recent
            ],
        }

    async def list_logs(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[dict]:
        items, total = await self.logs.list_for_user(user_id, page, page_size)
        pages = ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[
                {
                    "id": str(log.id),
                    "action": log.action,
                    "level": log.level,
                    "message": log.message,
                    "portal": log.portal,
                    "job_id": log.job_id,
                    "correlation_id": log.correlation_id,
                    "created_at": log.created_at.isoformat(),
                }
                for log in items
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def run(self, user_id: str, job_type: str = "fetch") -> dict:
        topic_map = {
            "fetch": "job.fetch",
            "match": "job.match",
            "apply": "job.apply",
            "report": "reports",
        }
        topic = topic_map.get(job_type, "job.fetch")
        await publish(topic, {"user_id": user_id, "source": "manual"}, key=user_id)
        return {"detail": f"Triggered {job_type}", "topic": topic}

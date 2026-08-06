"""Audit log persistence."""

from __future__ import annotations

from typing import Any

from app.models.automation_log import AuditLog
from app.repository.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self) -> None:
        super().__init__(AuditLog)

    async def list_for_user(
        self,
        user_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        filters: dict[str, Any] = {"user_id": user_id}
        if action:
            filters["action"] = action
        if resource_type:
            filters["resource_type"] = resource_type
        total = await AuditLog.find(filters).count()
        items = (
            await AuditLog.find(filters)
            .sort([("created_at", -1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return items, total

    async def list_for_job(
        self,
        user_id: str,
        job_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        filters = {"user_id": user_id, "job_id": job_id}
        total = await AuditLog.find(filters).count()
        items = (
            await AuditLog.find(filters)
            .sort([("created_at", -1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return items, total

"""Record and query user/job activity audit logs."""

from __future__ import annotations

from math import ceil
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.automation_log import AuditLog
from app.repository.audit_repository import AuditLogRepository
from app.repository.job_repository import JobRepository
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse

logger = get_logger(__name__)


class AuditService:
    def __init__(
        self,
        audits: AuditLogRepository | None = None,
        jobs: JobRepository | None = None,
    ) -> None:
        self.audits = audits or AuditLogRepository()
        self.jobs = jobs or JobRepository()

    def _to_response(self, row: AuditLog) -> AuditLogResponse:
        return AuditLogResponse(
            id=str(row.id),
            user_id=row.user_id,
            actor_id=row.actor_id or row.user_id,
            action=row.action,
            message=row.message or row.action,
            resource=row.resource,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            job_id=row.job_id or "",
            application_id=row.application_id or "",
            source=row.source,
            severity=row.severity,
            ip=row.ip,
            user_agent=row.user_agent,
            metadata=row.metadata or {},
            created_at=row.created_at.isoformat(),
        )

    async def record(
        self,
        user_id: str,
        action: str,
        *,
        message: str = "",
        actor_id: str | None = None,
        resource: str = "",
        resource_type: str = "",
        resource_id: str = "",
        job_id: str = "",
        application_id: str = "",
        source: str = "user",
        severity: str = "info",
        ip: str = "",
        user_agent: str = "",
        metadata: dict[str, Any] | None = None,
        emit: bool = True,
    ) -> AuditLog:
        if job_id and not resource_type:
            resource_type = "job"
            resource_id = resource_id or job_id
        if not resource and resource_type:
            resource = f"{resource_type}:{resource_id}" if resource_id else resource_type

        entry = AuditLog(
            user_id=user_id,
            actor_id=actor_id or user_id,
            action=action,
            message=message or action.replace(".", " ").replace("_", " ").title(),
            resource=resource,
            resource_type=resource_type,
            resource_id=resource_id,
            job_id=job_id or "",
            application_id=application_id or "",
            source=source,
            severity=severity,
            ip=ip,
            user_agent=user_agent,
            metadata=metadata or {},
        )
        await entry.insert()

        if emit:
            try:
                from app.events.realtime import emit_realtime

                await emit_realtime(
                    user_id,
                    "audit.created",
                    {
                        "id": str(entry.id),
                        "action": action,
                        "job_id": entry.job_id,
                        "resource_type": entry.resource_type,
                        "severity": severity,
                    },
                    title=entry.message,
                    body=action,
                    severity=severity if severity in {"success", "error", "warning", "info"} else "info",
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("audit_realtime_failed", error=str(exc))
        return entry

    async def list_user_activity(
        self,
        user_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> PaginatedResponse[AuditLogResponse]:
        items, total = await self.audits.list_for_user(
            user_id,
            page=page,
            page_size=page_size,
            action=action,
            resource_type=resource_type,
        )
        return PaginatedResponse(
            items=[self._to_response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if page_size else 0,
        )

    async def list_job_activity(
        self,
        user_id: str,
        job_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[AuditLogResponse]:
        job = await self.jobs.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Job not found")
        items, total = await self.audits.list_for_job(
            user_id, job_id, page=page, page_size=page_size
        )
        return PaginatedResponse(
            items=[self._to_response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if page_size else 0,
        )


# Module-level helper for workers/services without DI
_default_audit = AuditService()


async def audit_event(user_id: str, action: str, **kwargs: Any) -> AuditLog | None:
    try:
        return await _default_audit.record(user_id, action, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit_record_failed", action=action, error=str(exc))
        return None

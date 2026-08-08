"""Record and query user/job activity audit logs."""

from __future__ import annotations

from enum import Enum
from math import ceil
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.automation_log import AuditLog
from app.repository.audit_repository import AuditLogRepository
from app.repository.job_repository import JobRepository
from app.repository.user_repository import UserRepository
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.services.activity_narratives import narrate_activity

logger = get_logger(__name__)

_DEFAULT_DIFF_EXCLUDE = frozenset({"updated_at", "created_at", "password", "password_hash", "hashed_password"})


def _serialize_diff_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _serialize_diff_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_diff_value(v) for v in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            pass
    return str(value)


def build_field_changes(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    exclude: set[str] | frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Return [{field, from, to}, ...] for keys that actually changed."""
    skip = set(_DEFAULT_DIFF_EXCLUDE)
    if exclude:
        skip |= set(exclude)
    changes: list[dict[str, Any]] = []
    for key in sorted(set(before) | set(after)):
        if key in skip:
            continue
        old = _serialize_diff_value(before.get(key))
        new = _serialize_diff_value(after.get(key))
        if old == new:
            continue
        changes.append({"field": key, "from": old, "to": new})
    return changes


def changes_metadata(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    exclude: set[str] | frozenset[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    changes = build_field_changes(before, after, exclude=exclude)
    meta: dict[str, Any] = {
        "fields": [c["field"] for c in changes],
        "changes": changes,
    }
    if extra:
        meta.update(extra)
    return meta


class AuditService:
    def __init__(
        self,
        audits: AuditLogRepository | None = None,
        jobs: JobRepository | None = None,
        users: UserRepository | None = None,
    ) -> None:
        self.audits = audits or AuditLogRepository()
        self.jobs = jobs or JobRepository()
        self.users = users or UserRepository()

    def _to_response(
        self,
        row: AuditLog,
        *,
        actor_name: str = "",
    ) -> AuditLogResponse:
        source = row.source or "user"
        if source in {"worker", "system"}:
            display_actor = "JobPilot"
        else:
            display_actor = actor_name or "You"
        story = narrate_activity(
            actor_name=display_actor,
            action=row.action,
            message=row.message or row.action,
            source=source,
            severity=row.severity or "info",
            metadata=row.metadata or {},
        )
        meta = dict(row.metadata or {})
        meta.setdefault("outcome", story["outcome"])
        meta.setdefault("next_step", story["next_step"])
        return AuditLogResponse(
            id=str(row.id),
            user_id=row.user_id,
            actor_id=row.actor_id or row.user_id,
            actor_name=story["actor_name"],
            action=row.action,
            message=row.message or row.action,
            summary=story["summary"],
            outcome=story["outcome"],
            next_step=story["next_step"],
            resource=row.resource,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            job_id=row.job_id or "",
            application_id=row.application_id or "",
            source=source,
            severity=row.severity,
            ip=row.ip,
            user_agent=row.user_agent,
            metadata=meta,
            created_at=row.created_at.isoformat(),
        )

    async def _actor_names(self, rows: list[AuditLog]) -> dict[str, str]:
        ids = {((row.actor_id or row.user_id) or "") for row in rows}
        ids.discard("")
        names: dict[str, str] = {}
        for actor_id in ids:
            user = await self.users.get_by_id(actor_id)
            if user:
                names[actor_id] = user.full_name or user.email or "You"
        return names

    async def _to_responses(self, rows: list[AuditLog]) -> list[AuditLogResponse]:
        names = await self._actor_names(rows)
        return [
            self._to_response(
                row,
                actor_name=names.get(row.actor_id or row.user_id, ""),
            )
            for row in rows
        ]

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
            items=await self._to_responses(items),
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
            items=await self._to_responses(items),
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

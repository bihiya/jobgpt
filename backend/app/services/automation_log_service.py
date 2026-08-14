"""Helpers to persist automation logs visible on the Automation page."""

from __future__ import annotations

from typing import Any

from app.events.realtime import emit_realtime
from app.models.automation_log import AutomationLog


async def write_automation_log(
    user_id: str,
    *,
    action: str,
    message: str,
    level: str = "info",
    portal: str = "",
    job_id: str | None = None,
    application_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str = "",
    emit: bool = True,
) -> AutomationLog:
    entry = AutomationLog(
        user_id=user_id,
        job_id=job_id,
        application_id=application_id,
        portal=portal,
        action=action,
        level=level,
        message=message,
        metadata=metadata or {},
        correlation_id=correlation_id,
    )
    await entry.insert()
    if emit:
        await emit_realtime(
            user_id,
            "automation.log",
            {
                "id": str(entry.id),
                "action": action,
                "level": level,
                "message": message,
                "portal": portal,
                "correlation_id": correlation_id,
            },
            title="Automation update",
            body=message,
            severity="error" if level == "error" else "success" if level == "success" else "info",
        )
    return entry

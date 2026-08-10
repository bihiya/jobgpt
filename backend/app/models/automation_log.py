"""Automation and audit log documents."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import Field


class AutomationLog(Document):
    user_id: Annotated[str, Indexed()]
    job_id: str | None = None
    application_id: str | None = None
    portal: str = ""
    action: str
    level: str = "info"
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: Annotated[str, Indexed()] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "automation_logs"
        indexes = [
            # Cosmos Mongo requires an index on every ORDER BY path.
            [("user_id", 1), ("created_at", -1)],
        ]


class AuditLog(Document):
    """Unified activity stream for users and jobs."""

    user_id: Annotated[str, Indexed()] = ""
    actor_id: Annotated[str, Indexed()] = ""
    action: Annotated[str, Indexed()] = ""
    message: str = ""
    resource: str = ""  # legacy / display label
    resource_type: Annotated[str, Indexed()] = ""  # user|job|application|portal|settings|auth|…
    resource_id: Annotated[str, Indexed()] = ""
    job_id: Annotated[str, Indexed()] = ""
    application_id: str = ""
    source: str = "user"  # user|worker|system
    severity: str = "info"  # info|success|warning|error
    ip: str = ""
    user_agent: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"
        indexes = [
            [("user_id", 1), ("created_at", -1)],
            [("job_id", 1), ("created_at", -1)],
            [("actor_id", 1), ("created_at", -1)],
        ]

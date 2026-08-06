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


class AuditLog(Document):
    user_id: Annotated[str, Indexed()] = ""
    action: str
    resource: str = ""
    ip: str = ""
    user_agent: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_logs"

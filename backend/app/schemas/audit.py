"""Audit / activity log schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    actor_id: str
    action: str
    message: str
    resource: str = ""
    resource_type: str = ""
    resource_id: str = ""
    job_id: str = ""
    application_id: str = ""
    source: str = "user"
    severity: str = "info"
    ip: str = ""
    user_agent: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str

"""Job portal connector documents with health scoring."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import BaseModel, Field

from app.models.enums import PortalName, PortalStatus


class ProxyConfig(BaseModel):
    server: str = ""
    username: str = ""
    password: str = ""


class PortalCredentials(BaseModel):
    username: str = ""
    password: str = ""


class PortalHealth(BaseModel):
    score: float = 100.0  # 0-100
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_error: str = ""
    auto_paused: bool = False
    paused_reason: str = ""


class Portal(Document):
    user_id: Annotated[str, Indexed()]
    name: PortalName
    credentials: PortalCredentials = Field(default_factory=PortalCredentials)
    cookies: dict[str, Any] = Field(default_factory=dict)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    status: PortalStatus = PortalStatus.DISCONNECTED
    health: PortalHealth = Field(default_factory=PortalHealth)
    last_sync_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "portals"
        indexes = [
            [("user_id", 1), ("name", 1)],
        ]

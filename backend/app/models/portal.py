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
    # Legacy / display shape; SessionVault also writes encrypted session_blob
    cookies: dict[str, Any] = Field(default_factory=dict)
    session_blob: str = ""  # Fernet-encrypted Playwright cookie list
    session_updated_at: datetime | None = None
    totp_secret: str = ""  # transient plaintext on write; cleared after vault encrypt
    totp_secret_encrypted: str = ""
    selector_version: int = 1
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    status: PortalStatus = PortalStatus.DISCONNECTED
    health: PortalHealth = Field(default_factory=PortalHealth)
    last_sync_at: datetime | None = None
    # Set when a sync is queued; cleared when the fetch worker finishes (success or fail).
    sync_started_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "portals"
        indexes = [
            [("user_id", 1), ("name", 1)],
        ]

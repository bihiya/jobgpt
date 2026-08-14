"""Job portal schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import PortalName, PortalStatus


class ProxySchema(BaseModel):
    server: str = ""
    username: str = ""
    password: str = ""


class CredentialsSchema(BaseModel):
    username: str = ""
    password: str = ""


class PortalHealthSchema(BaseModel):
    score: float = 100.0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_error: str = ""
    auto_paused: bool = False
    paused_reason: str = ""


class PortalCreate(BaseModel):
    name: PortalName
    credentials: CredentialsSchema = Field(default_factory=CredentialsSchema)
    proxy: ProxySchema = Field(default_factory=ProxySchema)
    cookies: dict | list = Field(default_factory=dict)
    totp_secret: str = ""
    selector_version: int = 1


class PortalUpdate(BaseModel):
    credentials: CredentialsSchema | None = None
    proxy: ProxySchema | None = None
    cookies: dict | list | None = None
    totp_secret: str | None = None
    selector_version: int | None = None
    status: PortalStatus | None = None
    clear_credentials: bool = False


class PortalResponse(BaseModel):
    id: str
    name: PortalName
    status: PortalStatus
    last_sync_at: str | None = None
    last_attempt_at: str | None = None
    sync_started_at: str | None = None
    created_at: str
    username: str = ""
    has_credentials: bool = False
    has_password: bool = False
    has_session: bool = False
    has_totp: bool = False
    session_updated_at: str | None = None
    selector_version: int = 1
    health: PortalHealthSchema = Field(default_factory=PortalHealthSchema)

    model_config = {"from_attributes": True}

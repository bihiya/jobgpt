"""Job portal schemas."""

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
    cookies: dict = Field(default_factory=dict)


class PortalUpdate(BaseModel):
    credentials: CredentialsSchema | None = None
    proxy: ProxySchema | None = None
    cookies: dict | None = None
    status: PortalStatus | None = None


class PortalResponse(BaseModel):
    id: str
    name: PortalName
    status: PortalStatus
    last_sync_at: str | None = None
    created_at: str
    has_credentials: bool = False
    health: PortalHealthSchema = Field(default_factory=PortalHealthSchema)

    model_config = {"from_attributes": True}

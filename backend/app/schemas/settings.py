"""Settings schemas."""

from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    match_threshold: float | None = Field(default=None, ge=0, le=1)
    auto_apply: bool | None = None
    max_applications_per_day: int | None = Field(default=None, ge=1, le=500)
    headless: bool | None = None
    timezone: str | None = None
    notification_email: bool | None = None


class SettingsResponse(BaseModel):
    match_threshold: float
    auto_apply: bool
    max_applications_per_day: int
    headless: bool
    timezone: str
    notification_email: bool

    model_config = {"from_attributes": True}

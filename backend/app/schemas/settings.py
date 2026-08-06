"""Settings schemas."""

from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    match_threshold: float | None = Field(default=None, ge=0, le=1)
    auto_apply: bool | None = None
    require_approval: bool | None = None
    use_llm_ranking: bool | None = None
    max_applications_per_day: int | None = Field(default=None, ge=1, le=500)
    headless: bool | None = None
    timezone: str | None = None
    notification_email: bool | None = None
    follow_up_days: int | None = Field(default=None, ge=1, le=60)


class SettingsResponse(BaseModel):
    match_threshold: float
    auto_apply: bool
    require_approval: bool = True
    use_llm_ranking: bool = True
    max_applications_per_day: int
    headless: bool
    timezone: str
    notification_email: bool
    onboarding_completed: bool = False
    onboarding_step: str = "profile"
    follow_up_days: int = 7

    model_config = {"from_attributes": True}

"""User settings documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class UserSettings(Document):
    user_id: Annotated[str, Indexed(unique=True)]
    match_threshold: float = 0.7
    auto_apply: bool = False  # safer default: human-in-the-loop
    require_approval: bool = True
    use_llm_ranking: bool = True
    max_applications_per_day: int = 15  # safer default for portal anti-ban
    apply_cooldown_seconds: int = 45
    batch_min_score: float = 0.85
    headless: bool = True
    timezone: str = "UTC"
    notification_email: bool = True
    onboarding_completed: bool = False
    onboarding_step: str = "profile"  # profile|resume|portals|sync|done
    follow_up_days: int = 7
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "settings"

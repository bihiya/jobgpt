"""User settings documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class UserSettings(Document):
    user_id: Annotated[str, Indexed(unique=True)]
    match_threshold: float = 0.7
    auto_apply: bool = True
    max_applications_per_day: int = 50
    headless: bool = True
    timezone: str = "UTC"
    notification_email: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "settings"

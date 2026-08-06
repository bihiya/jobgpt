"""User notification channel configuration."""

from datetime import datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import AlertChannel


class NotificationChannel(Document):
    user_id: Annotated[str, Indexed()]
    channel: AlertChannel
    target: str  # email, slack webhook URL, or custom webhook URL
    is_enabled: bool = True
    events: list[str] = Field(
        default_factory=lambda: ["job.success", "job.failed", "approval.needed", "reminder.due"]
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "notification_channels"

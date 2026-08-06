"""Notification documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class Notification(Document):
    user_id: Annotated[str, Indexed()]
    title: str
    body: str
    type: str = "info"
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "notifications"

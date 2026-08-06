"""Application follow-up reminders."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class Reminder(Document):
    user_id: Annotated[str, Indexed()]
    application_id: Annotated[str, Indexed()]
    job_id: str = ""
    title: str
    due_at: Annotated[datetime, Indexed()]
    is_completed: bool = False
    channel: str = "in_app"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reminders"

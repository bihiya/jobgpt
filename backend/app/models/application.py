"""Job application documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import ApplicationStatus


class Application(Document):
    user_id: Annotated[str, Indexed()]
    job_id: Annotated[str, Indexed()]
    resume_id: str | None = None
    status: ApplicationStatus = ApplicationStatus.PENDING
    attempts: int = 0
    next_retry_at: datetime | None = None
    screenshot_path: str = ""
    error_message: str = ""
    applied_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "applications"
        indexes = [
            [("user_id", 1), ("status", 1)],
        ]

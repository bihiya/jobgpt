"""Job application documents with follow-up support."""

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
    follow_up_at: datetime | None = None
    screenshot_path: str = ""
    screenshot_url: str = ""  # S3 URL when using object storage
    error_message: str = ""
    applied_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "applications"
        indexes = [
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("follow_up_at", 1)],
            [("user_id", 1), ("applied_at", 1)],
        ]

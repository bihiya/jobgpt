"""Job application documents with follow-up support."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

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
    # Apply session recorder + human blockers
    session_steps: list[dict[str, Any]] = Field(default_factory=list)
    correlation_id: str = ""
    unknown_questions: list[str] = Field(default_factory=list)
    blocker_type: str = ""  # unknown_question | otp | ""
    fail_proof_html: str = ""
    fail_proof_path: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "applications"
        indexes = [
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("follow_up_at", 1)],
            [("user_id", 1), ("applied_at", 1)],
            # Cosmos Mongo requires an index on every ORDER BY path.
            [("user_id", 1), ("created_at", -1)],
            [("user_id", 1), ("updated_at", -1)],
        ]

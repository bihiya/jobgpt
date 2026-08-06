"""Job listing documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import JobStatus


class Job(Document):
    user_id: Annotated[str, Indexed()]
    external_id: str
    title: str
    company: str
    location: str = ""
    salary: str = ""
    experience: str = ""
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    apply_url: str = ""
    portal: Annotated[str, Indexed()]
    status: JobStatus = JobStatus.NEW
    match_score: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "jobs"
        indexes = [
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("match_score", -1)],
            [("external_id", 1), ("portal", 1)],
        ]

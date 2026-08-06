"""Scheduler job documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class SchedulerJob(Document):
    user_id: Annotated[str, Indexed()]
    name: str
    job_type: str  # fetch | match | apply | report
    cron: str = ""
    interval_seconds: int = 3600
    is_enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "scheduler_jobs"

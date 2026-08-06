"""Application schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import ApplicationStatus


class ApplicationCreate(BaseModel):
    job_id: str
    resume_id: str | None = None


class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    resume_id: str | None
    status: ApplicationStatus
    attempts: int
    screenshot_path: str
    error_message: str
    applied_at: str | None
    created_at: str

    model_config = {"from_attributes": True}

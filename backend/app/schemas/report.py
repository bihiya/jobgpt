"""Report and analytics schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ReportFormat, ReportStatus


class ReportCreate(BaseModel):
    type: str = "custom"
    format: ReportFormat = ReportFormat.CSV
    filters: dict[str, Any] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    id: str
    type: str
    format: ReportFormat
    status: ReportStatus
    file_path: str
    created_at: str

    model_config = {"from_attributes": True}


class AnalyticsResponse(BaseModel):
    jobs_found: int
    applied: int
    pending: int
    failed: int
    success_rate: float
    daily_applications: list[dict[str, Any]]
    companies: list[dict[str, Any]]
    portal_stats: list[dict[str, Any]]
    top_companies: list[dict[str, Any]]
    skill_demand: list[dict[str, Any]]
    applications_per_day: float

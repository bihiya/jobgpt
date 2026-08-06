"""Report documents."""

from datetime import datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import ReportFormat, ReportStatus


class Report(Document):
    user_id: Annotated[str, Indexed()]
    type: str = "custom"
    format: ReportFormat = ReportFormat.CSV
    file_path: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)
    status: ReportStatus = ReportStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reports"

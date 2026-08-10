"""Human-in-the-loop approval queue."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import ApprovalStatus


class Approval(Document):
    user_id: Annotated[str, Indexed()]
    job_id: Annotated[str, Indexed()]
    status: ApprovalStatus = ApprovalStatus.PENDING
    match_score: float = 0.0
    summary: str = ""
    decided_at: datetime | None = None
    expires_at: datetime | None = None
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "approvals"
        indexes = [
            [("user_id", 1), ("status", 1)],
            # Cosmos Mongo requires an index on every ORDER BY path.
            [("user_id", 1), ("created_at", -1)],
            [("user_id", 1), ("match_score", -1)],
        ]

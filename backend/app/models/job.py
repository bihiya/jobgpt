"""Job listing documents with match breakdown and dedupe fingerprint."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import BaseModel, Field

from app.models.enums import JobStatus


class MatchBreakdown(BaseModel):
    total: float = 0.0
    skills: float = 0.0
    keywords: float = 0.0
    location: float = 0.0
    experience: float = 0.0
    llm_score: float | None = None
    llm_rationale: str = ""
    reasons: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


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
    match_breakdown: MatchBreakdown = Field(default_factory=MatchBreakdown)
    content_hash: Annotated[str, Indexed()] = ""  # dedupe fingerprint
    source: str = "portal"  # portal | extension | manual
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "jobs"
        indexes = [
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("match_score", -1)],
            [("external_id", 1), ("portal", 1)],
            [("user_id", 1), ("content_hash", 1)],
            [("user_id", 1), ("apply_url", 1)],
        ]

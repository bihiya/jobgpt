"""Job schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import JobStatus

PipelineColumn = Literal["fetched", "queued", "applied", "interview", "shortlisted"]


class MatchBreakdownSchema(BaseModel):
    total: float = 0.0
    skills: float = 0.0
    keywords: float = 0.0
    location: float = 0.0
    experience: float = 0.0
    llm_score: float | None = None
    llm_rationale: str = ""
    reasons: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str
    salary: str
    experience: str
    description: str
    skills: list[str]
    apply_url: str
    portal: str
    status: JobStatus
    match_score: float
    match_breakdown: MatchBreakdownSchema = Field(default_factory=MatchBreakdownSchema)
    source: str = "portal"
    fetched_at: str
    created_at: str

    model_config = {"from_attributes": True}


class JobUpdateRequest(BaseModel):
    status: JobStatus | None = None


class JobMoveRequest(BaseModel):
    """Drag-and-drop pipeline move. Queued starts auto-apply."""

    column: PipelineColumn
    resume_id: str | None = None


class JobPipelineCard(BaseModel):
    id: str
    title: str
    company: str
    portal: str
    status: str
    match_score: float
    location: str = ""


class JobMoveResponse(BaseModel):
    job: JobResponse
    column: PipelineColumn
    queued: bool = False
    application_id: str | None = None


class JobFilterParams(BaseModel):
    q: str | None = None
    portal: str | None = None
    company: str | None = None
    status: JobStatus | None = None
    min_score: float | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "fetched_at"
    sort_dir: str = "desc"


class JobIngestRequest(BaseModel):
    """Chrome extension / manual ingest."""

    title: str
    company: str
    apply_url: HttpUrl | str
    location: str = ""
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    portal: str = "extension"
    external_id: str | None = None
    salary: str = ""
    experience: str = ""

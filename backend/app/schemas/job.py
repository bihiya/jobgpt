"""Job schemas."""

from pydantic import BaseModel, Field

from app.models.enums import JobStatus


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
    fetched_at: str
    created_at: str

    model_config = {"from_attributes": True}


class JobUpdateRequest(BaseModel):
    status: JobStatus | None = None


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

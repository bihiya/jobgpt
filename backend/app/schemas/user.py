"""User and resume schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SalaryExpectationSchema(BaseModel):
    min: int = 0
    max: int = 0
    currency: str = "USD"


class UserProfileSchema(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0
    location: str = ""
    salary_expectation: SalaryExpectationSchema = Field(default_factory=SalaryExpectationSchema)
    keywords: list[str] = Field(default_factory=list)
    notice_period_days: int = 0
    phone: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    profile: UserProfileSchema | None = None


class ResumeResponse(BaseModel):
    id: str
    name: str
    file_type: str
    is_default: bool
    created_at: str

    model_config = {"from_attributes": True}

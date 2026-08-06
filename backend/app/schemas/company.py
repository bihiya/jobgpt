"""Company schemas."""

from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import CompanyPlatform, CompanyStatus


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    career_url: HttpUrl | str
    platform: CompanyPlatform = CompanyPlatform.CUSTOM
    priority: int = Field(default=1, ge=1, le=100)
    tags: list[str] = Field(default_factory=list)
    status: CompanyStatus = CompanyStatus.ACTIVE


class CompanyUpdate(BaseModel):
    name: str | None = None
    career_url: HttpUrl | str | None = None
    platform: CompanyPlatform | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
    tags: list[str] | None = None
    status: CompanyStatus | None = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    career_url: str
    platform: CompanyPlatform
    priority: int
    tags: list[str]
    status: CompanyStatus
    created_at: str

    model_config = {"from_attributes": True}

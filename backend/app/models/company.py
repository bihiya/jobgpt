"""Company configuration documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import CompanyPlatform, CompanyStatus


class Company(Document):
    user_id: Annotated[str, Indexed()]
    name: Annotated[str, Indexed()]
    career_url: str
    platform: CompanyPlatform = CompanyPlatform.CUSTOM
    priority: int = 1
    tags: list[str] = Field(default_factory=list)
    status: CompanyStatus = CompanyStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "companies"

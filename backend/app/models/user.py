"""User and related auth documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class SalaryExpectation(BaseModel):
    min: int = 0
    max: int = 0
    currency: str = "USD"


class UserProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0
    location: str = ""
    salary_expectation: SalaryExpectation = Field(default_factory=SalaryExpectation)
    keywords: list[str] = Field(default_factory=list)
    notice_period_days: int = 0
    phone: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""


class User(Document):
    email: Annotated[EmailStr, Indexed(unique=True)]
    hashed_password: str
    full_name: str
    roles: list[UserRole] = Field(default_factory=lambda: [UserRole.USER])
    is_active: bool = True
    profile: UserProfile = Field(default_factory=UserProfile)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"


class Role(Document):
    name: Annotated[str, Indexed(unique=True)]
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "roles"


class RefreshToken(Document):
    user_id: Annotated[str, Indexed()]
    token_hash: Annotated[str, Indexed(unique=True)]
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "refresh_tokens"

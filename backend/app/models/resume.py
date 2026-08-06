"""Resume documents."""

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class Resume(Document):
    user_id: Annotated[str, Indexed()]
    name: str
    file_path: str
    file_type: str
    is_default: bool = False
    parsed_text: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "resumes"

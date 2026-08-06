"""Smart question bank for application forms."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field


class QuestionAnswer(Document):
    user_id: Annotated[str, Indexed()]
    question: str
    question_normalized: Annotated[str, Indexed()] = ""
    answer: str
    tags: list[str] = Field(default_factory=list)
    portals: list[str] = Field(default_factory=list)
    use_count: int = 0
    last_used_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "question_bank"
        indexes = [
            [("user_id", 1), ("question_normalized", 1)],
        ]

"""Resume repository."""

from __future__ import annotations

from app.models.resume import Resume
from app.repository.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self) -> None:
        super().__init__(Resume)

    async def list_for_user(self, user_id: str) -> list[Resume]:
        return await self.find_many({"user_id": user_id}, limit=50, sort=[("created_at", -1)])

    async def get_default(self, user_id: str) -> Resume | None:
        return await self.find_one({"user_id": user_id, "is_default": True})

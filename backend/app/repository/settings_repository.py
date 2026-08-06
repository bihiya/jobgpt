"""Settings repository."""

from app.models.settings import UserSettings
from app.repository.base import BaseRepository


class SettingsRepository(BaseRepository[UserSettings]):
    def __init__(self) -> None:
        super().__init__(UserSettings)

    async def get_or_create(self, user_id: str) -> UserSettings:
        existing = await self.find_one({"user_id": user_id})
        if existing:
            return existing
        return await self.create({"user_id": user_id})

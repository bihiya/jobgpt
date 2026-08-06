"""Portal repository."""

from app.models.enums import PortalName
from app.models.portal import Portal
from app.repository.base import BaseRepository


class PortalRepository(BaseRepository[Portal]):
    def __init__(self) -> None:
        super().__init__(Portal)

    async def list_for_user(self, user_id: str) -> list[Portal]:
        return await self.find_many({"user_id": user_id}, limit=100, sort=[("name", 1)])

    async def get_by_name(self, user_id: str, name: PortalName) -> Portal | None:
        return await self.find_one({"user_id": user_id, "name": name})

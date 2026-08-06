"""Company repository."""

from app.models.company import Company
from app.repository.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self) -> None:
        super().__init__(Company)

    async def list_for_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Company], int]:
        filters = {"user_id": user_id}
        skip = (page - 1) * page_size
        total = await self.count(filters)
        items = await self.list(filters, skip=skip, limit=page_size, sort=[("priority", 1), ("name", 1)])
        return items, total

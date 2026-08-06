"""Company configuration service."""

from datetime import datetime
from math import ceil

from app.core.exceptions import NotFoundError
from app.models.company import Company
from app.repository.company_repository import CompanyRepository
from app.schemas.common import PaginatedResponse
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate


class CompanyService:
    def __init__(self, companies: CompanyRepository | None = None) -> None:
        self.companies = companies or CompanyRepository()

    def _to_response(self, company: Company) -> CompanyResponse:
        return CompanyResponse(
            id=str(company.id),
            name=company.name,
            career_url=str(company.career_url),
            platform=company.platform,
            priority=company.priority,
            tags=company.tags,
            status=company.status,
            created_at=company.created_at.isoformat(),
        )

    async def list(self, user_id: str, page: int = 1, page_size: int = 50) -> PaginatedResponse[CompanyResponse]:
        items, total = await self.companies.list_for_user(user_id, page, page_size)
        pages = ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[self._to_response(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def create(self, user_id: str, payload: CompanyCreate) -> CompanyResponse:
        company = await self.companies.create(
            {
                "user_id": user_id,
                **payload.model_dump(),
                "career_url": str(payload.career_url),
            }
        )
        return self._to_response(company)

    async def get(self, user_id: str, company_id: str) -> CompanyResponse:
        company = await self._owned(user_id, company_id)
        return self._to_response(company)

    async def update(self, user_id: str, company_id: str, payload: CompanyUpdate) -> CompanyResponse:
        company = await self._owned(user_id, company_id)
        data = payload.model_dump(exclude_unset=True)
        if "career_url" in data and data["career_url"] is not None:
            data["career_url"] = str(data["career_url"])
        data["updated_at"] = datetime.utcnow()
        company = await self.companies.update(company, data)
        return self._to_response(company)

    async def delete(self, user_id: str, company_id: str) -> None:
        company = await self._owned(user_id, company_id)
        await self.companies.delete(company)

    async def _owned(self, user_id: str, company_id: str) -> Company:
        company = await self.companies.get_by_id(company_id)
        if not company or company.user_id != user_id:
            raise NotFoundError("Company not found")
        return company

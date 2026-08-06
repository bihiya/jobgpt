"""Company configuration endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.dependencies.services import get_company_service
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=PaginatedResponse[CompanyResponse])
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return await service.list(str(user.id), page, page_size)


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    payload: CompanyCreate,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return await service.create(str(user.id), payload)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return await service.get(str(user.id), company_id)


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str,
    payload: CompanyUpdate,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    return await service.update(str(user.id), company_id, payload)


@router.delete("/{company_id}", response_model=MessageResponse)
async def delete_company(
    company_id: str,
    user: User = Depends(get_current_user),
    service: CompanyService = Depends(get_company_service),
):
    await service.delete(str(user.id), company_id)
    return MessageResponse(detail="Company deleted")

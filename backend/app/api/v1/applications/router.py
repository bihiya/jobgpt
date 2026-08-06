"""Application endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user
from app.models.enums import ApplicationStatus
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationResponse
from app.schemas.common import PaginatedResponse
from app.dependencies.services import get_application_service
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=PaginatedResponse[ApplicationResponse])
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ApplicationStatus | None = None,
    user: User = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
):
    return await service.list(str(user.id), page, page_size, status)


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    user: User = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
):
    return await service.get(str(user.id), application_id)


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    payload: ApplicationCreate,
    user: User = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
):
    return await service.queue(str(user.id), payload)


@router.post("/{application_id}/retry", response_model=ApplicationResponse)
async def retry_application(
    application_id: str,
    user: User = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
):
    return await service.retry(str(user.id), application_id)

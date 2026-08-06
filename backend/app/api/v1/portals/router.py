"""Job portal connector endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.portal import PortalCreate, PortalResponse, PortalUpdate
from app.dependencies.services import get_portal_service
from app.services.portal_service import PortalService

router = APIRouter(prefix="/job-portals", tags=["job-portals"])


@router.get("", response_model=list[PortalResponse])
async def list_portals(
    user: User = Depends(get_current_user),
    service: PortalService = Depends(get_portal_service),
):
    return await service.list(str(user.id))


@router.post("", response_model=PortalResponse, status_code=201)
async def create_portal(
    payload: PortalCreate,
    user: User = Depends(get_current_user),
    service: PortalService = Depends(get_portal_service),
):
    return await service.create(str(user.id), payload)


@router.patch("/{portal_id}", response_model=PortalResponse)
async def update_portal(
    portal_id: str,
    payload: PortalUpdate,
    user: User = Depends(get_current_user),
    service: PortalService = Depends(get_portal_service),
):
    return await service.update(str(user.id), portal_id, payload)


@router.post("/{portal_id}/sync", response_model=PortalResponse)
async def sync_portal(
    portal_id: str,
    user: User = Depends(get_current_user),
    service: PortalService = Depends(get_portal_service),
):
    return await service.sync(str(user.id), portal_id)


@router.delete("/{portal_id}", response_model=MessageResponse)
async def delete_portal(
    portal_id: str,
    user: User = Depends(get_current_user),
    service: PortalService = Depends(get_portal_service),
):
    await service.delete(str(user.id), portal_id)
    return MessageResponse(detail="Portal disconnected")

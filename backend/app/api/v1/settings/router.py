"""Settings endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.dependencies.services import get_settings_service
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
):
    return await service.get(str(user.id))


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
):
    return await service.update(str(user.id), payload)

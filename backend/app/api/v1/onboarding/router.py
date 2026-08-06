"""Onboarding wizard API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class AdvanceRequest(BaseModel):
    step: str


@router.get("/status")
async def onboarding_status(user: User = Depends(get_current_user)):
    return await OnboardingService().status(str(user.id))


@router.post("/advance")
async def advance(payload: AdvanceRequest, user: User = Depends(get_current_user)):
    return await OnboardingService().advance(str(user.id), payload.step)


@router.post("/first-sync")
async def first_sync(user: User = Depends(get_current_user)):
    return await OnboardingService().trigger_first_sync(str(user.id))

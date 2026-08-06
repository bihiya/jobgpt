"""Automation endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/status")
async def automation_status(
    user: User = Depends(get_current_user),
    service: AutomationService = Depends(AutomationService),
):
    return await service.status(str(user.id))


@router.get("/logs", response_model=PaginatedResponse[dict])
async def automation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    service: AutomationService = Depends(AutomationService),
):
    return await service.list_logs(str(user.id), page, page_size)


@router.post("/run")
async def run_automation(
    job_type: str = "fetch",
    user: User = Depends(get_current_user),
    service: AutomationService = Depends(AutomationService),
):
    return await service.run(str(user.id), job_type)

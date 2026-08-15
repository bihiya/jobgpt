"""Reports and analytics endpoints."""

from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.dependencies.auth import get_current_user
from app.dependencies.services import get_report_service
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.report import AnalyticsResponse, ReportCreate, ReportResponse, WeeklyStoryResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=PaginatedResponse[ReportResponse])
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return await service.list(str(user.id), page, page_size)


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    payload: ReportCreate,
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return await service.create(str(user.id), payload)


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return await service.analytics(str(user.id))


@router.get("/weekly-story", response_model=WeeklyStoryResponse)
async def weekly_story(
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return await service.weekly_story(str(user.id))


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    data, filename = await service.get_download_bytes(str(user.id), report_id)
    return StreamingResponse(
        BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

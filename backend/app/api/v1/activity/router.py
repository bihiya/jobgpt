"""User and job activity (audit log) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter(tags=["activity"])


def get_audit_service() -> AuditService:
    return AuditService()


@router.get("/users/me/activity", response_model=PaginatedResponse[AuditLogResponse])
async def my_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str | None = None,
    resource_type: str | None = None,
    user: User = Depends(get_current_user),
    service: AuditService = Depends(get_audit_service),
):
    return await service.list_user_activity(
        str(user.id),
        page=page,
        page_size=page_size,
        action=action,
        resource_type=resource_type,
    )


@router.get("/activity", response_model=PaginatedResponse[AuditLogResponse])
async def activity_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str | None = None,
    resource_type: str | None = None,
    user: User = Depends(get_current_user),
    service: AuditService = Depends(get_audit_service),
):
    """Alias for the global activity page."""
    return await service.list_user_activity(
        str(user.id),
        page=page,
        page_size=page_size,
        action=action,
        resource_type=resource_type,
    )


@router.get("/jobs/{job_id}/activity", response_model=PaginatedResponse[AuditLogResponse])
async def job_activity(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: AuditService = Depends(get_audit_service),
):
    return await service.list_job_activity(
        str(user.id),
        job_id,
        page=page,
        page_size=page_size,
    )

"""Application endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.exceptions import NotFoundError
from app.core.kafka import publish
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_application_service
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.user import User
from app.repository.job_repository import JobRepository
from app.repository.portal_repository import PortalRepository
from app.schemas.application import ApplicationCreate, ApplicationResponse
from app.schemas.common import PaginatedResponse
from app.services.application_service import ApplicationService
from app.services.session_vault import SessionVault

router = APIRouter(prefix="/applications", tags=["applications"])


class OtpSubmit(BaseModel):
    code: str = Field(min_length=4, max_length=12)
    save_totp_secret: str = ""  # optional: persist TOTP seed for future autosolve


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


@router.post("/{application_id}/cancel", response_model=ApplicationResponse)
async def cancel_application(
    application_id: str,
    user: User = Depends(get_current_user),
    service: ApplicationService = Depends(get_application_service),
):
    return await service.cancel(str(user.id), application_id)


@router.post("/{application_id}/otp")
async def submit_otp(
    application_id: str,
    payload: OtpSubmit,
    user: User = Depends(get_current_user),
):
    """Provide portal OTP for a NEEDS_OTP application and resume apply."""
    app = await Application.get(application_id)
    if not app or app.user_id != str(user.id):
        raise NotFoundError("Application not found")
    if app.status != ApplicationStatus.NEEDS_OTP:
        raise NotFoundError("Application is not waiting for OTP")

    job = await JobRepository().get_by_id(app.job_id)
    if job:
        portal = await PortalRepository().find_one(
            {"user_id": str(user.id), "name": job.portal}
        )
        if portal and payload.save_totp_secret:
            vault = SessionVault()
            vault.save_totp_secret(portal, payload.save_totp_secret)
            await portal.save()

    app.status = ApplicationStatus.PENDING
    app.blocker_type = ""
    app.error_message = ""
    app.updated_at = datetime.utcnow()
    # Stash one-shot OTP for worker via metadata on next apply — also set env-like field
    app.session_steps = list(app.session_steps or []) + [
        {
            "key": "otp_provided",
            "label": "User provided OTP",
            "status": "ok",
            "detail": "queued",
            "metadata": {"code_len": len(payload.code)},
        }
    ]
    await app.save()

    await publish(
        "job.apply",
        {
            "user_id": str(user.id),
            "job_id": app.job_id,
            "application_id": str(app.id),
            "otp_code": payload.code,
            "resumed_from": "otp",
        },
        key=str(user.id),
    )
    return {"application_id": str(app.id), "status": "queued"}

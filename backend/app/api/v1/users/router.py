"""User profile and resume endpoints."""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.dependencies.auth import get_current_user
from app.dependencies.services import get_user_service
from app.models.resume import Resume
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.common import MessageResponse
from app.schemas.user import ResumeResponse, UserProfileSchema, UserUpdateRequest
from app.services.user_service import UserService, resume_content_disposition

router = APIRouter(prefix="/users", tags=["users"])


def _resume_payload(resume: Resume) -> ResumeResponse:
    created = resume.created_at.isoformat() if resume.created_at else ""
    return ResumeResponse(
        id=str(resume.id),
        name=resume.name,
        file_type=resume.file_type,
        is_default=resume.is_default,
        created_at=created,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    profile = await service.get_profile(str(user.id))
    return UserResponse(
        id=str(profile.id),
        email=profile.email,
        full_name=profile.full_name,
        roles=profile.roles,
        is_active=profile.is_active,
        profile=UserProfileSchema(**profile.profile.model_dump()),
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    profile = await service.update_profile(str(user.id), payload)
    return UserResponse(
        id=str(profile.id),
        email=profile.email,
        full_name=profile.full_name,
        roles=profile.roles,
        is_active=profile.is_active,
        profile=UserProfileSchema(**profile.profile.model_dump()),
    )


@router.get("/me/resumes", response_model=list[ResumeResponse])
async def list_resumes(
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    resumes = await service.list_resumes(str(user.id))
    return [_resume_payload(r) for r in resumes]


@router.post("/me/resumes", response_model=ResumeResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    is_default: bool = Form(default=False),
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    resume = await service.upload_resume(str(user.id), file, name=name, is_default=is_default)
    return _resume_payload(resume)


@router.get("/me/resumes/{resume_id}/download")
async def download_resume(
    resume_id: str,
    inline: bool = Query(default=False),
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    data, filename, media_type = await service.download_resume(str(user.id), resume_id)
    return StreamingResponse(
        BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": resume_content_disposition(filename, inline=inline)},
    )


@router.delete("/me/resumes/{resume_id}", response_model=MessageResponse)
async def delete_resume(
    resume_id: str,
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    await service.delete_resume(str(user.id), resume_id)
    return MessageResponse(detail="Resume deleted")

"""User and resume service."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.resume import Resume
from app.models.user import User
from app.repository.resume_repository import ResumeRepository
from app.repository.user_repository import UserRepository
from app.schemas.user import UserUpdateRequest


class UserService:
    def __init__(
        self,
        users: UserRepository | None = None,
        resumes: ResumeRepository | None = None,
    ) -> None:
        self.users = users or UserRepository()
        self.resumes = resumes or ResumeRepository()

    async def get_profile(self, user_id: str) -> User:
        user = await self.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def update_profile(self, user_id: str, payload: UserUpdateRequest) -> User:
        user = await self.get_profile(user_id)
        data: dict = {"updated_at": datetime.utcnow()}
        diff_before: dict = {}
        diff_after: dict = {}
        if payload.full_name is not None:
            diff_before["full_name"] = user.full_name
            diff_after["full_name"] = payload.full_name
            data["full_name"] = payload.full_name
        if payload.profile is not None:
            old_profile = (
                user.profile.model_dump()
                if hasattr(user.profile, "model_dump")
                else dict(user.profile or {})
            )
            new_profile = payload.profile.model_dump()
            data["profile"] = new_profile
            for key, new_val in new_profile.items():
                old_val = old_profile.get(key)
                if old_val != new_val:
                    diff_before[f"profile.{key}"] = old_val
                    diff_after[f"profile.{key}"] = new_val
        updated = await self.users.update(user, data)
        from app.services.audit_service import audit_event, changes_metadata

        await audit_event(
            user_id,
            "profile.updated",
            message="updated profile details",
            resource_type="user",
            resource_id=user_id,
            severity="success",
            metadata=changes_metadata(
                diff_before,
                diff_after,
                extra={
                    "outcome": "Passed",
                    "next_step": "Updated profile will be used on the next application.",
                },
            ),
        )
        return updated

    async def upload_resume(
        self,
        user_id: str,
        file: UploadFile,
        name: str | None = None,
        is_default: bool = False,
    ) -> Resume:
        upload_root = Path(settings.upload_dir) / user_id
        upload_root.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename or "resume.pdf").suffix.lower() or ".pdf"
        filename = f"{uuid4().hex}{ext}"
        path = upload_root / filename

        async with aiofiles.open(path, "wb") as out:
            content = await file.read()
            await out.write(content)

        if is_default:
            for existing in await self.resumes.list_for_user(user_id):
                if existing.is_default:
                    existing.is_default = False
                    await existing.save()

        resume = await self.resumes.create(
            {
                "user_id": user_id,
                "name": name or file.filename or filename,
                "file_path": str(path),
                "file_type": ext.lstrip("."),
                "is_default": is_default or not await self.resumes.list_for_user(user_id),
            }
        )
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "resume.uploaded",
            message=f"Uploaded resume {resume.name}",
            resource_type="resume",
            resource_id=str(resume.id),
            severity="success",
            metadata={"file_type": resume.file_type},
        )
        return resume

    async def list_resumes(self, user_id: str) -> list[Resume]:
        return await self.resumes.list_for_user(user_id)

    async def delete_resume(self, user_id: str, resume_id: str) -> None:
        resume = await self.resumes.get_by_id(resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume not found")
        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        await self.resumes.delete(resume)
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "resume.deleted",
            message=f"Deleted resume {resume.name}",
            resource_type="resume",
            resource_id=resume_id,
            severity="warning",
        )

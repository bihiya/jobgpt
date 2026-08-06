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
        if payload.full_name is not None:
            data["full_name"] = payload.full_name
        if payload.profile is not None:
            data["profile"] = payload.profile.model_dump()
        return await self.users.update(user, data)

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

        return await self.resumes.create(
            {
                "user_id": user_id,
                "name": name or file.filename or filename,
                "file_path": str(path),
                "file_type": ext.lstrip("."),
                "is_default": is_default or not await self.resumes.list_for_user(user_id),
            }
        )

    async def list_resumes(self, user_id: str) -> list[Resume]:
        return await self.resumes.list_for_user(user_id)

    async def delete_resume(self, user_id: str, resume_id: str) -> None:
        resume = await self.resumes.get_by_id(resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume not found")
        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        await self.resumes.delete(resume)

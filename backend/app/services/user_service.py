"""User and resume service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import UploadFile

from app.core.exceptions import ConflictError, NotFoundError
from app.models.resume import Resume
from app.models.user import User
from app.repository.resume_repository import ResumeRepository
from app.repository.user_repository import UserRepository
from app.schemas.user import UserUpdateRequest
from app.services.storage_service import StorageService

MAX_RESUME_VERSIONS = 5

_RESUME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _resume_content_type(ext: str) -> str:
    suffix = ext if ext.startswith(".") else f".{ext}"
    return _RESUME_TYPES.get(suffix.lower(), "application/octet-stream")


def resume_content_disposition(filename: str, *, inline: bool = False) -> str:
    kind = "inline" if inline else "attachment"
    raw = (filename or "resume").replace("\r", " ").replace("\n", " ").strip() or "resume"
    ascii_name = "".join(ch if 32 <= ord(ch) < 127 and ch not in '\\"' else "_" for ch in raw)
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(raw)}"


class UserService:
    def __init__(
        self,
        users: UserRepository | None = None,
        resumes: ResumeRepository | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self.users = users or UserRepository()
        self.resumes = resumes or ResumeRepository()
        self.storage = storage or StorageService()

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
        existing_count = await self.resumes.count({"user_id": user_id})
        if existing_count >= MAX_RESUME_VERSIONS:
            raise ConflictError(
                f"You can keep up to {MAX_RESUME_VERSIONS} resume versions. "
                "Delete one to upload another.",
                code="RESUME_LIMIT",
            )
        ext = Path(file.filename or "resume.pdf").suffix.lower() or ".pdf"
        filename = f"{uuid4().hex}{ext}"
        content = await file.read()
        stored = await self.storage.save_bytes(
            content,
            folder=f"resumes/{user_id}",
            filename=filename,
            content_type=_resume_content_type(ext),
        )

        if is_default:
            await self.resumes.bulk_update(
                {"user_id": user_id, "is_default": True},
                {"is_default": False},
            )
        resume = await self.resumes.create(
            {
                "user_id": user_id,
                "name": name or file.filename or filename,
                "file_path": stored["path"],
                "file_type": ext.lstrip("."),
                "is_default": is_default or existing_count == 0,
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

    async def download_resume(self, user_id: str, resume_id: str) -> tuple[bytes, str, str]:
        resume = await self.resumes.get_by_id(resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume not found")
        data = await self.storage.read_bytes(resume.file_path)
        filename = resume.name or f"resume.{resume.file_type or 'pdf'}"
        media_type = _resume_content_type(resume.file_type or ".pdf")
        return data, filename, media_type

    async def delete_resume(self, user_id: str, resume_id: str) -> None:
        resume = await self.resumes.get_by_id(resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume not found")
        was_default = bool(resume.is_default)
        await self.storage.delete(resume.file_path)
        await self.resumes.delete(resume)
        if was_default:
            remaining = await self.resumes.list_for_user(user_id)
            if remaining:
                await self.resumes.update(
                    remaining[0],
                    {"is_default": True, "updated_at": datetime.utcnow()},
                )
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "resume.deleted",
            message=f"Deleted resume {resume.name}",
            resource_type="resume",
            resource_id=resume_id,
            severity="warning",
        )

"""Resume upload should not depend on Cosmos ORDER BY indexes."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_upload_resume_sets_default_without_sorted_list():
    created = SimpleNamespace(
        id="r1",
        name="cv.pdf",
        file_type="pdf",
        is_default=True,
        created_at=datetime.utcnow(),
    )
    resumes = SimpleNamespace(
        list_for_user=AsyncMock(side_effect=AssertionError("sorted list must not be used")),
        count=AsyncMock(return_value=1),
        bulk_update=AsyncMock(return_value=1),
        create=AsyncMock(return_value=created),
    )
    storage = SimpleNamespace(
        save_bytes=AsyncMock(
            return_value={
                "path": "blob://resumes/u1/cv.pdf",
                "url": "https://blob/cv.pdf",
                "backend": "azure-blob",
            }
        )
    )
    service = UserService(users=SimpleNamespace(), resumes=resumes, storage=storage)
    upload = MagicMock()
    upload.filename = "cv.pdf"
    upload.read = AsyncMock(return_value=b"%PDF-1.4")

    with patch("app.services.audit_service.audit_event", new_callable=AsyncMock):
        result = await service.upload_resume("u1", upload, is_default=True)

    resumes.bulk_update.assert_awaited_once_with(
        {"user_id": "u1", "is_default": True},
        {"is_default": False},
    )
    resumes.count.assert_awaited_once_with({"user_id": "u1"})
    payload = resumes.create.await_args.args[0]
    assert payload["is_default"] is True
    assert payload["file_type"] == "pdf"
    assert payload["file_path"] == "blob://resumes/u1/cv.pdf"
    assert result is created


@pytest.mark.asyncio
async def test_first_resume_becomes_default():
    created = SimpleNamespace(
        id="r2",
        name="cv.pdf",
        file_type="pdf",
        is_default=True,
        created_at=datetime.utcnow(),
    )
    resumes = SimpleNamespace(
        count=AsyncMock(return_value=0),
        bulk_update=AsyncMock(return_value=0),
        create=AsyncMock(return_value=created),
    )
    storage = SimpleNamespace(
        save_bytes=AsyncMock(
            return_value={
                "path": "blob://resumes/u1/cv.pdf",
                "url": "https://blob/cv.pdf",
                "backend": "azure-blob",
            }
        )
    )
    service = UserService(users=SimpleNamespace(), resumes=resumes, storage=storage)
    upload = MagicMock()
    upload.filename = "cv.pdf"
    upload.read = AsyncMock(return_value=b"%PDF-1.4")

    with patch("app.services.audit_service.audit_event", new_callable=AsyncMock):
        await service.upload_resume("u1", upload, is_default=False)

    resumes.bulk_update.assert_not_awaited()
    payload = resumes.create.await_args.args[0]
    assert payload["is_default"] is True
    storage.save_bytes.assert_awaited_once()

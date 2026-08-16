"""Resume upload should not depend on Cosmos ORDER BY indexes."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.services.user_service import MAX_RESUME_VERSIONS, UserService, resume_content_disposition


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


def _upload(name="cv.pdf"):
    upload = MagicMock()
    upload.filename = name
    upload.read = AsyncMock(return_value=b"%PDF-1.4")
    return upload


@pytest.mark.asyncio
async def test_sixth_resume_deletes_oldest():
    created = SimpleNamespace(
        id="new",
        name="fresh.pdf",
        file_type="pdf",
        is_default=True,
        created_at=datetime.utcnow(),
    )
    oldest = SimpleNamespace(
        id="old",
        name="oldest.pdf",
        file_path="blob://resumes/u1/old.pdf",
    )
    kept = [
        created,
        SimpleNamespace(id="r2"),
        SimpleNamespace(id="r3"),
        SimpleNamespace(id="r4"),
        SimpleNamespace(id="r5"),
        oldest,
    ]
    resumes = SimpleNamespace(
        count=AsyncMock(return_value=MAX_RESUME_VERSIONS),
        bulk_update=AsyncMock(return_value=1),
        create=AsyncMock(return_value=created),
        list_for_user=AsyncMock(return_value=kept),
        delete=AsyncMock(),
    )
    storage = SimpleNamespace(
        save_bytes=AsyncMock(
            return_value={
                "path": "blob://resumes/u1/fresh.pdf",
                "url": "https://blob/fresh.pdf",
                "backend": "azure-blob",
            }
        ),
        delete=AsyncMock(),
    )
    service = UserService(users=SimpleNamespace(), resumes=resumes, storage=storage)

    with patch("app.services.audit_service.audit_event", new_callable=AsyncMock):
        result = await service.upload_resume("u1", _upload("fresh.pdf"), is_default=True)

    assert result is created
    storage.save_bytes.assert_awaited_once()
    resumes.list_for_user.assert_awaited_once()
    storage.delete.assert_awaited_once_with("blob://resumes/u1/old.pdf")
    resumes.delete.assert_awaited_once_with(oldest)


@pytest.mark.asyncio
async def test_download_resume_reads_storage():
    resume = SimpleNamespace(
        id="r1",
        user_id="u1",
        name="Lav Resume.pdf",
        file_type="pdf",
        file_path="blob://resumes/u1/abc.pdf",
    )
    service = UserService(
        users=SimpleNamespace(),
        resumes=SimpleNamespace(get_by_id=AsyncMock(return_value=resume)),
        storage=SimpleNamespace(read_bytes=AsyncMock(return_value=b"%PDF-bytes")),
    )
    data, filename, media = await service.download_resume("u1", "r1")
    assert data == b"%PDF-bytes"
    assert filename == "Lav Resume.pdf"
    assert media == "application/pdf"


@pytest.mark.asyncio
async def test_download_resume_rejects_other_user():
    resume = SimpleNamespace(id="r1", user_id="other")
    service = UserService(
        users=SimpleNamespace(),
        resumes=SimpleNamespace(get_by_id=AsyncMock(return_value=resume)),
        storage=SimpleNamespace(read_bytes=AsyncMock()),
    )
    with pytest.raises(NotFoundError):
        await service.download_resume("u1", "r1")


@pytest.mark.asyncio
async def test_delete_default_promotes_newest_remaining():
    doomed = SimpleNamespace(
        id="r1",
        user_id="u1",
        name="old.pdf",
        is_default=True,
        file_path="blob://resumes/u1/old.pdf",
    )
    newest = SimpleNamespace(id="r2", is_default=False)
    resumes = SimpleNamespace(
        get_by_id=AsyncMock(return_value=doomed),
        delete=AsyncMock(),
        list_for_user=AsyncMock(return_value=[newest]),
        update=AsyncMock(),
    )
    storage = SimpleNamespace(delete=AsyncMock())
    service = UserService(users=SimpleNamespace(), resumes=resumes, storage=storage)

    with patch("app.services.audit_service.audit_event", new_callable=AsyncMock):
        await service.delete_resume("u1", "r1")

    storage.delete.assert_awaited_once_with("blob://resumes/u1/old.pdf")
    resumes.update.assert_awaited_once()
    assert resumes.update.await_args.args[0] is newest
    assert resumes.update.await_args.args[1]["is_default"] is True


def test_content_disposition_encodes_filename():
    header = resume_content_disposition("Lav Resume.pdf", inline=True)
    assert header.startswith("inline;")
    assert "filename=\"Lav Resume.pdf\"" in header
    assert "filename*=UTF-8''Lav%20Resume.pdf" in header

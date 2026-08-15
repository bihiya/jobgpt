"""Azure Blob vs local storage routing."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.storage_service import StorageService
from app.services.user_service import UserService


@pytest.fixture
def blob_settings(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "azure_storage_account", "stjobpilottest")
    monkeypatch.setattr(settings, "azure_storage_container", "uploads")
    monkeypatch.setattr(settings, "azure_storage_connection_string", "")
    monkeypatch.setattr(settings, "s3_enabled", False)
    monkeypatch.setattr(settings, "s3_bucket", "")
    return settings


@pytest.mark.asyncio
async def test_save_bytes_uses_azure_blob(blob_settings):
    service = StorageService()
    assert service.use_blob is True
    with patch.object(service, "_put_blob", new_callable=AsyncMock) as put:
        stored = await service.save_bytes(
            b"%PDF",
            folder="resumes/u1",
            filename="cv.pdf",
            content_type="application/pdf",
        )
    put.assert_awaited_once()
    assert stored["backend"] == "azure-blob"
    assert stored["path"] == "blob://resumes/u1/cv.pdf"
    assert stored["key"] == "resumes/u1/cv.pdf"
    assert "stjobpilottest.blob.core.windows.net" in stored["url"]


@pytest.mark.asyncio
async def test_as_local_file_downloads_blob(blob_settings, tmp_path):
    service = StorageService()
    with patch.object(service, "_get_blob", new_callable=AsyncMock, return_value=b"pdf-bytes"):
        local = await service.as_local_file("blob://resumes/u1/cv.pdf")
    data = Path(local).read_bytes()
    assert data == b"pdf-bytes"
    await service.cleanup_temp(local, original="blob://resumes/u1/cv.pdf")
    assert not Path(local).exists()


@pytest.mark.asyncio
async def test_local_fallback_when_blob_not_configured(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "azure_storage_account", "")
    monkeypatch.setattr(settings, "s3_enabled", False)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    service = StorageService()
    stored = await service.save_bytes(b"hello", folder="resumes/u1", filename="cv.pdf")
    assert stored["backend"] == "local"
    assert Path(stored["path"]).read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_upload_resume_stores_blob_path(blob_settings):
    created = SimpleNamespace(
        id="r1",
        name="cv.pdf",
        file_type="pdf",
        is_default=True,
        created_at=None,
    )
    resumes = SimpleNamespace(
        count=AsyncMock(return_value=0),
        bulk_update=AsyncMock(return_value=0),
        create=AsyncMock(return_value=created),
    )
    storage = SimpleNamespace(
        save_bytes=AsyncMock(
            return_value={
                "path": "blob://resumes/u1/abc.pdf",
                "url": "https://x/abc.pdf",
                "backend": "azure-blob",
            }
        ),
        delete=AsyncMock(),
    )
    service = UserService(users=SimpleNamespace(), resumes=resumes, storage=storage)
    upload = MagicMock()
    upload.filename = "cv.pdf"
    upload.read = AsyncMock(return_value=b"%PDF-1.4")

    with patch("app.services.audit_service.audit_event", new_callable=AsyncMock):
        await service.upload_resume("u1", upload, is_default=True)

    storage.save_bytes.assert_awaited_once()
    payload = resumes.create.await_args.args[0]
    assert payload["file_path"] == "blob://resumes/u1/abc.pdf"

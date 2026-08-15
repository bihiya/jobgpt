"""Object storage: Azure Blob (managed identity), S3-compatible, or local disk."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import aiofiles

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_BLOB_PREFIX = "blob://"


def _safe_key(folder: str, filename: str) -> str:
    folder = folder.strip("/").replace("..", "")
    name = Path(filename).name or uuid4().hex
    return f"{folder}/{name}"


class StorageService:
    def __init__(self) -> None:
        self.account = (settings.azure_storage_account or "").strip()
        self.container = (settings.azure_storage_container or "uploads").strip() or "uploads"
        self.use_blob = bool(self.account)
        self.use_s3 = (not self.use_blob) and bool(settings.s3_bucket and settings.s3_enabled)

    def blob_url(self, key: str) -> str:
        return f"https://{self.account}.blob.core.windows.net/{self.container}/{key}"

    def stored_path(self, key: str) -> str:
        if self.use_blob:
            return f"{_BLOB_PREFIX}{key}"
        if self.use_s3:
            return f"s3://{settings.s3_bucket}/{key}"
        return key

    def key_from_path(self, stored: str) -> str:
        value = stored or ""
        if value.startswith(_BLOB_PREFIX):
            return value.removeprefix(_BLOB_PREFIX)
        if value.startswith("s3://"):
            rest = value.split("/", 3)
            return rest[3] if len(rest) > 3 else value
        if self.use_blob and not os.path.isabs(value):
            return value.lstrip("/")
        return value

    def is_remote(self, stored: str) -> bool:
        value = stored or ""
        if value.startswith(_BLOB_PREFIX) or value.startswith("s3://"):
            return True
        if self.use_blob and value and not os.path.isabs(value):
            return True
        return False

    async def save_bytes(
        self,
        data: bytes,
        *,
        folder: str,
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> dict[str, str]:
        name = filename or uuid4().hex
        key = _safe_key(folder, name)
        if self.use_blob:
            await self._put_blob(key, data, content_type)
            return {
                "path": self.stored_path(key),
                "url": self.blob_url(key),
                "backend": "azure-blob",
                "key": key,
            }
        if self.use_s3:
            url = await self._put_s3(key, data, content_type)
            return {"path": self.stored_path(key), "url": url, "backend": "s3", "key": key}
        path = Path(settings.upload_dir) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as fh:
            await fh.write(data)
        return {"path": str(path), "url": f"/files/{key}", "backend": "local", "key": key}

    async def save_file(
        self,
        local_path: str,
        *,
        folder: str,
        content_type: str = "",
    ) -> dict[str, str]:
        data = Path(local_path).read_bytes()
        return await self.save_bytes(
            data,
            folder=folder,
            filename=Path(local_path).name,
            content_type=content_type or "application/octet-stream",
        )

    async def read_bytes(self, stored: str) -> bytes:
        if self.is_remote(stored) and self.use_blob:
            return await self._get_blob(self.key_from_path(stored))
        if self.use_s3 and stored.startswith("s3://"):
            raise FileNotFoundError("S3 download is not configured for this path")
        path = Path(stored)
        if not path.exists():
            raise FileNotFoundError(stored)
        return path.read_bytes()

    async def as_local_file(self, stored: str) -> str:
        """Return a filesystem path Playwright can upload. Downloads blob objects to a temp file."""
        if not self.is_remote(stored):
            return stored
        data = await self.read_bytes(stored)
        suffix = Path(self.key_from_path(stored)).suffix or ""
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="jobpilot-")
        handle.write(data)
        handle.close()
        return handle.name

    async def cleanup_temp(self, local_path: str | None, *, original: str) -> None:
        if not local_path or local_path == original:
            return
        if not self.is_remote(original):
            return
        try:
            os.remove(local_path)
        except OSError:
            logger.warning("temp_cleanup_failed", path=local_path)

    async def delete(self, stored: str) -> None:
        if not stored:
            return
        if self.is_remote(stored) and self.use_blob:
            await self._delete_blob(self.key_from_path(stored))
            return
        if os.path.exists(stored):
            os.remove(stored)

    async def _blob_client(self):
        from azure.storage.blob.aio import BlobServiceClient

        conn = (settings.azure_storage_connection_string or "").strip()
        if conn:
            return BlobServiceClient.from_connection_string(conn)
        from azure.identity.aio import DefaultAzureCredential

        credential = DefaultAzureCredential()
        return BlobServiceClient(
            account_url=f"https://{self.account}.blob.core.windows.net",
            credential=credential,
        )

    async def _put_blob(self, key: str, data: bytes, content_type: str) -> None:
        client = await self._blob_client()
        try:
            blob = client.get_blob_client(container=self.container, blob=key)
            await blob.upload_blob(data, overwrite=True, content_type=content_type)
        except Exception:
            logger.exception("azure_blob_upload_failed", key=key, container=self.container)
            raise
        finally:
            await client.close()
        logger.info("azure_blob_uploaded", key=key, bytes=len(data), container=self.container)

    async def _get_blob(self, key: str) -> bytes:
        client = await self._blob_client()
        try:
            blob = client.get_blob_client(container=self.container, blob=key)
            stream = await blob.download_blob()
            return await stream.readall()
        finally:
            await client.close()

    async def _delete_blob(self, key: str) -> None:
        client = await self._blob_client()
        try:
            blob = client.get_blob_client(container=self.container, blob=key)
            await blob.delete_blob()
        except Exception as exc:  # noqa: BLE001
            logger.warning("azure_blob_delete_failed", key=key, error=str(exc))
        finally:
            await client.close()

    async def _put_s3(self, key: str, data: bytes, content_type: str) -> str:
        try:
            import aioboto3

            session = aioboto3.Session()
            async with session.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            ) as s3:
                await s3.put_object(
                    Bucket=settings.s3_bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
            if settings.s3_public_base_url:
                return f"{settings.s3_public_base_url.rstrip('/')}/{key}"
            return f"s3://{settings.s3_bucket}/{key}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("s3_upload_failed_fallback_local", error=str(exc))
            path = Path(settings.upload_dir) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return str(path)

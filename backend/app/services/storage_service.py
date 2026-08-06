"""Object storage (S3-compatible) with local filesystem fallback."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.use_s3 = bool(settings.s3_bucket and settings.s3_enabled)

    async def save_bytes(
        self,
        data: bytes,
        *,
        folder: str,
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> dict[str, str]:
        name = filename or f"{uuid4().hex}"
        key = f"{folder}/{name}"
        if self.use_s3:
            url = await self._put_s3(key, data, content_type)
            return {"path": key, "url": url, "backend": "s3"}
        path = Path(settings.upload_dir) / folder
        path.mkdir(parents=True, exist_ok=True)
        full = path / name
        async with aiofiles.open(full, "wb") as fh:
            await fh.write(data)
        return {"path": str(full), "url": f"/files/{folder}/{name}", "backend": "local"}

    async def save_file(self, local_path: str, *, folder: str, content_type: str = "") -> dict[str, str]:
        data = Path(local_path).read_bytes()
        return await self.save_bytes(
            data,
            folder=folder,
            filename=Path(local_path).name,
            content_type=content_type or "application/octet-stream",
        )

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

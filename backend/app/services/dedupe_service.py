"""Duplicate / already-applied detection using hash + Redis Bloom approx."""

from __future__ import annotations

import hashlib

from app.core.redis_features import bloom_add, bloom_might_contain
from app.core.redis import ns
from app.models.enums import JobStatus
from app.models.job import Job
from app.repository.application_repository import ApplicationRepository
from app.repository.job_repository import JobRepository


class DedupeService:
    def __init__(
        self,
        jobs: JobRepository | None = None,
        applications: ApplicationRepository | None = None,
    ) -> None:
        self.jobs = jobs or JobRepository()
        self.applications = applications or ApplicationRepository()

    @staticmethod
    def content_hash(title: str, company: str, apply_url: str = "", external_id: str = "") -> str:
        raw = "|".join(
            [
                (apply_url or "").strip().lower(),
                (external_id or "").strip().lower(),
                (title or "").strip().lower(),
                (company or "").strip().lower(),
            ]
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    async def is_duplicate(self, user_id: str, fingerprint: str, apply_url: str = "") -> bool:
        bloom_key = f"jobs:{user_id}"
        try:
            if await bloom_might_contain(bloom_key, fingerprint):
                existing = await self.jobs.find_one(
                    {"user_id": user_id, "content_hash": fingerprint}
                )
                if existing:
                    return True
        except Exception:  # noqa: BLE001
            pass

        if apply_url:
            by_url = await self.jobs.find_one({"user_id": user_id, "apply_url": apply_url})
            if by_url:
                return True

        # Already applied check via applications joining job hashes is approximate:
        applied_jobs = await Job.find(
            {"user_id": user_id, "status": {"$in": [JobStatus.APPLIED, JobStatus.APPLYING]}}
        ).to_list()
        for job in applied_jobs:
            if job.content_hash == fingerprint or (apply_url and job.apply_url == apply_url):
                return True
        return False

    async def remember(self, user_id: str, fingerprint: str) -> None:
        try:
            await bloom_add(f"jobs:{user_id}", fingerprint)
        except Exception:  # noqa: BLE001
            pass
        _ = ns  # namespace helper retained for future key variants

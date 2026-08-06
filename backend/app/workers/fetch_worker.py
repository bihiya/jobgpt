"""Fetch jobs worker with dedupe + portal health."""

from datetime import datetime
from typing import Any

from app.automation.portals.registry import get_portal_adapter
from app.core.kafka import publish
from app.core.logging import get_logger
from app.events.realtime import emit_realtime
from app.services.audit_service import audit_event
from app.models.enums import JobStatus, PortalStatus
from app.models.job import Job
from app.repository.portal_repository import PortalRepository
from app.repository.user_repository import UserRepository
from app.services.dedupe_service import DedupeService
from app.services.portal_health_service import PortalHealthService
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class FetchWorker(BaseWorker):
    topics = ["job.fetch"]
    group_id = "jobpilot-fetch"

    def __init__(self) -> None:
        super().__init__()
        self.portals = PortalRepository()
        self.users = UserRepository()
        self.dedupe = DedupeService()
        self.health = PortalHealthService()

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        if not user_id:
            users = await self.users.find_many(limit=100)
            for user in users:
                await publish("job.fetch", {"user_id": str(user.id), "source": "fanout"}, key=str(user.id))
            return

        user = await self.users.get_by_id(user_id)
        if not user:
            return

        portals = await self.portals.list_for_user(user_id)
        portal_filter = payload.get("portal")
        query = " ".join(user.profile.keywords[:5]) or "software engineer"
        location = user.profile.location

        for portal in portals:
            if portal_filter and portal.name.value != portal_filter:
                continue
            if portal.status == PortalStatus.DISCONNECTED:
                continue
            if not self.health.is_usable(portal):
                logger.info("portal_skipped_unhealthy", portal=portal.name.value, score=portal.health.score)
                continue

            adapter = get_portal_adapter(
                portal.name,
                credentials=portal.credentials.model_dump(),
                proxy=portal.proxy.model_dump() if portal.proxy.server else None,
            )
            try:
                extracted = await adapter.fetch_jobs(query, location)
                inserted = 0
                for item in extracted:
                    fingerprint = self.dedupe.content_hash(
                        item.title, item.company, item.apply_url, item.external_id
                    )
                    if await self.dedupe.is_duplicate(user_id, fingerprint, item.apply_url):
                        continue
                    existing = await Job.find_one(
                        {
                            "user_id": user_id,
                            "external_id": item.external_id,
                            "portal": portal.name.value,
                        }
                    )
                    if existing:
                        continue
                    job = Job(
                        user_id=user_id,
                        external_id=item.external_id,
                        title=item.title,
                        company=item.company,
                        location=item.location,
                        salary=item.salary,
                        experience=item.experience,
                        description=item.description,
                        skills=item.skills,
                        apply_url=item.apply_url,
                        portal=portal.name.value,
                        content_hash=fingerprint,
                        source="portal",
                        status=JobStatus.NEW,
                        fetched_at=datetime.utcnow(),
                    )
                    await job.insert()
                    await self.dedupe.remember(user_id, fingerprint)
                    inserted += 1
                    await publish(
                        "job.match",
                        {"user_id": user_id, "job_id": str(job.id)},
                        key=user_id,
                    )
                    await emit_realtime(
                        user_id,
                        "job.created",
                        {
                            "job_id": str(job.id),
                            "title": job.title,
                            "company": job.company,
                            "portal": portal.name.value,
                        },
                    )
                    await audit_event(
                        user_id,
                        "job.created",
                        message=f"Fetched {job.title} at {job.company}",
                        job_id=str(job.id),
                        resource_type="job",
                        resource_id=str(job.id),
                        source="worker",
                        metadata={"portal": portal.name.value},
                    )
                portal.last_sync_at = datetime.utcnow()
                portal.status = PortalStatus.CONNECTED
                await self.health.record_success(portal)
                await emit_realtime(
                    user_id,
                    "portal.synced",
                    {
                        "portal": portal.name.value,
                        "inserted": inserted,
                        "fetched": len(extracted),
                    },
                    title=f"{portal.name.value} sync complete",
                    body=f"Added {inserted} new jobs",
                    severity="success" if inserted else "info",
                )
                logger.info(
                    "fetch_complete",
                    user_id=user_id,
                    portal=portal.name.value,
                    count=len(extracted),
                    inserted=inserted,
                )
            except Exception as exc:  # noqa: BLE001
                await self.health.record_failure(portal, str(exc))
                await emit_realtime(
                    user_id,
                    "portal.health",
                    {"portal": portal.name.value, "error": str(exc)},
                    title="Portal sync failed",
                    body=str(exc),
                    severity="error",
                )
                logger.exception("fetch_failed", portal=portal.name.value, error=str(exc))
                raise


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(FetchWorker().start)

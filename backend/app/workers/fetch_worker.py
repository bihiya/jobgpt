"""Fetch jobs worker."""

from datetime import datetime
from typing import Any

from app.automation.portals.registry import get_portal_adapter
from app.core.kafka import publish
from app.core.logging import get_logger
from app.models.enums import PortalStatus
from app.models.job import Job
from app.repository.portal_repository import PortalRepository
from app.repository.user_repository import UserRepository
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class FetchWorker(BaseWorker):
    topics = ["job.fetch"]
    group_id = "jobpilot-fetch"

    def __init__(self) -> None:
        super().__init__()
        self.portals = PortalRepository()
        self.users = UserRepository()

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        if not user_id:
            # System tick: fan-out to active users with connected portals
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
            adapter = get_portal_adapter(
                portal.name,
                credentials=portal.credentials.model_dump(),
                proxy=portal.proxy.model_dump() if portal.proxy.server else None,
            )
            try:
                extracted = await adapter.fetch_jobs(query, location)
                for item in extracted:
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
                        fetched_at=datetime.utcnow(),
                    )
                    await job.insert()
                    await publish(
                        "job.match",
                        {"user_id": user_id, "job_id": str(job.id)},
                        key=user_id,
                    )
                portal.last_sync_at = datetime.utcnow()
                portal.status = PortalStatus.CONNECTED
                await portal.save()
                logger.info("fetch_complete", user_id=user_id, portal=portal.name.value, count=len(extracted))
            except Exception as exc:  # noqa: BLE001
                portal.status = PortalStatus.ERROR
                await portal.save()
                logger.exception("fetch_failed", portal=portal.name.value, error=str(exc))


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(FetchWorker().start)

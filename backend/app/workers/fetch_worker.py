"""Fetch jobs worker with dedupe + portal health."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.automation.errors import PortalAuthError
from app.automation.portals.registry import get_portal_adapter
from app.core.kafka import publish
from app.core.logging import get_logger
from app.events.realtime import emit_realtime
from app.models.enums import JobStatus, PortalStatus
from app.models.job import Job
from app.repository.portal_repository import PortalRepository
from app.repository.user_repository import UserRepository
from app.services.audit_service import audit_event
from app.services.automation_log_service import write_automation_log
from app.services.dedupe_service import DedupeService
from app.services.portal_health_service import PortalHealthService
from app.services.session_vault import SessionVault, has_auth_cookies
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

    async def _clear_sync_started(
        self,
        *,
        user_id: str | None = None,
        portal_id: str | None = None,
        portal_name: str | None = None,
    ) -> None:
        """Clear stuck sync_started_at markers for early exits / crashes."""
        try:
            if portal_id:
                portal = await self.portals.get_by_id(portal_id)
                if portal and getattr(portal, "sync_started_at", None):
                    portal.sync_started_at = None
                    portal.updated_at = datetime.utcnow()
                    await portal.save()
                return
            if not user_id:
                return
            portals = await self.portals.list_for_user(user_id)
            for portal in portals:
                if portal_name and portal.name.value != portal_name:
                    continue
                if getattr(portal, "sync_started_at", None):
                    portal.sync_started_at = None
                    portal.updated_at = datetime.utcnow()
                    await portal.save()
        except Exception as exc:  # noqa: BLE001
            logger.warning("clear_sync_started_failed", error=str(exc))

    async def _log_recorder_steps(
        self,
        user_id: str,
        portal_name: str,
        adapter: Any,
        correlation_id: str,
    ) -> None:
        steps = []
        try:
            steps = adapter.recorder.to_list() if getattr(adapter, "recorder", None) else []
        except Exception:  # noqa: BLE001
            steps = []
        for step in steps:
            if step.get("key") != "login" and step.get("status") not in {"warn", "error", "failed"}:
                continue
            level = "warning" if step.get("status") in {"warn", "warning"} else (
                "error" if step.get("status") in {"error", "failed"} else "info"
            )
            await write_automation_log(
                user_id,
                action="fetch.login",
                level=level,
                portal=portal_name,
                message=str(
                    step.get("label")
                    or step.get("detail")
                    or step.get("message")
                    or step.get("key")
                    or "login step"
                ),
                metadata={"step": step},
                correlation_id=correlation_id,
            )

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        portal_filter = payload.get("portal")
        portal_id = payload.get("portal_id")
        if not user_id:
            users = await self.users.find_many(limit=100)
            for user in users:
                await publish("job.fetch", {"user_id": str(user.id), "source": "fanout"}, key=str(user.id))
            return

        try:
            await self._handle_user(
                user_id=str(user_id),
                portal_filter=portal_filter,
                portal_id=str(portal_id) if portal_id else None,
                payload=payload,
            )
        finally:
            # Safety net: never leave sync_started_at stuck on early returns / crashes.
            await self._clear_sync_started(
                user_id=str(user_id),
                portal_id=str(portal_id) if portal_id else None,
                portal_name=str(portal_filter) if portal_filter else None,
            )

    async def _handle_user(
        self,
        *,
        user_id: str,
        portal_filter: str | None,
        portal_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        user = await self.users.get_by_id(user_id)
        if not user:
            await write_automation_log(
                user_id,
                action="fetch",
                level="error",
                message="Fetch aborted — user not found",
            )
            return

        correlation_id = payload.get("correlation_id") or uuid4().hex
        portals = await self.portals.list_for_user(user_id)
        query = " ".join(user.profile.keywords[:5]) or "software engineer"
        location = user.profile.location or "Remote"

        await write_automation_log(
            user_id,
            action="fetch.start",
            level="info",
            message=f"Fetch started — query “{query}” ({len(portals)} portal(s))",
            metadata={"query": query, "location": location, "portals": len(portals)},
            correlation_id=correlation_id,
        )

        if not portals:
            await write_automation_log(
                user_id,
                action="fetch.skipped",
                level="warning",
                message="No job portals connected. Connect a portal under Job Portals, then run fetch again.",
                correlation_id=correlation_id,
            )
            return

        ran = 0
        total_inserted = 0
        auth_failures = 0
        for portal in portals:
            if portal_id and str(portal.id) != portal_id:
                continue
            if portal_filter and portal.name.value != portal_filter:
                continue
            if portal.status == PortalStatus.DISCONNECTED:
                if getattr(portal, "sync_started_at", None):
                    portal.sync_started_at = None
                    await portal.save()
                await write_automation_log(
                    user_id,
                    action="fetch.skipped",
                    level="warning",
                    portal=portal.name.value,
                    message=f"{portal.name.value} skipped — disconnected",
                    correlation_id=correlation_id,
                )
                continue
            if not self.health.is_usable(portal):
                logger.info("portal_skipped_unhealthy", portal=portal.name.value, score=portal.health.score)
                if getattr(portal, "sync_started_at", None):
                    portal.sync_started_at = None
                    await portal.save()
                await write_automation_log(
                    user_id,
                    action="fetch.skipped",
                    level="warning",
                    portal=portal.name.value,
                    message=f"{portal.name.value} skipped — unhealthy (score {portal.health.score})",
                    metadata={"score": portal.health.score, "error": portal.health.last_error},
                    correlation_id=correlation_id,
                )
                await emit_realtime(
                    user_id,
                    "portal.health",
                    {
                        "portal": portal.name.value,
                        "portal_id": str(portal.id),
                        "error": portal.health.last_error or "Portal paused / unhealthy",
                    },
                    title=f"{portal.name.value} sync skipped",
                    body=portal.health.paused_reason or portal.health.last_error or "Re-auth required",
                    severity="warning",
                )
                continue

            vault = SessionVault()
            adapter = get_portal_adapter(
                portal.name,
                credentials=portal.credentials.model_dump(),
                cookies=vault.load_cookies(portal),
                proxy=portal.proxy.model_dump() if portal.proxy.server else None,
                totp_secret=vault.load_totp_secret(portal),
                selector_version=getattr(portal, "selector_version", 1) or 1,
            )
            ran += 1
            credentials_expected = bool(portal.credentials.username)
            await write_automation_log(
                user_id,
                action="fetch.portal",
                level="info",
                portal=portal.name.value,
                message=f"Fetching jobs from {portal.name.value}…",
                correlation_id=correlation_id,
            )
            try:
                extracted = await adapter.fetch_jobs(query, location)
                await self._log_recorder_steps(user_id, portal.name.value, adapter, correlation_id)

                # Persist cookies only when they prove an authenticated session
                # (or when the portal has no auth-cookie requirement).
                last_cookies = list(adapter.browser.last_cookies or [])
                if last_cookies and (
                    not credentials_expected or has_auth_cookies(portal.name.value, last_cookies)
                ):
                    vault.save_cookies(portal, last_cookies)
                    portal.updated_at = datetime.utcnow()
                    await portal.save()
                elif credentials_expected and last_cookies and not has_auth_cookies(
                    portal.name.value, last_cookies
                ):
                    # Anonymous tracking cookies must not flip has_session.
                    logger.info(
                        "skip_anonymous_cookie_save",
                        portal=portal.name.value,
                        cookie_count=len(last_cookies),
                    )

                # Credentials were provided but scrape stayed guest → treat as auth failure.
                if credentials_expected and not has_auth_cookies(portal.name.value, last_cookies):
                    raise PortalAuthError(
                        "Fetch finished without an authenticated session — login likely failed",
                        code="NOT_LOGGED_IN",
                    )

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
                    total_inserted += 1
                    try:
                        await publish(
                            "job.match",
                            {"user_id": user_id, "job_id": str(job.id)},
                            key=user_id,
                        )
                    except Exception as pub_exc:  # noqa: BLE001
                        # Kafka may be down in local/dev — match can be triggered manually.
                        logger.warning("match_publish_skipped", error=str(pub_exc))
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
                portal.sync_started_at = None
                portal.status = PortalStatus.CONNECTED
                await self.health.record_success(portal)
                complete_level = "success" if inserted else ("warning" if credentials_expected else "info")
                await write_automation_log(
                    user_id,
                    action="fetch.complete",
                    level=complete_level,
                    portal=portal.name.value,
                    message=f"{portal.name.value}: found {len(extracted)}, added {inserted} new job(s)",
                    metadata={"fetched": len(extracted), "inserted": inserted},
                    correlation_id=correlation_id,
                )
                await emit_realtime(
                    user_id,
                    "portal.synced",
                    {
                        "portal": portal.name.value,
                        "portal_id": str(portal.id),
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
                await self._log_recorder_steps(user_id, portal.name.value, adapter, correlation_id)
                portal.sync_started_at = None
                await self.health.record_failure(portal, str(exc))
                if isinstance(exc, PortalAuthError):
                    auth_failures += 1
                    portal.status = PortalStatus.ERROR
                    await portal.save()
                await write_automation_log(
                    user_id,
                    action="fetch.failed",
                    level="error",
                    portal=portal.name.value,
                    message=f"{portal.name.value} sync failed: {exc}",
                    metadata={
                        "error": str(exc),
                        "code": getattr(exc, "code", None),
                    },
                    correlation_id=correlation_id,
                )
                await emit_realtime(
                    user_id,
                    "portal.health",
                    {
                        "portal": portal.name.value,
                        "portal_id": str(portal.id),
                        "error": str(exc),
                        "code": getattr(exc, "code", None),
                    },
                    title="Portal sync failed",
                    body=str(exc),
                    severity="error",
                )
                logger.exception("fetch_failed", portal=portal.name.value, error=str(exc))

        done_level = "success" if total_inserted else ("error" if auth_failures else "info")
        await write_automation_log(
            user_id,
            action="fetch.done",
            level=done_level,
            message=(
                f"Fetch finished — ran {ran} portal(s), added {total_inserted} new job(s)"
                if ran
                else "Fetch finished — no usable portals to run"
            ),
            metadata={
                "portals_ran": ran,
                "inserted": total_inserted,
                "auth_failures": auth_failures,
            },
            correlation_id=correlation_id,
        )


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(FetchWorker().start)

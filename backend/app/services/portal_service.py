"""Job portal connector service."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.core.exceptions import ConflictError, NotFoundError
from app.core.times import iso_utc
from app.models.enums import PortalStatus
from app.models.portal import Portal, PortalCredentials
from app.producers.events import publish_job_fetch
from app.repository.portal_repository import PortalRepository
from app.schemas.portal import PortalCreate, PortalResponse, PortalUpdate


class PortalService:
    def __init__(self, portals: PortalRepository | None = None) -> None:
        self.portals = portals or PortalRepository()

    @staticmethod
    def _has_auth_session(portal: Portal) -> bool:
        """True only when vault holds portal auth cookies (not anonymous tracking)."""
        from app.services.session_vault import portal_has_auth_session

        return portal_has_auth_session(portal)

    def _to_response(self, portal: Portal) -> PortalResponse:
        from app.schemas.portal import PortalHealthSchema

        health = portal.health.model_dump() if getattr(portal, "health", None) else {}
        return PortalResponse(
            id=str(portal.id),
            name=portal.name,
            status=portal.status,
            last_sync_at=iso_utc(portal.last_sync_at),
            last_attempt_at=iso_utc(getattr(portal, "updated_at", None)),
            sync_started_at=iso_utc(getattr(portal, "sync_started_at", None)),
            created_at=iso_utc(portal.created_at) or "",
            username=(getattr(portal.credentials, "username", "") or "").strip(),
            has_credentials=bool(getattr(portal.credentials, "username", "")),
            has_password=bool(getattr(portal.credentials, "password", "")),
            has_session=self._has_auth_session(portal),
            has_totp=bool(getattr(portal, "totp_secret_encrypted", "")),
            session_updated_at=iso_utc(getattr(portal, "session_updated_at", None)),
            selector_version=int(getattr(portal, "selector_version", 1) or 1),
            health=PortalHealthSchema(**health),
        )

    async def list(self, user_id: str) -> list[PortalResponse]:
        items = await self.portals.list_for_user(user_id)
        return [self._to_response(p) for p in items]

    async def create(self, user_id: str, payload: PortalCreate) -> PortalResponse:
        existing = await self.portals.get_by_name(user_id, payload.name)
        if existing:
            raise ConflictError("Portal already connected")
        from app.services.session_vault import SessionVault, parse_cookie_paste

        vault = SessionVault()
        portal = await self.portals.create(
            {
                "user_id": user_id,
                "name": payload.name,
                "credentials": payload.credentials.model_dump(),
                "proxy": payload.proxy.model_dump(),
                "cookies": {},
                "selector_version": payload.selector_version or 1,
                # Stay CONNECTED so sync/fetch can run; UI uses has_session for "Logged in".
                "status": PortalStatus.CONNECTED,
            }
        )
        name = getattr(payload.name, "value", payload.name)
        cookies = parse_cookie_paste(payload.cookies, portal=str(name))
        if cookies:
            # Only persist cookies that prove auth for portals that require it.
            from app.services.session_vault import has_auth_cookies

            if has_auth_cookies(str(name), cookies) or not portal.credentials.username:
                vault.save_cookies(portal, cookies)
        if payload.totp_secret:
            vault.save_totp_secret(portal, payload.totp_secret)
        await portal.save()
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "portal.connected",
            message=f"Connected portal {payload.name}",
            resource_type="portal",
            resource_id=str(portal.id),
            severity="success",
            metadata={"portal": getattr(payload.name, "value", payload.name)},
        )
        return self._to_response(portal)

    @staticmethod
    def _merge_credentials(
        current: PortalCredentials | None,
        incoming: dict | None,
        *,
        clear: bool = False,
    ) -> PortalCredentials:
        """Replace username; keep existing password when the new one is blank."""
        if clear:
            return PortalCredentials()
        current = current or PortalCredentials()
        incoming = incoming or {}
        username = str(incoming.get("username") or "").strip()
        password = str(incoming.get("password") or "")
        return PortalCredentials(
            username=username or current.username,
            password=password or current.password,
        )

    async def update(self, user_id: str, portal_id: str, payload: PortalUpdate) -> PortalResponse:
        portal = await self._owned(user_id, portal_id)
        from app.services.session_vault import SessionVault, parse_cookie_paste

        vault = SessionVault()
        data = payload.model_dump(exclude_unset=True)
        totp = data.pop("totp_secret", None)
        cookies_raw = data.pop("cookies", None)
        creds = data.pop("credentials", None)
        clear = bool(data.pop("clear_credentials", False))
        data["updated_at"] = datetime.utcnow()

        creds_changed = False
        if clear or creds is not None:
            before_user = getattr(portal.credentials, "username", "") or ""
            before_pass = getattr(portal.credentials, "password", "") or ""
            merged = self._merge_credentials(portal.credentials, creds, clear=clear)
            data["credentials"] = merged.model_dump()
            creds_changed = clear or merged.username != before_user or (
                bool((creds or {}).get("password")) and merged.password != before_pass
            )

        portal = await self.portals.update(portal, data)
        if creds_changed:
            # Stale cookies would skip a fresh login with the new email/password.
            vault.clear_session(portal)
        if cookies_raw is not None:
            portal_name = getattr(portal.name, "value", portal.name)
            vault.save_cookies(portal, parse_cookie_paste(cookies_raw, portal=str(portal_name)))
        if totp is not None:
            vault.save_totp_secret(portal, totp)
        await portal.save()
        return self._to_response(portal)

    async def clear_credentials(self, user_id: str, portal_id: str) -> PortalResponse:
        return await self.update(
            user_id,
            portal_id,
            PortalUpdate(clear_credentials=True),
        )

    async def sync(self, user_id: str, portal_id: str) -> PortalResponse:
        portal = await self._owned(user_id, portal_id)
        correlation_id = uuid4().hex
        # Mark in-progress only — last_sync_at is written by FetchWorker on success.
        portal.sync_started_at = datetime.utcnow()
        portal.updated_at = datetime.utcnow()
        await portal.save()
        from app.services.automation_log_service import write_automation_log

        await write_automation_log(
            user_id,
            action="fetch.portal",
            level="info",
            portal=portal.name.value,
            message=f"Sync queued for {portal.name.value}…",
            correlation_id=correlation_id,
            metadata={"portal_id": str(portal.id), "source": "portal.sync"},
        )
        try:
            mode = await publish_job_fetch(
                user_id,
                portal=portal.name.value,
                portal_id=str(portal.id),
                source="portal.sync",
                correlation_id=correlation_id,
            )
        except Exception:
            # Clear in-progress marker when the queue/fallback cannot start.
            portal.sync_started_at = None
            portal.updated_at = datetime.utcnow()
            await portal.save()
            raise
        from app.events.realtime import emit_realtime
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "portal.sync_requested",
            message=f"Sync requested for {portal.name.value} ({mode})",
            resource_type="portal",
            resource_id=str(portal.id),
            severity="success",
            metadata={
                "portal": portal.name.value,
                "mode": mode,
                "correlation_id": correlation_id,
            },
        )
        await emit_realtime(
            user_id,
            "portal.sync_started",
            {
                "portal": portal.name.value,
                "portal_id": str(portal.id),
                "mode": mode,
                "correlation_id": correlation_id,
            },
            title=f"{portal.name.value} sync started",
            body="Fetching jobs in the background…",
            severity="info",
        )
        return self._to_response(portal).model_copy(update={"correlation_id": correlation_id})

    async def reauth(self, user_id: str, portal_id: str, payload: PortalUpdate) -> PortalResponse:
        """One-click re-auth: refresh credentials/cookies/TOTP, clear auto-pause, sync."""
        portal = await self._owned(user_id, portal_id)
        updated = await self.update(user_id, portal_id, payload)
        portal = await self._owned(user_id, portal_id)
        if getattr(portal, "health", None):
            portal.health.auto_paused = False
            portal.health.paused_reason = ""
            portal.health.consecutive_failures = 0
            portal.health.score = max(portal.health.score, 60.0)
            portal.health.last_error = ""
        portal.status = PortalStatus.CONNECTED
        portal.updated_at = datetime.utcnow()
        await portal.save()
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "portal.reauth",
            message=f"Re-authenticated {portal.name.value}",
            resource_type="portal",
            resource_id=str(portal.id),
            severity="success",
            metadata={"portal": portal.name.value},
        )
        _ = updated
        return await self.sync(user_id, portal_id)

    async def delete(self, user_id: str, portal_id: str) -> None:
        portal = await self._owned(user_id, portal_id)
        await self.portals.delete(portal)

    async def _owned(self, user_id: str, portal_id: str) -> Portal:
        portal = await self.portals.get_by_id(portal_id)
        if not portal or portal.user_id != user_id:
            raise NotFoundError("Portal not found")
        return portal

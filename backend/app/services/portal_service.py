"""Job portal connector service."""

from __future__ import annotations

from datetime import datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import PortalStatus
from app.models.portal import Portal
from app.producers.events import publish_job_fetch
from app.repository.portal_repository import PortalRepository
from app.schemas.portal import PortalCreate, PortalResponse, PortalUpdate


class PortalService:
    def __init__(self, portals: PortalRepository | None = None) -> None:
        self.portals = portals or PortalRepository()

    def _to_response(self, portal: Portal) -> PortalResponse:
        from app.schemas.portal import PortalHealthSchema

        health = portal.health.model_dump() if getattr(portal, "health", None) else {}
        return PortalResponse(
            id=str(portal.id),
            name=portal.name,
            status=portal.status,
            last_sync_at=portal.last_sync_at.isoformat() if portal.last_sync_at else None,
            sync_started_at=(
                portal.sync_started_at.isoformat()
                if getattr(portal, "sync_started_at", None)
                else None
            ),
            created_at=portal.created_at.isoformat(),
            has_credentials=bool(portal.credentials.username),
            has_session=bool(getattr(portal, "session_blob", "") or portal.cookies),
            has_totp=bool(getattr(portal, "totp_secret_encrypted", "")),
            session_updated_at=(
                portal.session_updated_at.isoformat()
                if getattr(portal, "session_updated_at", None)
                else None
            ),
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
        from app.services.session_vault import SessionVault, normalize_cookies

        vault = SessionVault()
        portal = await self.portals.create(
            {
                "user_id": user_id,
                "name": payload.name,
                "credentials": payload.credentials.model_dump(),
                "proxy": payload.proxy.model_dump(),
                "cookies": {},
                "selector_version": payload.selector_version or 1,
                "status": PortalStatus.CONNECTED,
            }
        )
        cookies = normalize_cookies(payload.cookies)
        if cookies:
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

    async def update(self, user_id: str, portal_id: str, payload: PortalUpdate) -> PortalResponse:
        portal = await self._owned(user_id, portal_id)
        from app.services.session_vault import SessionVault, normalize_cookies

        vault = SessionVault()
        data = payload.model_dump(exclude_unset=True)
        totp = data.pop("totp_secret", None)
        cookies_raw = data.pop("cookies", None)
        data["updated_at"] = datetime.utcnow()
        portal = await self.portals.update(portal, data)
        if cookies_raw is not None:
            vault.save_cookies(portal, normalize_cookies(cookies_raw))
        if totp is not None:
            vault.save_totp_secret(portal, totp)
        await portal.save()
        return self._to_response(portal)

    async def sync(self, user_id: str, portal_id: str) -> PortalResponse:
        portal = await self._owned(user_id, portal_id)
        # Mark in-progress only — last_sync_at is written by FetchWorker on success.
        portal.sync_started_at = datetime.utcnow()
        portal.updated_at = datetime.utcnow()
        await portal.save()
        mode = await publish_job_fetch(
            user_id,
            portal=portal.name.value,
            portal_id=str(portal.id),
            source="portal.sync",
        )
        from app.events.realtime import emit_realtime
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "portal.sync_requested",
            message=f"Sync requested for {portal.name.value} ({mode})",
            resource_type="portal",
            resource_id=str(portal.id),
            severity="success",
            metadata={"portal": portal.name.value, "mode": mode},
        )
        await emit_realtime(
            user_id,
            "portal.sync_started",
            {
                "portal": portal.name.value,
                "portal_id": str(portal.id),
                "mode": mode,
            },
            title=f"{portal.name.value} sync started",
            body="Fetching jobs in the background…",
            severity="info",
        )
        return self._to_response(portal)

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

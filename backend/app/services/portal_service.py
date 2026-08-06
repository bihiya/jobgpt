"""Job portal connector service."""

from datetime import datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.core.kafka import publish
from app.models.enums import PortalStatus
from app.models.portal import Portal
from app.repository.portal_repository import PortalRepository
from app.schemas.portal import PortalCreate, PortalResponse, PortalUpdate


class PortalService:
    def __init__(self, portals: PortalRepository | None = None) -> None:
        self.portals = portals or PortalRepository()

    def _to_response(self, portal: Portal) -> PortalResponse:
        return PortalResponse(
            id=str(portal.id),
            name=portal.name,
            status=portal.status,
            last_sync_at=portal.last_sync_at.isoformat() if portal.last_sync_at else None,
            created_at=portal.created_at.isoformat(),
            has_credentials=bool(portal.credentials.username),
        )

    async def list(self, user_id: str) -> list[PortalResponse]:
        items = await self.portals.list_for_user(user_id)
        return [self._to_response(p) for p in items]

    async def create(self, user_id: str, payload: PortalCreate) -> PortalResponse:
        existing = await self.portals.get_by_name(user_id, payload.name)
        if existing:
            raise ConflictError("Portal already connected")
        portal = await self.portals.create(
            {
                "user_id": user_id,
                "name": payload.name,
                "credentials": payload.credentials.model_dump(),
                "proxy": payload.proxy.model_dump(),
                "cookies": payload.cookies,
                "status": PortalStatus.CONNECTED,
            }
        )
        return self._to_response(portal)

    async def update(self, user_id: str, portal_id: str, payload: PortalUpdate) -> PortalResponse:
        portal = await self._owned(user_id, portal_id)
        data = payload.model_dump(exclude_unset=True)
        data["updated_at"] = datetime.utcnow()
        portal = await self.portals.update(portal, data)
        return self._to_response(portal)

    async def sync(self, user_id: str, portal_id: str) -> PortalResponse:
        portal = await self._owned(user_id, portal_id)
        portal.last_sync_at = datetime.utcnow()
        portal.status = PortalStatus.CONNECTED
        await portal.save()
        await publish(
            "job.fetch",
            {"user_id": user_id, "portal": portal.name.value, "portal_id": str(portal.id)},
            key=user_id,
        )
        return self._to_response(portal)

    async def delete(self, user_id: str, portal_id: str) -> None:
        portal = await self._owned(user_id, portal_id)
        await self.portals.delete(portal)

    async def _owned(self, user_id: str, portal_id: str) -> Portal:
        portal = await self.portals.get_by_id(portal_id)
        if not portal or portal.user_id != user_id:
            raise NotFoundError("Portal not found")
        return portal

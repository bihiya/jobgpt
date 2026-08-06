"""User settings service."""

from datetime import datetime

from app.repository.settings_repository import SettingsRepository
from app.schemas.settings import SettingsResponse, SettingsUpdate


class SettingsService:
    def __init__(self, settings_repo: SettingsRepository | None = None) -> None:
        self.settings_repo = settings_repo or SettingsRepository()

    def _to_response(self, doc) -> SettingsResponse:
        return SettingsResponse(
            match_threshold=doc.match_threshold,
            auto_apply=doc.auto_apply,
            max_applications_per_day=doc.max_applications_per_day,
            headless=doc.headless,
            timezone=doc.timezone,
            notification_email=doc.notification_email,
        )

    async def get(self, user_id: str) -> SettingsResponse:
        doc = await self.settings_repo.get_or_create(user_id)
        return self._to_response(doc)

    async def update(self, user_id: str, payload: SettingsUpdate) -> SettingsResponse:
        doc = await self.settings_repo.get_or_create(user_id)
        data = payload.model_dump(exclude_unset=True)
        data["updated_at"] = datetime.utcnow()
        doc = await self.settings_repo.update(doc, data)
        return self._to_response(doc)

"""Onboarding wizard state machine: profile → resume → portals → sync."""

from __future__ import annotations

from app.core.kafka import publish
from app.repository.resume_repository import ResumeRepository
from app.repository.portal_repository import PortalRepository
from app.repository.settings_repository import SettingsRepository
from app.repository.user_repository import UserRepository
from app.services.question_bank_service import QuestionBankService


STEPS = ["profile", "resume", "portals", "sync", "done"]


class OnboardingService:
    def __init__(self) -> None:
        self.settings = SettingsRepository()
        self.users = UserRepository()
        self.resumes = ResumeRepository()
        self.portals = PortalRepository()
        self.questions = QuestionBankService()

    async def status(self, user_id: str) -> dict:
        settings = await self.settings.get_or_create(user_id)
        user = await self.users.get_by_id(user_id)
        resumes = await self.resumes.list_for_user(user_id)
        portals = await self.portals.list_for_user(user_id)
        profile_ok = bool(user and user.profile.skills and user.profile.location)
        return {
            "completed": settings.onboarding_completed,
            "step": settings.onboarding_step,
            "steps": STEPS,
            "checklist": {
                "profile": profile_ok,
                "resume": len(resumes) > 0,
                "portals": len(portals) > 0,
                "sync": settings.onboarding_step in {"sync", "done"} or settings.onboarding_completed,
            },
        }

    async def advance(self, user_id: str, step: str) -> dict:
        if step not in STEPS:
            step = "profile"
        settings = await self.settings.get_or_create(user_id)
        settings.onboarding_step = step
        if step == "done":
            settings.onboarding_completed = True
            user = await self.users.get_by_id(user_id)
            if user:
                await self.questions.seed_defaults(user_id, user.profile.model_dump())
        settings.updated_at = __import__("datetime").datetime.utcnow()
        await settings.save()
        return await self.status(user_id)

    async def trigger_first_sync(self, user_id: str) -> dict:
        await publish("job.fetch", {"user_id": user_id, "source": "onboarding"}, key=user_id)
        return await self.advance(user_id, "done")

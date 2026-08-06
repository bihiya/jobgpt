"""Daily application caps and per-portal cooldown to reduce bans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.settings import UserSettings


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str = ""
    applied_today: int = 0
    max_per_day: int = 0
    cooldown_seconds: int = 0
    retry_after_seconds: int = 0


ACTIVE_TODAY = [
    ApplicationStatus.SUCCESS,
    ApplicationStatus.IN_PROGRESS,
    ApplicationStatus.RETRYING,
    ApplicationStatus.FOLLOW_UP,
]


class ApplyRateLimiter:
    async def check(
        self,
        user_id: str,
        settings: UserSettings,
        *,
        portal: str = "",
    ) -> RateLimitDecision:
        max_per_day = int(getattr(settings, "max_applications_per_day", 50) or 50)
        cooldown = int(getattr(settings, "apply_cooldown_seconds", 45) or 45)
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        applied_today = await Application.find(
            {
                "user_id": user_id,
                "status": {"$in": [ApplicationStatus.SUCCESS, ApplicationStatus.FOLLOW_UP]},
                "applied_at": {"$gte": start},
            }
        ).count()

        if applied_today >= max_per_day:
            return RateLimitDecision(
                allowed=False,
                reason=f"Daily application cap reached ({applied_today}/{max_per_day})",
                applied_today=applied_today,
                max_per_day=max_per_day,
                cooldown_seconds=cooldown,
            )

        if cooldown > 0:
            filters: dict = {
                "user_id": user_id,
                "status": {"$in": list(ACTIVE_TODAY)},
                "updated_at": {"$gte": datetime.utcnow() - timedelta(seconds=cooldown)},
            }
            # Prefer portal-scoped cooldown when we can join via recent apps —
            # applications don't store portal; use recent SUCCESS/IN_PROGRESS globally.
            recent = (
                await Application.find({"user_id": user_id})
                .sort([("updated_at", -1)])
                .limit(1)
                .to_list()
            )
            if recent:
                last = recent[0]
                if last.status in ACTIVE_TODAY and last.updated_at:
                    elapsed = (datetime.utcnow() - last.updated_at).total_seconds()
                    if elapsed < cooldown and last.status == ApplicationStatus.IN_PROGRESS:
                        wait = int(cooldown - elapsed)
                        return RateLimitDecision(
                            allowed=False,
                            reason=f"Apply cooldown active — wait {wait}s (anti-ban)",
                            applied_today=applied_today,
                            max_per_day=max_per_day,
                            cooldown_seconds=cooldown,
                            retry_after_seconds=wait,
                        )
                    if (
                        last.status == ApplicationStatus.SUCCESS
                        and last.applied_at
                        and (datetime.utcnow() - last.applied_at).total_seconds() < cooldown
                    ):
                        wait = int(cooldown - (datetime.utcnow() - last.applied_at).total_seconds())
                        return RateLimitDecision(
                            allowed=False,
                            reason=f"Apply cooldown active — wait {wait}s (anti-ban)",
                            applied_today=applied_today,
                            max_per_day=max_per_day,
                            cooldown_seconds=cooldown,
                            retry_after_seconds=max(wait, 1),
                        )

        return RateLimitDecision(
            allowed=True,
            applied_today=applied_today,
            max_per_day=max_per_day,
            cooldown_seconds=cooldown,
        )

"""Per-portal health score and auto-pause on repeated failures."""

from __future__ import annotations

from datetime import datetime

from app.core.logging import get_logger
from app.models.enums import PortalStatus
from app.models.portal import Portal

logger = get_logger(__name__)

AUTO_PAUSE_THRESHOLD = 5
HEALTH_DECAY_ON_FAIL = 12
HEALTH_GAIN_ON_SUCCESS = 5


class PortalHealthService:
    async def record_success(self, portal: Portal) -> Portal:
        h = portal.health
        h.success_count += 1
        h.consecutive_failures = 0
        h.score = min(100.0, h.score + HEALTH_GAIN_ON_SUCCESS)
        h.last_error = ""
        if h.auto_paused and h.score >= 40:
            h.auto_paused = False
            h.paused_reason = ""
            portal.status = PortalStatus.CONNECTED
        portal.health = h
        portal.updated_at = datetime.utcnow()
        await portal.save()
        return portal

    async def record_failure(self, portal: Portal, error: str) -> Portal:
        h = portal.health
        h.failure_count += 1
        h.consecutive_failures += 1
        h.score = max(0.0, h.score - HEALTH_DECAY_ON_FAIL)
        h.last_error = error[:500]
        if h.consecutive_failures >= AUTO_PAUSE_THRESHOLD or h.score <= 20:
            h.auto_paused = True
            h.paused_reason = f"Auto-paused after {h.consecutive_failures} failures"
            portal.status = PortalStatus.ERROR
            logger.warning(
                "portal_auto_paused",
                portal=portal.name,
                score=h.score,
                failures=h.consecutive_failures,
            )
        portal.health = h
        portal.updated_at = datetime.utcnow()
        await portal.save()
        return portal

    def is_usable(self, portal: Portal) -> bool:
        if portal.health.auto_paused:
            return False
        if portal.status == PortalStatus.DISCONNECTED:
            return False
        return portal.health.score > 20

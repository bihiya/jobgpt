"""Notification worker."""

from typing import Any

from app.core.logging import get_logger
from app.models.notification import Notification
from app.workers.base import BaseWorker

logger = get_logger(__name__)


class NotificationWorker(BaseWorker):
    topics = ["notifications", "job.success", "job.failed"]
    group_id = "jobpilot-notifications"

    async def handle(self, topic: str, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        if not user_id:
            return

        if topic == "notifications":
            title = payload.get("title", "Notification")
            body = payload.get("body", "")
            ntype = payload.get("type", "info")
        elif topic == "job.success":
            title = "Job application succeeded"
            body = f"Application {payload.get('application_id')} succeeded"
            ntype = "success"
        else:
            title = "Job application failed"
            body = payload.get("error", "Application failed")
            ntype = "error"

        await Notification(user_id=user_id, title=title, body=body, type=ntype).insert()
        logger.info("notification_created", user_id=user_id, title=title)


if __name__ == "__main__":
    from app.workers.bootstrap import main

    main(NotificationWorker().start)

"""Application calendar + follow-up reminders."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil

from app.core.exceptions import NotFoundError
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import Job
from app.models.reminder import Reminder
from app.schemas.common import PaginatedResponse
from app.services.notifications.dispatcher import NotificationDispatcher


class ReminderService:
    def __init__(self) -> None:
        self.notifier = NotificationDispatcher()

    async def schedule_follow_up(
        self,
        user_id: str,
        application: Application,
        days: int = 7,
    ) -> Reminder:
        job = await Job.get(application.job_id)
        title = f"Follow up: {job.title if job else 'Application'}"
        due = datetime.utcnow() + timedelta(days=days)
        application.follow_up_at = due
        application.status = ApplicationStatus.FOLLOW_UP
        await application.save()
        reminder = Reminder(
            user_id=user_id,
            application_id=str(application.id),
            job_id=application.job_id,
            title=title,
            due_at=due,
        )
        await reminder.insert()
        return reminder

    async def calendar(self, user_id: str, month: int | None = None, year: int | None = None) -> list[dict]:
        now = datetime.utcnow()
        month = month or now.month
        year = year or now.year
        start = datetime(year, month, 1)
        end = datetime(year + (month // 12), (month % 12) + 1, 1)
        apps = await Application.find(
            {
                "user_id": user_id,
                "$or": [
                    {"applied_at": {"$gte": start, "$lt": end}},
                    {"follow_up_at": {"$gte": start, "$lt": end}},
                ],
            }
        ).to_list()
        events = []
        for app in apps:
            job = await Job.get(app.job_id)
            if app.applied_at and start <= app.applied_at < end:
                events.append(
                    {
                        "id": f"applied-{app.id}",
                        "type": "applied",
                        "date": app.applied_at.isoformat(),
                        "title": job.title if job else "Applied",
                        "company": job.company if job else "",
                        "application_id": str(app.id),
                        "job_id": app.job_id,
                    }
                )
            if app.follow_up_at and start <= app.follow_up_at < end:
                events.append(
                    {
                        "id": f"followup-{app.id}",
                        "type": "follow_up",
                        "date": app.follow_up_at.isoformat(),
                        "title": f"Follow up — {job.title if job else 'Application'}",
                        "company": job.company if job else "",
                        "application_id": str(app.id),
                        "job_id": app.job_id,
                    }
                )
        return sorted(events, key=lambda e: e["date"])

    async def due(self, user_id: str) -> list[dict]:
        items = await Reminder.find(
            {"user_id": user_id, "is_completed": False, "due_at": {"$lte": datetime.utcnow()}}
        ).to_list()
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "due_at": r.due_at.isoformat(),
                "application_id": r.application_id,
                "job_id": r.job_id,
            }
            for r in items
        ]

    async def complete(self, user_id: str, reminder_id: str) -> None:
        reminder = await Reminder.get(reminder_id)
        if not reminder or reminder.user_id != user_id:
            raise NotFoundError("Reminder not found")
        reminder.is_completed = True
        await reminder.save()

    async def notify_due(self, user_id: str) -> int:
        items = await self.due(user_id)
        for item in items:
            await self.notifier.dispatch(
                user_id,
                event="reminder.due",
                title="Follow-up due",
                body=item["title"],
                type_="info",
                metadata=item,
            )
        return len(items)

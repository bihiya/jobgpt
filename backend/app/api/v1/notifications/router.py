"""Notification channel configuration + calendar/reminders."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.enums import AlertChannel
from app.models.user import User
from app.models.webhook import NotificationChannel
from app.schemas.common import MessageResponse
from app.services.reminder_service import ReminderService

router = APIRouter(tags=["notifications"])


class ChannelCreate(BaseModel):
    channel: AlertChannel
    target: str
    events: list[str] = Field(
        default_factory=lambda: ["job.success", "job.failed", "approval.needed", "reminder.due"]
    )
    is_enabled: bool = True


@router.get("/notification-channels")
async def list_channels(user: User = Depends(get_current_user)):
    items = await NotificationChannel.find({"user_id": str(user.id)}).to_list()
    return [
        {
            "id": str(c.id),
            "channel": c.channel,
            "target": c.target,
            "events": c.events,
            "is_enabled": c.is_enabled,
        }
        for c in items
    ]


@router.post("/notification-channels", status_code=201)
async def create_channel(payload: ChannelCreate, user: User = Depends(get_current_user)):
    doc = NotificationChannel(user_id=str(user.id), **payload.model_dump())
    await doc.insert()
    return {"id": str(doc.id), "channel": doc.channel, "target": doc.target}


@router.delete("/notification-channels/{channel_id}", response_model=MessageResponse)
async def delete_channel(channel_id: str, user: User = Depends(get_current_user)):
    doc = await NotificationChannel.get(channel_id)
    if doc and doc.user_id == str(user.id):
        await doc.delete()
    return MessageResponse(detail="Deleted")


@router.get("/calendar")
async def calendar(
    month: int | None = None,
    year: int | None = None,
    user: User = Depends(get_current_user),
):
    return await ReminderService().calendar(str(user.id), month=month, year=year)


@router.get("/reminders/due")
async def reminders_due(user: User = Depends(get_current_user)):
    return await ReminderService().due(str(user.id))


@router.post("/reminders/{reminder_id}/complete", response_model=MessageResponse)
async def complete_reminder(reminder_id: str, user: User = Depends(get_current_user)):
    await ReminderService().complete(str(user.id), reminder_id)
    return MessageResponse(detail="Completed")

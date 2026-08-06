"""Multi-channel alerts: in-app, email, Slack, webhook."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.kafka import publish
from app.models.enums import AlertChannel
from app.models.notification import Notification
from app.models.webhook import NotificationChannel

logger = get_logger(__name__)


class NotificationDispatcher:
    async def dispatch(
        self,
        user_id: str,
        *,
        event: str,
        title: str,
        body: str,
        type_: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        metadata = metadata or {}
        await Notification(user_id=user_id, title=title, body=body, type=type_).insert()
        await publish(
            "notifications",
            {
                "user_id": user_id,
                "event": event,
                "title": title,
                "body": body,
                "type": type_,
                "metadata": metadata,
            },
            key=user_id,
        )

        channels = await NotificationChannel.find(
            {"user_id": user_id, "is_enabled": True}
        ).to_list()
        for channel in channels:
            if event not in channel.events and "*" not in channel.events:
                continue
            try:
                if channel.channel == AlertChannel.SLACK:
                    await self._slack(channel.target, title, body)
                elif channel.channel == AlertChannel.WEBHOOK:
                    await self._webhook(channel.target, event, title, body, metadata)
                elif channel.channel == AlertChannel.EMAIL:
                    await self._email(channel.target, title, body)
            except Exception as exc:  # noqa: BLE001
                logger.warning("alert_channel_failed", channel=channel.channel, error=str(exc))

    async def _slack(self, webhook_url: str, title: str, body: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                webhook_url,
                json={"text": f"*{title}*\n{body}"},
            )

    async def _webhook(
        self,
        url: str,
        event: str,
        title: str,
        body: str,
        metadata: dict[str, Any],
    ) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                json={"event": event, "title": title, "body": body, "metadata": metadata},
            )

    async def _email(self, to_email: str, title: str, body: str) -> None:
        if not settings.smtp_host:
            logger.info("email_skipped_no_smtp", to=to_email, title=title)
            return
        # Lightweight SMTP send via aiosmtplib if configured
        try:
            import aiosmtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = settings.smtp_from
            msg["To"] = to_email
            msg["Subject"] = f"[JobPilot] {title}"
            msg.set_content(body)
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username or None,
                password=settings.smtp_password or None,
                start_tls=settings.smtp_tls,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("email_send_failed", error=str(exc), to=to_email)

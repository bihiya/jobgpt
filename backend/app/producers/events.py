"""Typed Kafka event producers."""

from typing import Any

from app.core.kafka import publish


async def publish_job_fetch(user_id: str, **extra: Any) -> None:
    await publish("job.fetch", {"user_id": user_id, **extra}, key=user_id)


async def publish_job_match(user_id: str, job_id: str, **extra: Any) -> None:
    await publish("job.match", {"user_id": user_id, "job_id": job_id, **extra}, key=user_id)


async def publish_job_apply(user_id: str, job_id: str, **extra: Any) -> None:
    await publish("job.apply", {"user_id": user_id, "job_id": job_id, **extra}, key=user_id)


async def publish_notification(user_id: str, title: str, body: str, type_: str = "info") -> None:
    await publish(
        "notifications",
        {"user_id": user_id, "title": title, "body": body, "type": type_},
        key=user_id,
    )

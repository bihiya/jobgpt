"""
Celery integration for CPU/IO background tasks (complementary to Kafka workers).

Kafka: event-driven pipeline (fetch → match → apply)
Celery: scheduled/ad-hoc tasks (report generation, cache warming, cleanup)
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "jobpilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="jobpilot",
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="jobpilot.warm_analytics_cache", bind=True, max_retries=3)
def warm_analytics_cache(self, user_id: str) -> dict:
    """Sync Celery task wrapper — runs cache warming outside the request path."""
    return {"user_id": user_id, "status": "queued_for_warm"}


@celery_app.task(name="jobpilot.cleanup_expired_tokens", bind=True)
def cleanup_expired_tokens(self) -> dict:
    return {"status": "ok"}


@celery_app.task(name="jobpilot.generate_report", bind=True, autoretry_for=(Exception,), retry_backoff=True)
def generate_report_task(self, user_id: str, report_id: str) -> dict:
    return {"user_id": user_id, "report_id": report_id, "status": "accepted"}

"""Pipeline column mapping and drag-to-queue auto-apply."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.enums import JobStatus
from app.schemas.application import ApplicationCreate
from app.services.job_service import JobService
from app.services.pipeline import (
    PIPELINE_COLUMN_KEYS,
    column_for_status,
    should_queue_apply,
    target_status_for_column,
)


def test_pipeline_has_five_flow_columns():
    assert PIPELINE_COLUMN_KEYS == ("fetched", "queued", "applied", "interview", "shortlisted")


def test_column_for_status_maps_fetched_and_queued():
    assert column_for_status(JobStatus.NEW) == "fetched"
    assert column_for_status(JobStatus.MATCHED) == "fetched"
    assert column_for_status(JobStatus.AWAITING_APPROVAL) == "fetched"
    assert column_for_status(JobStatus.FAILED) == "fetched"
    assert column_for_status(JobStatus.APPLYING) == "queued"
    assert column_for_status(JobStatus.APPROVED) == "queued"
    assert column_for_status(JobStatus.APPLIED) == "applied"
    assert column_for_status(JobStatus.INTERVIEW) == "interview"
    assert column_for_status(JobStatus.OFFER) == "shortlisted"
    assert column_for_status(JobStatus.SHORTLISTED) == "shortlisted"
    assert column_for_status(JobStatus.REJECTED) is None


def test_drop_on_queued_starts_auto_apply():
    assert should_queue_apply("fetched", "queued") is True
    assert should_queue_apply("applied", "queued") is True
    assert should_queue_apply("queued", "queued") is False
    assert should_queue_apply("queued", "applied") is False
    assert should_queue_apply("applied", "interview") is False


def test_target_status_for_column():
    assert target_status_for_column("queued") == JobStatus.APPLYING
    assert target_status_for_column("shortlisted") == JobStatus.SHORTLISTED
    with pytest.raises(ValueError):
        target_status_for_column("rejected")


def _job(**overrides):
    data = dict(
        id="job1",
        user_id="u1",
        title="Engineer",
        company="Acme",
        location="Remote",
        salary="",
        experience="",
        description="",
        skills=[],
        apply_url="https://example.com",
        portal="linkedin",
        status=JobStatus.MATCHED,
        match_score=0.91,
        match_breakdown=None,
        source="portal",
        fetched_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_move_fetched_to_queued_queues_application():
    job = _job()
    jobs_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=job))
    apps = SimpleNamespace(queue=AsyncMock(return_value=SimpleNamespace(id="app-1")))

    async def queue(user_id, payload: ApplicationCreate):
        assert payload.job_id == "job1"
        job.status = JobStatus.APPLYING
        return SimpleNamespace(id="app-1")

    apps.queue = queue
    service = JobService(jobs=jobs_repo, applications=apps)

    result = await service.move_to_column("u1", "job1", "queued")

    assert result.queued is True
    assert result.application_id == "app-1"
    assert result.column == "queued"
    assert result.job.status == JobStatus.APPLYING


@pytest.mark.asyncio
async def test_move_applied_to_interview_updates_status_only(monkeypatch):
    job = _job(status=JobStatus.APPLIED)
    jobs_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=job),
        update=AsyncMock(side_effect=lambda doc, data: _apply_update(doc, data)),
    )
    apps = SimpleNamespace(
        queue=AsyncMock(),
        cancel_active_for_job=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.services.audit_service.audit_event",
        AsyncMock(),
    )
    service = JobService(jobs=jobs_repo, applications=apps)

    result = await service.move_to_column("u1", "job1", "interview")

    assert result.queued is False
    assert result.job.status == JobStatus.INTERVIEW
    apps.queue.assert_not_called()


def _apply_update(doc, data):
    for key, value in data.items():
        setattr(doc, key, value)
    return doc

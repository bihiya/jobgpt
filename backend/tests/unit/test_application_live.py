"""Application list filters and live snapshots."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.enums import ApplicationStatus
from app.schemas.application import ApplicationCreate
from app.services.application_service import ApplicationService


def _app(**overrides):
    data = dict(
        id="a1",
        job_id="j1",
        resume_id=None,
        status=ApplicationStatus.IN_PROGRESS,
        attempts=1,
        screenshot_path="",
        screenshot_url="",
        error_message="",
        applied_at=None,
        created_at=datetime(2026, 8, 16, 10, 0, 0),
        updated_at=datetime(2026, 8, 16, 11, 0, 0),
        session_steps=[{"key": "started", "label": "Worker started applying"}],
        unknown_questions=[],
        blocker_type="",
        correlation_id="",
        user_id="u1",
        save=AsyncMock(),
    )
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_list_filters_by_job_id():
    repo = SimpleNamespace(list_for_user=AsyncMock(return_value=([_app()], 1)))
    service = ApplicationService(applications=repo, jobs=SimpleNamespace())
    page = await service.list("u1", page=1, page_size=20, job_id="j1")
    repo.list_for_user.assert_awaited_with("u1", None, 1, 20, job_id="j1")
    assert page.items[0].id == "a1"
    assert page.items[0].updated_at.endswith("Z")
    assert page.items[0].session_steps[0]["key"] == "started"


@pytest.mark.asyncio
async def test_latest_by_job_ids_maps_responses():
    repo = SimpleNamespace(latest_for_jobs=AsyncMock(return_value={"j1": _app()}))
    service = ApplicationService(applications=repo, jobs=SimpleNamespace())
    mapping = await service.latest_by_job_ids("u1", ["j1", "j2"])
    assert mapping["j1"].status == ApplicationStatus.IN_PROGRESS
    repo.latest_for_jobs.assert_awaited_with("u1", ["j1", "j2"])


@pytest.mark.asyncio
async def test_queue_records_a_waiting_step(monkeypatch):
    job = SimpleNamespace(
        id="j1",
        user_id="u1",
        title="Engineer",
        status="matched",
        save=AsyncMock(),
    )
    created = _app(status=ApplicationStatus.PENDING, session_steps=[])
    repo = SimpleNamespace(
        find_active_for_job=AsyncMock(return_value=None),
        create=AsyncMock(return_value=created),
    )
    service = ApplicationService(
        applications=repo,
        jobs=SimpleNamespace(get_by_id=AsyncMock(return_value=job)),
    )
    monkeypatch.setattr("app.services.application_service.publish_job_apply", AsyncMock())
    monkeypatch.setattr("app.services.application_service.emit_realtime", AsyncMock())
    monkeypatch.setattr("app.services.application_service.audit_event", AsyncMock())
    await service.queue("u1", ApplicationCreate(job_id="j1"))
    payload = repo.create.await_args.args[0]
    assert payload["session_steps"][0]["key"] == "queued"
    assert payload["session_steps"][0]["label"] == "Queued for auto-apply"

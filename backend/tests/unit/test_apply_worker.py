"""Apply worker: LinkedIn success, already-applied, and crash → failed."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.automation.base.portal import ApplyResult
from app.automation.session_recorder import ApplySessionRecorder
from app.models.enums import ApplicationStatus, JobStatus
from app.workers.apply_worker import ApplyWorker


def _job(**overrides):
    data = dict(
        id="j1",
        user_id="u1",
        portal="linkedin",
        title="Software Engineer",
        company="Acme",
        location="Remote",
        description="",
        skills=[],
        apply_url="https://www.linkedin.com/jobs/view/4123456789/",
        external_id="linkedin-4123456789",
        status=JobStatus.APPLYING,
        save=AsyncMock(),
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _app(**overrides):
    data = dict(
        id="a1",
        user_id="u1",
        job_id="j1",
        resume_id="r1",
        status=ApplicationStatus.PENDING,
        attempts=0,
        session_steps=[],
        blocker_type="",
        unknown_questions=[],
        error_message="",
        screenshot_path="",
        screenshot_url="",
        fail_proof_html="",
        fail_proof_path="",
        correlation_id="",
        applied_at=None,
        next_retry_at=None,
        updated_at=datetime.utcnow(),
        save=AsyncMock(),
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _resume():
    return SimpleNamespace(id="r1", file_path="/tmp/resume.pdf")


def _portal_doc():
    return SimpleNamespace(
        credentials=SimpleNamespace(model_dump=lambda: {}),
        proxy=SimpleNamespace(server="", model_dump=lambda: {}),
        selector_version=1,
        updated_at=None,
        save=AsyncMock(),
    )


def _worker(job, app, portal_doc=None):
    worker = ApplyWorker()
    worker.jobs.get_by_id = AsyncMock(return_value=job)
    worker.resumes.get_by_id = AsyncMock(return_value=_resume())
    worker.resumes.get_default = AsyncMock(return_value=_resume())
    worker.portals.find_one = AsyncMock(return_value=portal_doc or _portal_doc())
    worker.settings.get_or_create = AsyncMock(
        return_value=SimpleNamespace(headless=True, follow_up_days=7)
    )
    worker.rate_limiter.check = AsyncMock(return_value=SimpleNamespace(allowed=True))
    worker.health.is_usable = MagicMock(return_value=True)
    worker.health.record_success = AsyncMock()
    worker.health.record_failure = AsyncMock()
    worker.vault.load_cookies = MagicMock(return_value=[{"name": "li_at", "value": "tok"}])
    worker.vault.load_totp_secret = MagicMock(return_value="")
    worker.vault.save_cookies = MagicMock()
    worker.portals.list_for_user = AsyncMock(return_value=[])
    worker.users.get_by_id = AsyncMock(
        return_value=SimpleNamespace(
            profile=SimpleNamespace(experience_years=5, notice_period_days=30, location="Remote")
        )
    )
    worker.questions.resolve_answers = AsyncMock(return_value={})
    worker.questions.list = AsyncMock(return_value=[])
    worker.storage.as_local_file = AsyncMock(return_value="/tmp/resume.pdf")
    worker.storage.cleanup_temp = AsyncMock()
    worker.storage.save_file = AsyncMock(
        return_value={"url": "https://shot/ok.png", "path": "shots/ok.png"}
    )
    worker.reminders.schedule_follow_up = AsyncMock()
    worker.notifier.dispatch = AsyncMock()
    return worker


class _Log:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def insert(self):
        return None


@pytest.mark.asyncio
async def test_apply_worker_marks_linkedin_success():
    job = _job()
    app = _app()
    worker = _worker(job, app)
    adapter = MagicMock()
    adapter.recorder = ApplySessionRecorder()
    adapter.recorder.correlation_id = "cid-1"
    adapter.session_identity = {}
    adapter.apply_with_retry = AsyncMock(
        return_value=ApplyResult(
            success=True,
            message="Applied via LinkedIn Easy Apply (verified)",
            steps=[{"key": "verified", "label": "Verified apply result", "status": "ok"}],
            screenshot_path="/tmp/ok.png",
            cookies=[{"name": "li_at", "value": "tok"}],
            correlation_id="cid-1",
        )
    )

    with (
        patch("app.workers.apply_worker.Application.get", new=AsyncMock(return_value=app)),
        patch("app.workers.apply_worker.AutomationLog", _Log),
        patch("app.workers.apply_worker.get_portal_adapter", return_value=adapter),
        patch("app.workers.apply_worker.emit_realtime", new=AsyncMock()),
        patch("app.workers.apply_worker.publish", new=AsyncMock()),
        patch("app.workers.apply_worker.audit_event", new=AsyncMock()),
        patch("app.workers.apply_worker.apply_identity_to_portal"),
    ):
        await worker.handle("job.apply", {"user_id": "u1", "job_id": "j1", "application_id": "a1"})

    assert app.status == ApplicationStatus.SUCCESS
    assert job.status == JobStatus.APPLIED
    assert app.screenshot_url == "https://shot/ok.png"
    worker.health.record_success.assert_awaited()
    worker.notifier.dispatch.assert_awaited()
    adapter.apply_with_retry.assert_awaited_once()
    extracted = adapter.apply_with_retry.await_args.args[0]
    assert extracted.apply_url == job.apply_url
    assert extracted.title == "Software Engineer"
    assert any(step["key"] == "started" for step in adapter.recorder.to_list())


@pytest.mark.asyncio
async def test_apply_worker_already_applied_is_success():
    job = _job()
    app = _app()
    worker = _worker(job, app)
    adapter = MagicMock()
    adapter.recorder = ApplySessionRecorder()
    adapter.recorder.correlation_id = "cid-2"
    adapter.session_identity = {}
    adapter.apply_with_retry = AsyncMock(
        return_value=ApplyResult(
            success=True,
            message="Already applied on LinkedIn",
            steps=[{"key": "verified", "label": "Already applied on LinkedIn", "status": "ok"}],
            correlation_id="cid-2",
        )
    )

    with (
        patch("app.workers.apply_worker.Application.get", new=AsyncMock(return_value=app)),
        patch("app.workers.apply_worker.AutomationLog", _Log),
        patch("app.workers.apply_worker.get_portal_adapter", return_value=adapter),
        patch("app.workers.apply_worker.emit_realtime", new=AsyncMock()),
        patch("app.workers.apply_worker.publish", new=AsyncMock()),
        patch("app.workers.apply_worker.audit_event", new=AsyncMock()),
        patch("app.workers.apply_worker.apply_identity_to_portal"),
    ):
        await worker.handle("job.apply", {"user_id": "u1", "job_id": "j1", "application_id": "a1"})

    assert app.status == ApplicationStatus.SUCCESS
    assert job.status == JobStatus.APPLIED


@pytest.mark.asyncio
async def test_apply_worker_crash_marks_failed():
    job = _job()
    app = _app()
    worker = _worker(job, app)
    adapter = MagicMock()
    adapter.recorder = ApplySessionRecorder()
    adapter.recorder.correlation_id = "cid-3"
    adapter.session_identity = {}
    adapter.apply_with_retry = AsyncMock(side_effect=RuntimeError("browser died"))

    with (
        patch("app.workers.apply_worker.Application.get", new=AsyncMock(return_value=app)),
        patch("app.workers.apply_worker.AutomationLog", _Log),
        patch("app.workers.apply_worker.get_portal_adapter", return_value=adapter),
        patch("app.workers.apply_worker.emit_realtime", new=AsyncMock()),
        patch("app.workers.apply_worker.publish", new=AsyncMock()),
        patch("app.workers.apply_worker.audit_event", new=AsyncMock()),
        patch("app.workers.apply_worker.apply_identity_to_portal"),
    ):
        await worker.handle("job.apply", {"user_id": "u1", "job_id": "j1", "application_id": "a1"})

    assert app.status == ApplicationStatus.FAILED
    assert "browser died" in app.error_message
    assert job.status == JobStatus.FAILED
    worker.storage.cleanup_temp.assert_awaited()


@pytest.mark.asyncio
async def test_apply_worker_timeout_marks_failed(monkeypatch):
    import asyncio

    job = _job()
    app = _app()
    worker = _worker(job, app)
    adapter = MagicMock()
    adapter.recorder = ApplySessionRecorder()
    adapter.session_identity = {}

    async def hang(*_args, **_kwargs):
        await asyncio.sleep(30)
        return ApplyResult(success=True)

    adapter.apply_with_retry = hang
    monkeypatch.setattr("app.workers.apply_worker._APPLY_TIMEOUT_S", 0.05)

    with (
        patch("app.workers.apply_worker.Application.get", new=AsyncMock(return_value=app)),
        patch("app.workers.apply_worker.AutomationLog", _Log),
        patch("app.workers.apply_worker.get_portal_adapter", return_value=adapter),
        patch("app.workers.apply_worker.emit_realtime", new=AsyncMock()),
        patch("app.workers.apply_worker.publish", new=AsyncMock()),
        patch("app.workers.apply_worker.audit_event", new=AsyncMock()),
        patch("app.workers.apply_worker.apply_identity_to_portal"),
    ):
        await worker.handle("job.apply", {"user_id": "u1", "job_id": "j1", "application_id": "a1"})

    assert app.status == ApplicationStatus.FAILED
    assert "timed out" in app.error_message.lower()
    assert any(step["key"] == "failed" for step in adapter.recorder.to_list())
    assert any(step["key"] == "prepare" for step in adapter.recorder.to_list())


@pytest.mark.asyncio
async def test_apply_worker_resume_download_timeout_marks_failed(monkeypatch):
    import asyncio

    job = _job()
    app = _app()
    worker = _worker(job, app)
    adapter = MagicMock()
    adapter.recorder = ApplySessionRecorder()
    adapter.session_identity = {}
    adapter.apply_with_retry = AsyncMock(return_value=ApplyResult(success=True))

    async def hang_download(_stored: str) -> str:
        await asyncio.sleep(30)
        return "/tmp/resume.pdf"

    worker.storage.as_local_file = hang_download
    monkeypatch.setattr("app.workers.apply_worker._RESUME_DOWNLOAD_TIMEOUT_S", 0.05)

    with (
        patch("app.workers.apply_worker.Application.get", new=AsyncMock(return_value=app)),
        patch("app.workers.apply_worker.AutomationLog", _Log),
        patch("app.workers.apply_worker.get_portal_adapter", return_value=adapter),
        patch("app.workers.apply_worker.emit_realtime", new=AsyncMock()),
        patch("app.workers.apply_worker.publish", new=AsyncMock()),
        patch("app.workers.apply_worker.audit_event", new=AsyncMock()),
        patch("app.workers.apply_worker.apply_identity_to_portal"),
    ):
        await worker.handle("job.apply", {"user_id": "u1", "job_id": "j1", "application_id": "a1"})

    assert app.status == ApplicationStatus.FAILED
    assert "resume" in app.error_message.lower()
    adapter.apply_with_retry.assert_not_called()


@pytest.mark.asyncio
async def test_apply_worker_continues_when_question_bank_list_fails():
    job = _job()
    app = _app()
    worker = _worker(job, app)
    worker.questions.list = AsyncMock(side_effect=RuntimeError("order-by item is excluded"))
    adapter = MagicMock()
    adapter.recorder = ApplySessionRecorder()
    adapter.recorder.correlation_id = "cid-4"
    adapter.session_identity = {}
    adapter.apply_with_retry = AsyncMock(
        return_value=ApplyResult(success=True, message="ok", correlation_id="cid-4")
    )

    with (
        patch("app.workers.apply_worker.Application.get", new=AsyncMock(return_value=app)),
        patch("app.workers.apply_worker.AutomationLog", _Log),
        patch("app.workers.apply_worker.get_portal_adapter", return_value=adapter),
        patch("app.workers.apply_worker.emit_realtime", new=AsyncMock()),
        patch("app.workers.apply_worker.publish", new=AsyncMock()),
        patch("app.workers.apply_worker.audit_event", new=AsyncMock()),
        patch("app.workers.apply_worker.apply_identity_to_portal"),
    ):
        await worker.handle("job.apply", {"user_id": "u1", "job_id": "j1", "application_id": "a1"})

    adapter.apply_with_retry.assert_awaited_once()
    assert app.status == ApplicationStatus.SUCCESS
    keys = [step["key"] for step in adapter.recorder.to_list()]
    assert "prepare" in keys
    assert "started" in keys


def test_remember_apply_channel_on_job():
    job = _job()
    result = ApplyResult(
        success=True,
        metadata={"apply_channel": "External apply · Workday", "ats": "workday"},
    )
    ApplyWorker._remember_apply_channel(job, result)
    assert job.metadata["apply_channel"] == "External apply · Workday"
    assert job.metadata["ats"] == "workday"

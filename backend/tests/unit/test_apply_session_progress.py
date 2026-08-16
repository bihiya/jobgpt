"""Live apply recorder must survive apply_with_retry (browser/login steps)."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob
from app.automation.captcha import CaptchaHookResult
from app.automation.session_recorder import ApplySessionRecorder


class _DummyPortal(BasePortal):
    name = "linkedin"

    async def login(self, page) -> None:
        self.recorder.add("login", "Opened LinkedIn (checking existing session)")

    async def search(self, page, query: str, location: str = "") -> None:
        return None

    async def extract_jobs(self, page):
        return []

    async def apply(self, page, job, resume_path: str, answers: dict) -> ApplyResult:
        self.recorder.opened_jd(job.apply_url)
        return ApplyResult(success=True, message="ok")


@pytest.mark.asyncio
async def test_apply_with_retry_keeps_live_recorder_and_emits_browser_login():
    seen: list[str] = []
    portal = _DummyPortal()
    portal.recorder = ApplySessionRecorder(on_step=lambda step: seen.append(step.key))
    portal.recorder.add("queued", "Queued for auto-apply", status="pending")
    portal.recorder.complete_pending("queued", detail="Worker picked up")
    portal.recorder.add("started", "Worker started applying", detail="linkedin")

    @asynccontextmanager
    async def fake_session():
        yield (None, None, MagicMock())

    portal.browser.session = fake_session  # type: ignore[method-assign]
    portal.handle_captcha = AsyncMock(return_value=CaptchaHookResult())
    portal.capture_screenshot = AsyncMock(return_value="/tmp/shot.png")

    result = await portal.apply_with_retry(
        ExtractedJob(
            external_id="1",
            title="Engineer",
            company="Acme",
            apply_url="https://www.linkedin.com/jobs/view/1",
        ),
        "/tmp/resume.pdf",
        {},
    )

    keys = [step["key"] for step in portal.recorder.to_list()]
    assert keys[:3] == ["queued", "started", "browser"]
    assert "login" in keys
    assert "opened_jd" in keys
    assert "login" in seen
    assert "opened_jd" in seen
    assert "browser" in seen
    assert result.success is True
    assert portal.recorder.to_list()[0]["status"] == "ok"


@pytest.mark.asyncio
async def test_apply_with_retry_flushes_browser_step_before_session():
    """Live UI must see 'Launching browser' before Chromium.session() starts."""
    order: list[str] = []

    async def on_step(step):
        order.append(f"{step.key}:{step.status}")

    portal = _DummyPortal()
    portal.recorder = ApplySessionRecorder(on_step=on_step)
    portal.recorder.add("started", "Worker started applying", detail="linkedin")

    @asynccontextmanager
    async def fake_session():
        order.append("session-start")
        yield (None, None, MagicMock())

    portal.browser.session = fake_session  # type: ignore[method-assign]
    portal.handle_captcha = AsyncMock(return_value=CaptchaHookResult())
    portal.capture_screenshot = AsyncMock(return_value="/tmp/shot.png")

    await portal.apply_with_retry(
        ExtractedJob(
            external_id="1",
            title="Engineer",
            company="Acme",
            apply_url="https://www.linkedin.com/jobs/view/1",
        ),
        "/tmp/resume.pdf",
        {},
    )

    assert "browser:pending" in order
    assert order.index("browser:pending") < order.index("session-start")

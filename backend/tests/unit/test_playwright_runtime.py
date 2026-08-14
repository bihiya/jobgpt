"""Playwright runtime detection and automation fallback guards."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.automation.playwright_runtime import (
    job_requires_playwright,
    playwright_unavailable_message,
    require_playwright_for_job,
)
from app.core.exceptions import ServiceUnavailableError


def test_job_requires_playwright():
    assert job_requires_playwright("fetch") is True
    assert job_requires_playwright("apply") is True
    assert job_requires_playwright("match") is False
    assert job_requires_playwright("report") is False


def test_require_playwright_skips_non_browser_jobs():
    require_playwright_for_job("match")  # does not raise


def test_require_playwright_raises_when_missing():
    with patch("app.automation.playwright_runtime.playwright_available", return_value=False):
        with pytest.raises(ServiceUnavailableError) as exc:
            require_playwright_for_job("fetch")
        assert exc.value.code == "PLAYWRIGHT_UNAVAILABLE"
        assert "Playwright" in exc.value.message


def test_vercel_message(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    message = playwright_unavailable_message()
    assert "serverless" in message.lower()
    assert "Docker" in message or "Kubernetes" in message


@pytest.mark.asyncio
async def test_automation_run_fails_fast_without_playwright():
    from app.services.automation_service import AutomationService

    service = AutomationService()

    with (
        patch(
            "app.services.automation_service.publish",
            new=AsyncMock(
                side_effect=ServiceUnavailableError("Kafka is disabled", code="KAFKA_DISABLED")
            ),
        ),
        patch("app.services.automation_service.settings") as settings_mock,
        patch("app.services.automation_log_service.write_automation_log", new=AsyncMock()),
        patch("app.services.automation_service.emit_realtime", new=AsyncMock()),
        patch("app.services.audit_service.audit_event", new=AsyncMock()),
        patch("app.automation.playwright_runtime.playwright_available", return_value=False),
    ):
        settings_mock.app_env = "production"
        settings_mock.kafka_enabled = False

        with pytest.raises(ServiceUnavailableError) as exc:
            await service.run("user-1", "fetch")
        assert exc.value.code == "PLAYWRIGHT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_publish_job_fetch_fails_fast_without_playwright():
    from app.producers.events import publish_job_fetch

    with (
        patch(
            "app.producers.events.publish",
            new=AsyncMock(
                side_effect=ServiceUnavailableError("Kafka is disabled", code="KAFKA_DISABLED")
            ),
        ),
        patch("app.producers.events.settings") as settings_mock,
        patch("app.automation.playwright_runtime.playwright_available", return_value=False),
        patch("app.services.automation_log_service.write_automation_log", new=AsyncMock()),
    ):
        settings_mock.app_env = "development"
        settings_mock.kafka_enabled = False

        with pytest.raises(ServiceUnavailableError) as exc:
            await publish_job_fetch("user-1", source="portal.sync")
        assert exc.value.code == "PLAYWRIGHT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_automation_match_still_runs_inline_without_playwright():
    from app.services.automation_service import AutomationService

    service = AutomationService()

    with (
        patch(
            "app.services.automation_service.publish",
            new=AsyncMock(
                side_effect=ServiceUnavailableError("Kafka is disabled", code="KAFKA_DISABLED")
            ),
        ),
        patch("app.services.automation_service.settings") as settings_mock,
        patch("app.services.automation_log_service.write_automation_log", new=AsyncMock()),
        patch("app.services.automation_service.emit_realtime", new=AsyncMock()),
        patch("app.services.audit_service.audit_event", new=AsyncMock()),
        patch(
            "app.services.automation_service.asyncio.create_task",
            side_effect=lambda coro: coro.close() or MagicMock(),
        ) as create_task,
        patch("app.automation.playwright_runtime.playwright_available", return_value=False),
    ):
        settings_mock.app_env = "development"
        settings_mock.kafka_enabled = False

        result = await service.run("user-1", "match")
        assert result["mode"] == "inline"
        create_task.assert_called_once()


def test_browser_stealth_uses_current_chrome_ua():
    from app.automation.base.browser import DEFAULT_USER_AGENT, STEALTH_INIT_SCRIPT

    assert "Chrome/120" not in DEFAULT_USER_AGENT
    assert "Chrome/139" in DEFAULT_USER_AGENT
    assert "webdriver" in STEALTH_INIT_SCRIPT

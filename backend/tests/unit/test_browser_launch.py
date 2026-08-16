"""Chromium launch must not hang in Docker / Azure Container Apps."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.automation.base.browser import BaseBrowser


def test_container_uses_bundled_chromium_with_no_sandbox(monkeypatch):
    monkeypatch.setattr("app.automation.base.browser.running_in_container", lambda: True)
    monkeypatch.setattr("app.automation.base.browser.needs_no_sandbox", lambda: True)
    monkeypatch.setattr("app.core.config.settings.playwright_channel", None)

    browser = BaseBrowser(headless=True)
    assert browser._channel_candidates() == [None]
    assert browser._effective_headless() is True
    args = browser._launch_args(headless=True)
    assert args["timeout"] == 45_000
    assert "--no-sandbox" in args["args"]
    assert "--disable-dev-shm-usage" in args["args"]
    assert "channel" not in args


def test_non_container_tries_chrome_channel_first(monkeypatch):
    monkeypatch.setattr("app.automation.base.browser.running_in_container", lambda: False)
    monkeypatch.setattr("app.core.config.settings.playwright_channel", None)

    browser = BaseBrowser()
    assert browser._channel_candidates() == ["chrome", None]


def test_explicit_channel_still_falls_back_to_bundled(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.playwright_channel", "msedge")
    browser = BaseBrowser()
    assert browser._channel_candidates() == ["msedge", None]


def test_playwright_no_sandbox_env(monkeypatch):
    monkeypatch.delenv("PLAYWRIGHT_NO_SANDBOX", raising=False)
    monkeypatch.setattr("app.automation.base.browser.running_in_container", lambda: False)
    monkeypatch.setattr("app.automation.base.browser.os.geteuid", lambda: 1000)
    from app.automation.base import browser as browser_mod

    assert browser_mod.needs_no_sandbox() is False
    monkeypatch.setenv("PLAYWRIGHT_NO_SANDBOX", "true")
    assert browser_mod.needs_no_sandbox() is True


@pytest.mark.asyncio
async def test_launch_timeout_wraps_message(monkeypatch):
    monkeypatch.setattr("app.automation.base.browser.running_in_container", lambda: True)
    monkeypatch.setattr("app.core.config.settings.playwright_channel", None)
    browser = BaseBrowser()
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(side_effect=TimeoutError("launch hung"))

    with pytest.raises(RuntimeError, match="no-sandbox"):
        await browser._launch(playwright, headless=True)

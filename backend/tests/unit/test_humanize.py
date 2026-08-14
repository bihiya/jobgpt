"""Human-like typing / mouse helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.automation.humanize import click_locator, humanize_enabled, pause, type_locator, wander_mouse
from app.automation.stealth import STEALTH_INIT_SCRIPT
from app.automation.base.browser import BaseBrowser, chrome_user_agent


def test_humanize_disabled_in_test_env() -> None:
    assert humanize_enabled() is False


def test_stealth_script_covers_headless_leaks() -> None:
    assert "webdriver" in STEALTH_INIT_SCRIPT
    assert "window.chrome" in STEALTH_INIT_SCRIPT
    assert "plugins" in STEALTH_INIT_SCRIPT
    assert "HeadlessChrome" in STEALTH_INIT_SCRIPT


def test_chrome_user_agent_strips_headless_token() -> None:
    ua = chrome_user_agent("148.0.7778.96")
    assert "HeadlessChrome" not in ua
    assert "Chrome/148.0.7778.96" in ua
    assert "Linux" in ua


def test_effective_headless_uses_display(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPLAY", ":1")
    browser = BaseBrowser(headless=True)
    assert browser._effective_headless() is False
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("DISPLAY", "")
    assert browser._effective_headless() is True


@pytest.mark.asyncio
async def test_pause_is_noop_in_tests() -> None:
    inner = MagicMock()
    inner.wait_for_timeout = AsyncMock()
    await pause(inner, 10_000, 20_000)
    inner.wait_for_timeout.assert_not_called()


@pytest.mark.asyncio
async def test_type_locator_uses_press_sequentially_when_humanize_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.automation import humanize as humanize_mod

    monkeypatch.setattr(humanize_mod, "humanize_enabled", lambda: True)
    monkeypatch.setattr(humanize_mod, "pause", AsyncMock())

    calls: list[tuple] = []

    class _Loc:
        async def bounding_box(self):
            return None

        async def click(self, timeout: int = 0) -> None:
            calls.append(("click", timeout))

        async def fill(self, value: str, timeout: int = 0) -> None:
            calls.append(("fill", value))

        async def press_sequentially(self, value: str, delay: int = 0) -> None:
            calls.append(("type", value, delay))

    page = MagicMock()
    page.page = MagicMock()
    page.page.mouse = None
    await type_locator(page, _Loc(), "me@example.com", timeout=2000)
    assert ("fill", "") in calls
    typed = [c for c in calls if c[0] == "type"]
    assert typed and typed[0][1] == "me@example.com"
    assert typed[0][2] >= 42


@pytest.mark.asyncio
async def test_type_locator_fills_when_humanize_off() -> None:
    calls: list[str] = []

    class _Loc:
        async def fill(self, value: str, timeout: int = 0) -> None:
            calls.append(value)

        async def press_sequentially(self, value: str, delay: int = 0) -> None:
            raise AssertionError("should not type key-by-key in tests")

    await type_locator(MagicMock(), _Loc(), "secret")
    assert calls == ["secret"]


@pytest.mark.asyncio
async def test_click_locator_moves_mouse_when_humanize_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.automation import humanize as humanize_mod

    monkeypatch.setattr(humanize_mod, "humanize_enabled", lambda: True)
    monkeypatch.setattr(humanize_mod, "pause", AsyncMock())

    mouse = MagicMock()
    mouse.move = AsyncMock()
    page = MagicMock()
    page.page = MagicMock()
    page.page.mouse = mouse

    class _Loc:
        async def bounding_box(self):
            return {"x": 10, "y": 20, "width": 100, "height": 40}

        async def click(self, timeout: int = 0) -> None:
            return None

    await click_locator(page, _Loc(), timeout=1000)
    mouse.move.assert_awaited()
    args = mouse.move.await_args
    assert args.kwargs.get("steps") or (len(args.args) >= 3)


@pytest.mark.asyncio
async def test_wander_mouse_noop_without_humanize() -> None:
    page = MagicMock()
    page.page = MagicMock()
    page.page.mouse = MagicMock()
    page.page.mouse.move = AsyncMock()
    await wander_mouse(page)
    page.page.mouse.move.assert_not_called()

"""Human-like typing, mouse, and pauses for Playwright locators."""

from __future__ import annotations

import asyncio
import random
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def humanize_enabled() -> bool:
    if settings.app_env == "test":
        return False
    return bool(getattr(settings, "playwright_humanize", True))


def _raw_page(page: Any) -> Any:
    return getattr(page, "page", page)


async def pause(page: Any | None = None, min_ms: int = 250, max_ms: int = 900) -> None:
    """Wait a jittered amount of time. No-op in tests."""
    if not humanize_enabled():
        return
    lo, hi = (min_ms, max_ms) if min_ms <= max_ms else (max_ms, min_ms)
    delay = random.randint(max(0, lo), max(0, hi))
    raw = _raw_page(page) if page is not None else None
    wait = getattr(raw, "wait_for_timeout", None) if raw is not None else None
    try:
        if callable(wait):
            await wait(delay)
            return
    except Exception:  # noqa: BLE001
        pass
    await asyncio.sleep(delay / 1000)


async def wander_mouse(page: Any) -> None:
    if not humanize_enabled():
        return
    raw = _raw_page(page)
    mouse = getattr(raw, "mouse", None)
    if mouse is None:
        return
    try:
        await mouse.move(random.randint(60, 280), random.randint(80, 220), steps=random.randint(6, 14))
        await pause(page, 80, 220)
        await mouse.move(random.randint(420, 980), random.randint(180, 520), steps=random.randint(8, 18))
    except Exception:  # noqa: BLE001
        logger.debug("human_mouse_wander_skipped")


async def click_locator(page: Any, locator: Any, timeout: int = 5000) -> None:
    """Move toward the control, pause, then click (falls back to a plain click)."""
    if humanize_enabled():
        try:
            box = await locator.bounding_box()
            mouse = getattr(_raw_page(page), "mouse", None)
            if box and mouse is not None:
                x = box["x"] + box["width"] * random.uniform(0.28, 0.72)
                y = box["y"] + box["height"] * random.uniform(0.35, 0.68)
                await mouse.move(x, y, steps=random.randint(8, 18))
                await pause(page, 80, 240)
        except Exception:  # noqa: BLE001
            pass
    await locator.click(timeout=timeout)


async def type_locator(page: Any, locator: Any, value: str, timeout: int = 8000) -> None:
    """Click, then type key-by-key so LinkedIn sees InputEvents (not an instant .fill)."""
    if not humanize_enabled():
        await locator.fill(value, timeout=timeout)
        return
    try:
        await click_locator(page, locator, timeout=min(timeout, 4000))
    except Exception:  # noqa: BLE001
        pass
    press = getattr(locator, "press_sequentially", None)
    if callable(press):
        try:
            await locator.fill("", timeout=timeout)
        except Exception:  # noqa: BLE001
            pass
        delay = random.randint(42, 115)
        await press(value, delay=delay)
        return
    await locator.fill(value, timeout=timeout)

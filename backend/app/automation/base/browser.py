"""Base browser factory for Playwright automation."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.automation.stealth import STEALTH_INIT_SCRIPT
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Chromium in Docker/ACA often never returns from launch() without these flags.
_CONTAINER_LAUNCH_ARGS = (
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-gpu",
    "--disable-software-rasterizer",
)
_LAUNCH_TIMEOUT_MS = 45_000
_CONTEXT_TIMEOUT_S = 20.0


def chrome_user_agent(version: str) -> str:
    """Chrome UA without the HeadlessChrome token LinkedIn fingerprints."""
    ver = (version or "").strip() or "148.0.0.0"
    if ver.count(".") == 1:
        ver = f"{ver}.0.0"
    return (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{ver} Safari/537.36"
    )


def running_in_container() -> bool:
    """True on Docker / Kubernetes / Azure Container Apps."""
    if Path("/.dockerenv").exists():
        return True
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return True
    if os.environ.get("CONTAINER_APP_NAME") or os.environ.get("CONTAINER_APP_JOB_NAME"):
        return True
    try:
        return "docker" in Path("/proc/1/cgroup").read_text(errors="ignore")
    except OSError:
        return False


def needs_no_sandbox() -> bool:
    if os.environ.get("PLAYWRIGHT_NO_SANDBOX", "").strip() in {"1", "true", "yes"}:
        return True
    if running_in_container():
        return True
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


class BaseBrowser:
    def __init__(
        self,
        *,
        headless: bool | None = None,
        proxy: dict[str, str] | None = None,
        cookies: list[dict[str, Any]] | None = None,
    ) -> None:
        self.headless = settings.playwright_headless if headless is None else headless
        self.proxy = proxy
        self.cookies = cookies or []
        self.last_cookies: list[dict[str, Any]] = []

    def _effective_headless(self) -> bool:
        if self.headless is False:
            return False
        # Container jobs have no X display worth using; headed mode hangs ACA.
        if running_in_container():
            return True
        prefer = bool(getattr(settings, "playwright_prefer_headed", True))
        display = (os.environ.get("DISPLAY") or "").strip()
        if prefer and display:
            logger.info("browser_headed_via_display", display=display)
            return False
        return True

    def _channel_candidates(self) -> list[str | None]:
        requested = (settings.playwright_channel or "").strip() or None
        if requested:
            return [requested, None]
        # Google Chrome is not installed in the worker image. Trying channel="chrome"
        # first just burns the launch timeout before bundled Chromium starts.
        if running_in_container():
            return [None]
        return ["chrome", None]

    def _launch_args(self, *, headless: bool) -> dict[str, Any]:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1440,900",
        ]
        if needs_no_sandbox():
            args.extend(_CONTAINER_LAUNCH_ARGS)
        launch_args: dict[str, Any] = {
            "headless": headless,
            "args": args,
            "timeout": _LAUNCH_TIMEOUT_MS,
            "ignore_default_args": ["--enable-automation"],
        }
        if self.proxy and self.proxy.get("server"):
            launch_args["proxy"] = self.proxy
        return launch_args

    async def _launch(self, playwright: Any, *, headless: bool) -> Browser:
        launch_args = self._launch_args(headless=headless)
        last_exc: Exception | None = None
        for channel in self._channel_candidates():
            try:
                args = dict(launch_args)
                if channel:
                    args["channel"] = channel
                browser = await asyncio.wait_for(
                    playwright.chromium.launch(**args),
                    timeout=(_LAUNCH_TIMEOUT_MS / 1000) + 5,
                )
                logger.info(
                    "browser_launched",
                    channel=channel or "bundled",
                    headless=headless,
                    no_sandbox=needs_no_sandbox(),
                )
                return browser
            except TimeoutError as exc:
                last_exc = RuntimeError(
                    "Chromium did not start in time. In Docker/Azure this usually means "
                    "the browser is missing --no-sandbox or Playwright browsers are not installed."
                )
                logger.warning(
                    "browser_launch_timeout",
                    channel=channel or "bundled",
                    error=str(exc)[:200],
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(
                    "browser_launch_failed",
                    channel=channel or "bundled",
                    error=str(exc)[:200],
                )
        if last_exc:
            raise last_exc
        raise RuntimeError("Playwright failed to launch Chromium")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
        async with async_playwright() as playwright:
            headless = self._effective_headless()
            browser = await self._launch(playwright, headless=headless)
            context_kwargs: dict[str, Any] = {
                "viewport": {"width": 1440, "height": 900},
                "screen": {"width": 1920, "height": 1080},
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "color_scheme": "light",
                "device_scale_factor": 1,
                "has_touch": False,
                "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
            }
            if headless:
                context_kwargs["user_agent"] = chrome_user_agent(getattr(browser, "version", "") or "")
            context = await asyncio.wait_for(
                browser.new_context(**context_kwargs),
                timeout=_CONTEXT_TIMEOUT_S,
            )
            try:
                await context.add_init_script(STEALTH_INIT_SCRIPT)
            except Exception as exc:  # noqa: BLE001
                logger.warning("stealth_init_failed", error=str(exc)[:200])
            if self.cookies:
                try:
                    await context.add_cookies(self.cookies)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("cookie_inject_failed", error=str(exc))
            page = await asyncio.wait_for(context.new_page(), timeout=_CONTEXT_TIMEOUT_S)
            page.set_default_timeout(30_000)
            page.set_default_navigation_timeout(30_000)
            logger.info(
                "browser_session_started",
                headless=headless,
                cookies=len(self.cookies),
                ua_override=bool(headless),
            )
            try:
                yield browser, context, page
            finally:
                try:
                    self.last_cookies = await context.cookies()
                except Exception:  # noqa: BLE001
                    self.last_cookies = []
                await context.close()
                await browser.close()
                logger.info("browser_session_closed", cookies_exported=len(self.last_cookies))

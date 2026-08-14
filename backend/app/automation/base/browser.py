"""Base browser factory for Playwright automation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Chrome 120 fingerprints as a bot on LinkedIn 2026 login (captcha checkpoint).
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.7258.127 Safari/537.36"
)
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""


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

    async def _launch(self, playwright: Any) -> Browser:
        launch_args: dict[str, Any] = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
            "ignore_default_args": ["--enable-automation"],
        }
        if self.proxy and self.proxy.get("server"):
            launch_args["proxy"] = self.proxy

        channel = (settings.playwright_channel or "").strip() or None
        if channel:
            launch_args["channel"] = channel
            browser = await playwright.chromium.launch(**launch_args)
            logger.info("browser_launched", channel=channel, headless=self.headless)
            return browser

        try:
            browser = await playwright.chromium.launch(**launch_args)
            logger.info("browser_launched", channel="bundled", headless=self.headless)
            return browser
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if "Executable doesn't exist" not in message and "does not support" not in message:
                raise
            # macOS 12+ and fresh installs often lack bundled Chromium; use system Chrome.
            launch_args["channel"] = "chrome"
            browser = await playwright.chromium.launch(**launch_args)
            logger.warning(
                "browser_fallback_channel",
                channel="chrome",
                reason=message[:200],
            )
            return browser

    @asynccontextmanager
    async def session(self) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
        async with async_playwright() as playwright:
            browser = await self._launch(playwright)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=DEFAULT_USER_AGENT,
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
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
            page = await context.new_page()
            logger.info("browser_session_started", headless=self.headless, cookies=len(self.cookies))
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

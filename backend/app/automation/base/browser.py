"""Base browser factory for Playwright automation."""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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

    @asynccontextmanager
    async def session(self) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
        async with async_playwright() as playwright:
            launch_args: dict[str, Any] = {"headless": self.headless}
            if self.proxy and self.proxy.get("server"):
                launch_args["proxy"] = self.proxy

            browser = await playwright.chromium.launch(**launch_args)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            if self.cookies:
                await context.add_cookies(self.cookies)
            page = await context.new_page()
            logger.info("browser_session_started", headless=self.headless)
            try:
                yield browser, context, page
            finally:
                await context.close()
                await browser.close()
                logger.info("browser_session_closed")

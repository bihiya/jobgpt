"""Base page object helpers."""

from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.core.logging import get_logger

logger = get_logger(__name__)


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        await self.page.goto(url, wait_until=wait_until, timeout=30_000)

    async def fill(self, selector: str, value: str) -> None:
        await self.page.fill(selector, value)

    async def click(self, selector: str) -> None:
        await self.page.click(selector)

    async def wait_for(self, selector: str, timeout: int = 15000) -> None:
        await self.page.wait_for_selector(selector, timeout=timeout)

    async def text_content(self, selector: str) -> str:
        content = await self.page.text_content(selector)
        return (content or "").strip()

    async def upload(self, selector: str, file_path: str) -> None:
        await self.page.set_input_files(selector, file_path)

    async def screenshot(self, path: str) -> str:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=path, full_page=True)
        return path

    async def safe_click(self, selector: str, timeout: int = 5000) -> bool:
        try:
            await self.page.click(selector, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            logger.warning("selector_not_found", selector=selector)
            return False

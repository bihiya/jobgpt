"""Portal adapter contract and shared apply flow."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from app.automation.base.browser import BaseBrowser
from app.automation.base.page import BasePage
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedJob:
    external_id: str
    title: str
    company: str
    location: str = ""
    salary: str = ""
    experience: str = ""
    description: str = ""
    skills: list[str] = field(default_factory=list)
    apply_url: str = ""


@dataclass
class ApplyResult:
    success: bool
    screenshot_path: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePortal(ABC):
    name: str = "base"

    def __init__(
        self,
        *,
        credentials: dict[str, str] | None = None,
        cookies: list[dict[str, Any]] | None = None,
        proxy: dict[str, str] | None = None,
        headless: bool | None = None,
        captcha_hook: Any | None = None,
    ) -> None:
        self.credentials = credentials or {}
        self.cookies = cookies or []
        self.proxy = proxy
        if captcha_hook is None:
            from app.automation.captcha import default_captcha_hook

            captcha_hook = default_captcha_hook
        self.captcha_hook = captcha_hook
        self.browser = BaseBrowser(headless=headless, proxy=proxy, cookies=cookies)

    @abstractmethod
    async def login(self, page: BasePage) -> None: ...

    @abstractmethod
    async def search(self, page: BasePage, query: str, location: str = "") -> None: ...

    @abstractmethod
    async def extract_jobs(self, page: BasePage) -> list[ExtractedJob]: ...

    @abstractmethod
    async def apply(self, page: BasePage, job: ExtractedJob, resume_path: str, answers: dict) -> ApplyResult: ...

    async def submit(self, page: BasePage) -> None:
        await page.safe_click("button[type='submit'], button:has-text('Submit'), button:has-text('Apply')")

    async def capture_screenshot(self, page: BasePage, prefix: str = "shot") -> str:
        path = Path(settings.screenshot_dir) / f"{prefix}-{uuid4().hex}.png"
        return await page.screenshot(str(path))

    async def handle_captcha(self, page: BasePage) -> None:
        if self.captcha_hook:
            await self.captcha_hook(page)

    async def fetch_jobs(self, query: str, location: str = "") -> list[ExtractedJob]:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        ):
            with attempt:
                async with self.browser.session() as (_, _, raw_page):
                    page = BasePage(raw_page)
                    await self.login(page)
                    await self.handle_captcha(page)
                    await self.search(page, query, location)
                    jobs = await self.extract_jobs(page)
                    logger.info("jobs_extracted", portal=self.name, count=len(jobs))
                    return jobs
        return []

    async def apply_with_retry(
        self,
        job: ExtractedJob,
        resume_path: str,
        answers: dict | None = None,
    ) -> ApplyResult:
        answers = answers or {}
        last_error = "unknown"
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            reraise=False,
        ):
            with attempt:
                try:
                    async with self.browser.session() as (_, _, raw_page):
                        page = BasePage(raw_page)
                        await self.login(page)
                        result = await self.apply(page, job, resume_path, answers)
                        if not result.screenshot_path:
                            result.screenshot_path = await self.capture_screenshot(
                                page, prefix=f"{self.name}-apply"
                            )
                        return result
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    logger.warning("apply_attempt_failed", portal=self.name, error=last_error)
                    raise
        return ApplyResult(success=False, message=last_error)

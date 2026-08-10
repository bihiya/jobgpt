"""Portal adapter contract and shared apply flow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from tenacity import AsyncRetrying, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from app.automation.base.browser import BaseBrowser
from app.automation.base.page import BasePage
from app.automation.captcha import CaptchaHookResult
from app.automation.errors import PortalAuthError
from app.automation.session_recorder import ApplySessionRecorder
from app.automation.verify import capture_fail_proof
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
    needs_input: bool = False
    unknown_questions: list[str] = field(default_factory=list)
    needs_otp: bool = False
    steps: list[dict[str, Any]] = field(default_factory=list)
    fail_proof_html: str = ""
    fail_proof_path: str = ""
    cookies: list[dict[str, Any]] = field(default_factory=list)
    correlation_id: str = ""


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
        totp_secret: str = "",
        otp_code: str = "",
        selector_version: int = 1,
    ) -> None:
        self.credentials = credentials or {}
        self.cookies = cookies or []
        self.proxy = proxy
        self.totp_secret = totp_secret or ""
        self.otp_code = otp_code or ""
        self.selector_version = selector_version
        if captcha_hook is None:
            from app.automation.captcha import default_captcha_hook

            captcha_hook = default_captcha_hook
        self.captcha_hook = captcha_hook
        self.browser = BaseBrowser(headless=headless, proxy=proxy, cookies=cookies)
        self.recorder = ApplySessionRecorder()

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

    async def handle_captcha(self, page: BasePage) -> CaptchaHookResult:
        if not self.captcha_hook:
            return CaptchaHookResult()
        result = await self.captcha_hook(
            page,
            {"totp_secret": self.totp_secret, "otp_code": self.otp_code},
        )
        if isinstance(result, CaptchaHookResult):
            if result.captcha_solved or result.detail:
                self.recorder.captcha(result.captcha_solved, result.detail)
            if result.otp_handled or result.needs_otp:
                self.recorder.otp(result.otp_handled, result.detail)
            return result
        return CaptchaHookResult()

    def _credentials_required(self) -> bool:
        """True when the adapter was given username/password and must authenticate."""
        return bool(self.credentials.get("username") or self.credentials.get("password"))

    async def fetch_jobs(self, query: str, location: str = "") -> list[ExtractedJob]:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_not_exception_type(PortalAuthError),
            reraise=True,
        ):
            with attempt:
                async with self.browser.session() as (_, _, raw_page):
                    page = BasePage(raw_page)
                    await self.login(page)
                    captcha = await self.handle_captcha(page)
                    if captcha.needs_otp:
                        raise PortalAuthError(
                            captcha.detail or "Portal requires OTP / 2FA before fetch can continue",
                            code="OTP_REQUIRED",
                        )
                    if "captcha_unsolved" in (captcha.detail or ""):
                        raise PortalAuthError(
                            "CAPTCHA unsolved — cannot continue authenticated fetch",
                            code="CAPTCHA",
                        )
                    if self._credentials_required():
                        from app.automation.auth import ensure_logged_in

                        live_cookies = await page.page.context.cookies()
                        await ensure_logged_in(
                            page,
                            portal=self.name,
                            cookies=live_cookies,
                            selector_version=self.selector_version,
                        )
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
        self.recorder = ApplySessionRecorder()
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
                        captcha = await self.handle_captcha(page)
                        if captcha.needs_otp:
                            proof = await capture_fail_proof(page, prefix=f"{self.name}-otp")
                            result = ApplyResult(
                                success=False,
                                needs_otp=True,
                                message="Portal requires OTP / 2FA from you",
                                screenshot_path=proof["screenshot_path"],
                                fail_proof_html=proof["html"],
                                fail_proof_path=proof["html_path"],
                                steps=self.recorder.to_list(),
                                correlation_id=self.recorder.correlation_id,
                                cookies=list(self.browser.last_cookies),
                            )
                            return result

                        result = await self.apply(page, job, resume_path, answers)
                        result.steps = result.steps or self.recorder.to_list()
                        result.correlation_id = self.recorder.correlation_id
                        result.cookies = list(self.browser.last_cookies)

                        if result.needs_input or result.needs_otp:
                            if not result.screenshot_path:
                                proof = await capture_fail_proof(page, prefix=f"{self.name}-pause")
                                result.screenshot_path = proof["screenshot_path"]
                                result.fail_proof_html = proof["html"]
                                result.fail_proof_path = proof["html_path"]
                            return result

                        if not result.screenshot_path:
                            result.screenshot_path = await self.capture_screenshot(
                                page, prefix=f"{self.name}-apply"
                            )
                        return result
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    self.recorder.failed(last_error)
                    logger.warning("apply_attempt_failed", portal=self.name, error=last_error)
                    raise
        return ApplyResult(
            success=False,
            message=last_error,
            steps=self.recorder.to_list(),
            correlation_id=self.recorder.correlation_id,
            cookies=list(self.browser.last_cookies),
        )

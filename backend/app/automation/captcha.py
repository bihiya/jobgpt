"""Captcha / 2FA provider hooks for Playwright portals."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.automation.base.page import BasePage
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CaptchaProvider(ABC):
    @abstractmethod
    async def solve(self, page: BasePage, site_key: str = "", page_url: str = "") -> str: ...

    @abstractmethod
    async def handle_2fa(self, page: BasePage, hint: str = "") -> bool: ...


class NoopCaptchaProvider(CaptchaProvider):
    async def solve(self, page: BasePage, site_key: str = "", page_url: str = "") -> str:
        logger.info("captcha_noop", url=page_url or page.page.url)
        return ""

    async def handle_2fa(self, page: BasePage, hint: str = "") -> bool:
        logger.info("2fa_noop", hint=hint)
        return False


class TwoCaptchaProvider(CaptchaProvider):
    """Example integration with a 2captcha-like API."""

    async def solve(self, page: BasePage, site_key: str = "", page_url: str = "") -> str:
        if not settings.captcha_api_key:
            return await NoopCaptchaProvider().solve(page, site_key, page_url)
        async with httpx.AsyncClient(timeout=60) as client:
            # Placeholder protocol — swap for real provider endpoints
            resp = await client.post(
                settings.captcha_api_url,
                json={
                    "clientKey": settings.captcha_api_key,
                    "task": {
                        "type": "RecaptchaV2TaskProxyless",
                        "websiteURL": page_url or page.page.url,
                        "websiteKey": site_key,
                    },
                },
            )
            data = resp.json()
            token = data.get("solution", {}).get("gRecaptchaResponse", "")
            if token:
                await page.page.evaluate(
                    "(token) => { const el = document.querySelector('[name=\"g-recaptcha-response\"]'); if (el) el.value = token; }",
                    token,
                )
            return token

    async def handle_2fa(self, page: BasePage, hint: str = "") -> bool:
        # Hook for TOTP / email code injection via settings or external vault
        code = settings.totp_test_code
        if not code:
            return False
        if await page.page.query_selector("input[name*='otp'], input[name*='code'], input[autocomplete='one-time-code']"):
            await page.fill(
                "input[name*='otp'], input[name*='code'], input[autocomplete='one-time-code']",
                code,
            )
            await page.safe_click("button[type='submit']")
            return True
        return False


def get_captcha_provider() -> CaptchaProvider:
    provider = (settings.captcha_provider or "noop").lower()
    if provider in {"2captcha", "anticaptcha", "capsolver"}:
        return TwoCaptchaProvider()
    return NoopCaptchaProvider()


async def default_captcha_hook(page: BasePage, context: dict[str, Any] | None = None) -> None:
    context = context or {}
    provider = get_captcha_provider()
    # Detect common captcha widgets
    site_key = ""
    frame = await page.page.query_selector("[data-sitekey], .g-recaptcha")
    if frame:
        site_key = (await frame.get_attribute("data-sitekey")) or ""
        await provider.solve(page, site_key=site_key, page_url=page.page.url)
    # Detect 2FA
    if await page.page.query_selector("input[name*='otp'], input[name*='code']"):
        await provider.handle_2fa(page)

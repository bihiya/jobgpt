"""Captcha / 2FA provider hooks for Playwright portals."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.automation.base.page import BasePage
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CaptchaHookResult:
    captcha_solved: bool = False
    otp_handled: bool = False
    needs_otp: bool = False
    detail: str = ""


class CaptchaProvider(ABC):
    @abstractmethod
    async def solve(self, page: BasePage, site_key: str = "", page_url: str = "") -> str: ...

    @abstractmethod
    async def handle_2fa(
        self,
        page: BasePage,
        hint: str = "",
        totp_secret: str = "",
        otp_code: str = "",
    ) -> bool: ...


def _generate_totp(secret: str = "", one_shot_code: str = "") -> str:
    if one_shot_code:
        return str(one_shot_code).strip()
    secret = (secret or "").strip().replace(" ", "")
    if not secret:
        return settings.totp_test_code or ""
    try:
        import pyotp

        return pyotp.TOTP(secret).now()
    except Exception as exc:  # noqa: BLE001
        logger.warning("totp_generate_failed", error=str(exc))
        return settings.totp_test_code or ""


class NoopCaptchaProvider(CaptchaProvider):
    async def solve(self, page: BasePage, site_key: str = "", page_url: str = "") -> str:
        logger.info("captcha_noop", url=page_url or page.page.url)
        return ""

    async def handle_2fa(
        self,
        page: BasePage,
        hint: str = "",
        totp_secret: str = "",
        otp_code: str = "",
    ) -> bool:
        code = _generate_totp(totp_secret, one_shot_code=otp_code)
        if not code:
            logger.info("2fa_noop", hint=hint)
            return False
        return await _fill_otp(page, code)


class TwoCaptchaProvider(CaptchaProvider):
    """2Captcha / AntiCaptcha-compatible createTask + getTaskResult poll loop."""

    async def solve(self, page: BasePage, site_key: str = "", page_url: str = "") -> str:
        if not settings.captcha_api_key or not site_key:
            return await NoopCaptchaProvider().solve(page, site_key, page_url)

        create_url = settings.captcha_api_url
        result_url = settings.captcha_result_url
        async with httpx.AsyncClient(timeout=90) as client:
            create = await client.post(
                create_url,
                json={
                    "clientKey": settings.captcha_api_key,
                    "task": {
                        "type": "RecaptchaV2TaskProxyless",
                        "websiteURL": page_url or page.page.url,
                        "websiteKey": site_key,
                    },
                },
            )
            created = create.json()
            task_id = created.get("taskId")
            if created.get("errorId") and not task_id:
                logger.warning("captcha_create_failed", response=created)
                return ""

            token = ""
            for _ in range(int(settings.captcha_poll_attempts)):
                await asyncio.sleep(float(settings.captcha_poll_interval_seconds))
                poll = await client.post(
                    result_url,
                    json={"clientKey": settings.captcha_api_key, "taskId": task_id},
                )
                data = poll.json()
                status = data.get("status")
                if status == "ready":
                    token = (
                        data.get("solution", {}).get("gRecaptchaResponse")
                        or data.get("solution", {}).get("token")
                        or ""
                    )
                    break
                if data.get("errorId"):
                    logger.warning("captcha_poll_error", response=data)
                    break

            if token:
                await page.page.evaluate(
                    """(token) => {
                        const el = document.querySelector('[name="g-recaptcha-response"]');
                        if (el) { el.value = token; el.innerHTML = token; }
                        if (typeof ___grecaptcha_cfg !== 'undefined') {
                          try { window.___grecaptcha_cfg.clients && Object.values(window.___grecaptcha_cfg.clients); } catch (e) {}
                        }
                    }""",
                    token,
                )
                logger.info("captcha_solved", url=page_url or page.page.url)
            return token

    async def handle_2fa(
        self,
        page: BasePage,
        hint: str = "",
        totp_secret: str = "",
        otp_code: str = "",
    ) -> bool:
        code = _generate_totp(totp_secret, one_shot_code=otp_code)
        if not code:
            return False
        return await _fill_otp(page, code)


_OTP_SELECTORS = [
    "input[name*='otp']",
    "input[name*='code']",
    "input[name*='pin']",
    "input[autocomplete='one-time-code']",
    "input#input__email_verification_pin",
    "input[data-automation-id='otpToken']",
    "input[data-automation-id='otp']",
    "input[data-automation-id='emailVerificationPin']",
    "input[data-automation-id='verificationCode']",
    "input[aria-label*='verification']",
    "input[aria-label*='one-time']",
]


async def _fill_otp(page: BasePage, code: str) -> bool:
    selectors = list(_OTP_SELECTORS)
    for sel in selectors:
        if await page.page.query_selector(sel):
            await page.fill(sel, code)
            await page.safe_click(
                "button[type='submit'], button:has-text('Submit'), button:has-text('Verify'), "
                "button[data-automation-id='verifyButton']"
            )
            return True
    return False


def get_captcha_provider() -> CaptchaProvider:
    provider = (settings.captcha_provider or "noop").lower()
    if provider in {"2captcha", "anticaptcha", "capsolver"}:
        return TwoCaptchaProvider()
    return NoopCaptchaProvider()


async def default_captcha_hook(
    page: BasePage,
    context: dict[str, Any] | None = None,
) -> CaptchaHookResult:
    context = context or {}
    provider = get_captcha_provider()
    result = CaptchaHookResult()

    site_key = ""
    frame = await page.page.query_selector("[data-sitekey], .g-recaptcha, iframe[src*='recaptcha']")
    if frame:
        site_key = (await frame.get_attribute("data-sitekey")) or ""
        if not site_key:
            src = (await frame.get_attribute("src")) or ""
            if "k=" in src:
                site_key = src.split("k=")[-1].split("&")[0]
        token = await provider.solve(page, site_key=site_key, page_url=page.page.url)
        result.captcha_solved = bool(token)
        result.detail = "captcha_solved" if token else "captcha_unsolved"

    otp_sel = await page.page.query_selector(", ".join(_OTP_SELECTORS))
    if otp_sel:
        handled = await provider.handle_2fa(
            page,
            totp_secret=str(context.get("totp_secret") or ""),
            otp_code=str(context.get("otp_code") or ""),
        )
        result.otp_handled = handled
        result.needs_otp = not handled
        result.detail = (result.detail + "; " if result.detail else "") + (
            "otp_filled" if handled else "needs_otp"
        )
    return result

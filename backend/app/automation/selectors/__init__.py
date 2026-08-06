"""Versioned portal selector packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.automation.base.page import BasePage

logger = get_logger(__name__)


@dataclass(frozen=True)
class SelectorPack:
    portal: str
    version: int
    selectors: dict[str, list[str]] = field(default_factory=dict)

    def all(self, key: str) -> list[str]:
        return list(self.selectors.get(key, []))

    def primary(self, key: str) -> str:
        items = self.all(key)
        return items[0] if items else ""


LINKEDIN_V1 = SelectorPack(
    portal="linkedin",
    version=1,
    selectors={
        "login_user": ["#username", "input[name='session_key']"],
        "login_pass": ["#password", "input[name='session_password']"],
        "login_submit": ["button[type='submit']", "button.btn__primary--large"],
        "logged_in": [
            "img.global-nav__me-photo",
            ".global-nav__me",
            "a[href*='/feed']",
        ],
        "easy_apply": [
            "button.jobs-apply-button",
            "button:has-text('Easy Apply')",
            "button:has-text('Apply')",
        ],
        "file_input": ["input[type='file']"],
        "next": [
            "button:has-text('Next')",
            "button[aria-label='Continue to next step']",
            "button:has-text('Review')",
        ],
        "submit": [
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
            "button[aria-label='Submit application']",
        ],
        "success": [
            "text=Application sent",
            "text=Your application was sent",
            "h2:has-text('Application sent')",
            "[data-test-modal] h2:has-text('sent')",
        ],
        "otp": [
            "input[name*='pin']",
            "input[name*='otp']",
            "input[autocomplete='one-time-code']",
            "input#input__email_verification_pin",
        ],
        "job_cards": [".jobs-search-results__list-item", ".job-card-container"],
    },
)

INDEED_V1 = SelectorPack(
    portal="indeed",
    version=1,
    selectors={
        "login_user": ["input[type='email']", "#ifl-InputFormField-3"],
        "login_pass": ["input[type='password']", "input[name='password']"],
        "login_submit": ["button[type='submit']", "button:has-text('Sign in')"],
        "logged_in": ["a[href*='/account']", "[data-gnav-element-name='AccountMenu']"],
        "apply": [
            "button:has-text('Apply now')",
            "a:has-text('Apply now')",
            "button.ia-IndeedApplyButton",
        ],
        "file_input": ["input[type='file']"],
        "submit": [
            "button:has-text('Submit')",
            "button[type='submit']",
            "button:has-text('Continue')",
        ],
        "success": [
            "text=Application submitted",
            "text=Your application has been submitted",
            "h1:has-text('Application submitted')",
        ],
        "otp": [
            "input[name*='otp']",
            "input[name*='code']",
            "input[autocomplete='one-time-code']",
        ],
        "job_cards": [".job_seen_beacon", ".resultContent", ".jobsearch-ResultsList li"],
    },
)

GREENHOUSE_V1 = SelectorPack(
    portal="greenhouse",
    version=1,
    selectors={
        "job_links": ["a[href*='/jobs/']", "#main a[href*='jobs']"],
        "file_input": ["input[type='file']", "#resume"],
        "submit": [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit Application')",
        ],
        "success": [
            "text=Thank you for applying",
            "text=Application submitted",
            "#flash_success",
            ".application-confirmation",
        ],
        "form_fields": ["form input, form textarea, form select"],
    },
)

LEVER_V1 = SelectorPack(
    portal="lever",
    version=1,
    selectors={
        "job_cards": [".posting", "a.posting-title", ".posting-title"],
        "file_input": ["input[type='file']", "input[name='resume']"],
        "submit": [
            "button[type='submit']",
            "button:has-text('Submit application')",
            "#btn-submit",
        ],
        "success": [
            "text=Application submitted",
            "text=Thank you for applying",
            ".application-confirmation",
            "h3:has-text('Application submitted')",
        ],
        "form_fields": ["form input, form textarea, form select"],
    },
)

PACKS: dict[str, SelectorPack] = {
    "linkedin": LINKEDIN_V1,
    "indeed": INDEED_V1,
    "greenhouse": GREENHOUSE_V1,
    "lever": LEVER_V1,
}


def get_selector_pack(portal: str, version: int | None = None) -> SelectorPack:
    pack = PACKS.get((portal or "").lower())
    if not pack:
        return SelectorPack(portal=portal or "generic", version=0, selectors={})
    if version is not None and version != pack.version:
        logger.warning(
            "selector_version_mismatch",
            portal=portal,
            requested=version,
            current=pack.version,
        )
    return pack


async def click_first(page: "BasePage", selectors: list[str], timeout: int = 5000) -> str | None:
    for sel in selectors:
        if await page.safe_click(sel, timeout=timeout):
            return sel
    return None


async def fill_first(page: "BasePage", selectors: list[str], value: str) -> str | None:
    for sel in selectors:
        try:
            if await page.page.query_selector(sel):
                await page.fill(sel, value)
                return sel
        except Exception:  # noqa: BLE001
            continue
    return None


async def query_first(page: "BasePage", selectors: list[str]) -> Any:
    for sel in selectors:
        el = await page.page.query_selector(sel)
        if el:
            return el
    return None


async def any_visible(page: "BasePage", selectors: list[str]) -> bool:
    return bool(await query_first(page, selectors))

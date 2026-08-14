"""Versioned portal selector packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.automation.humanize import click_locator, type_locator
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
        # LinkedIn 2025+ uses generated ids; keep classic #username plus type/autocomplete.
        "login_user": [
            "#username",
            "input[name='session_key']",
            "input#session_key",
            "input[autocomplete='username']",
            "input[autocomplete='username webauthn']",
            "input[id*='username']",
            "input[id*='email']",
            "input[type='email']",
            "input[inputmode='email']",
            "input[aria-label*='Email']",
            "input[placeholder*='Email']",
            "input[name='email']",
            "form.login__form input[type='text']",
            "form.login__form input:not([type='hidden']):not([type='password']):not([type='checkbox'])",
            "#organic-div input[type='text']",
        ],
        "login_pass": [
            "#password",
            "input[name='session_password']",
            "input#session_password",
            "input[autocomplete='current-password']",
            "input[type='password']",
        ],
        "login_submit": [
            "button[data-litms-control-urn='login-submit']",
            "button[type='submit']",
            "button.btn__primary--large",
            # :has-text('Sign in') also matches "Sign in with Apple" (and :text-is misses nested spans).
            "button:has-text('Sign in'):not(:has-text('Apple')):not(:has-text('Google'))",
            "button >> text='Sign in'",
            "button:has-text('Continue')",
            "input[type='submit']",
        ],
        # Strong signals only — a[href*='/feed'] appears on marketing/login pages.
        "logged_in": [
            "img.global-nav__me-photo",
            ".global-nav__me",
            "button.global-nav__primary-link-me-menu-trigger",
            "[data-global-nav-link='me']",
        ],
        "login_error": [
            "#error-for-password",
            "#error-for-username",
            "form .form__label--error",
            "text=Wrong email or password",
            "text=Hmm, that's not the right password",
            "text=Couldn't find a LinkedIn account",
        ],
        "checkpoint": [
            "input#input__email_verification_pin",
            "text=Let's do a quick security check",
            "text=security verification",
            "text=Verify your identity",
            "#captcha-challenge",
            ".challenge-dialog",
        ],
        "captcha": [
            "#captcha-challenge",
            "iframe[src*='captcha']",
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "[data-sitekey]",
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
        # Avoid loose a[href*='/account'] — present on guest/marketing pages.
        "logged_in": [
            "[data-gnav-element-name='AccountMenu']",
            "#gnav-header-account-menu",
            "a[href*='/secure/account']",
            "button[aria-label*='Account']",
        ],
        "login_error": [
            "text=Invalid email or password",
            "text=incorrect password",
            "text=We don't recognize this email",
            "[data-testid='login-error']",
            ".ssl-error",
        ],
        "checkpoint": [
            "text=Verify your identity",
            "text=security check",
            "text=Confirm it's you",
            "#challenge",
        ],
        "captcha": [
            "iframe[src*='captcha']",
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "[data-sitekey]",
            "#captcha",
        ],
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
        try:
            locator = page.page.locator(sel)
            count = await locator.count()
            if int(count) == 0:
                continue
            for idx in range(count):
                item = locator.nth(idx)
                try:
                    if not await item.is_visible():
                        continue
                    await click_locator(page, item, timeout=timeout)
                    return sel
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass
        if ":has-text(" in sel or sel.startswith("text=") or " >> " in sel:
            if await page.safe_click(sel, timeout=min(1500, timeout)):
                return sel
    return None


async def click_if_present(page: "BasePage", selectors: list[str]) -> str | None:
    """Click the first visible match. Supports Playwright :has-text() (query_selector cannot)."""
    for sel in selectors:
        try:
            locator = page.page.locator(sel)
            count = await locator.count()
            for idx in range(int(count)):
                item = locator.nth(idx)
                try:
                    if not await item.is_visible():
                        continue
                    await item.click(timeout=1500)
                    return sel
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            continue
    return None


def _css_join(selectors: list[str]) -> str:
    return ", ".join(
        sel
        for sel in selectors
        if not sel.startswith("text=")
        and ":has-text(" not in sel
        and ":text-is(" not in sel
        and " >> " not in sel
    )


async def wait_any_selector(
    page: "BasePage",
    selectors: list[str],
    timeout: int = 15000,
    *,
    state: str = "visible",
) -> str | None:
    """Wait until any selector appears (including in child frames).

    Prefer *visible* locators. LinkedIn 2026 duplicates email/password as hidden
    inputs with generated ids; query_selector would otherwise return the hidden one.
    """
    if not selectors:
        return None

    async def _first_locator_match() -> str | None:
        for sel in selectors:
            try:
                loc = page.page.locator(sel)
                if state == "visible":
                    loc = loc.locator("visible=true")
                if int(await loc.count()) > 0:
                    return sel
            except Exception:  # noqa: BLE001
                continue
        return None

    found = await _first_locator_match()
    if found:
        return found

    css = _css_join(selectors)
    if css:
        try:
            await page.page.wait_for_selector(css, timeout=timeout, state=state)
        except Exception:  # noqa: BLE001
            pass
        found = await _first_locator_match()
        if found:
            return found
        for sel in selectors:
            try:
                el = await page.page.query_selector(sel)
                if el:
                    return sel
            except Exception:  # noqa: BLE001
                continue
    for sel in selectors:
        try:
            await page.page.wait_for_selector(sel, timeout=min(2500, timeout), state=state)
            return sel
        except Exception:  # noqa: BLE001
            continue
    frames = getattr(page.page, "frames", None) or []
    for frame in frames:
        wait = getattr(frame, "wait_for_selector", None)
        query = getattr(frame, "query_selector", None)
        if css and callable(wait):
            try:
                await wait(css, timeout=min(4000, timeout), state=state)
            except Exception:  # noqa: BLE001
                pass
        if not callable(query):
            continue
        for sel in selectors:
            try:
                el = await query(sel)
                if el:
                    return sel
            except Exception:  # noqa: BLE001
                continue
    return None


async def fill_first(page: "BasePage", selectors: list[str], value: str, timeout: int = 8000) -> str | None:
    """Fill the first *visible* matching input (LinkedIn duplicates hidden fields)."""
    for sel in selectors:
        try:
            locator = page.page.locator(sel)
            count = await locator.count()
            for idx in range(int(count)):
                item = locator.nth(idx)
                try:
                    if not await item.is_visible():
                        continue
                    await type_locator(page, item, value, timeout=timeout)
                    return sel
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            continue
    sel = await wait_any_selector(page, selectors, timeout=timeout)
    if not sel:
        return None
    try:
        await page.fill(sel, value)
        return sel
    except Exception:  # noqa: BLE001
        logger.warning("fill_failed", selector=sel)
        return None


async def query_first(page: "BasePage", selectors: list[str]) -> Any:
    for sel in selectors:
        try:
            locator = page.page.locator(sel)
            count = await locator.count()
            for idx in range(count):
                item = locator.nth(idx)
                try:
                    if await item.is_visible():
                        return await item.element_handle()
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass
        el = await page.page.query_selector(sel)
        if el:
            return el
    return None


async def any_visible(page: "BasePage", selectors: list[str]) -> bool:
    return bool(await query_first(page, selectors))

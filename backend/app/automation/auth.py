"""Shared portal login verification helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.automation.base.page import BasePage
from app.automation.errors import PortalAuthError
from app.automation.selectors import any_visible, get_selector_pack
from app.services.session_vault import AUTH_COOKIE_NAMES, has_auth_cookies

# Stable auth failure codes used by adapters + health / UI.
WRONG_PASSWORD = "WRONG_PASSWORD"
CHECKPOINT = "CHECKPOINT"
CAPTCHA = "CAPTCHA"
OTP_REQUIRED = "OTP_REQUIRED"
NOT_LOGGED_IN = "NOT_LOGGED_IN"
LOGIN_FAILED = "LOGIN_FAILED"


def _url_looks_like_checkpoint(url: str) -> bool:
    hay = (url or "").lower()
    try:
        path = (urlparse(url).path or "").lower()
    except Exception:  # noqa: BLE001
        path = hay
    markers = (
        "/checkpoint/",
        "/challenge/",
        "/login-submit",
        "/authwall",
        "/account/verify",
        "/account/challenge",
        "security-check",
        "captcha",
    )
    return any(m in path or m in hay for m in markers)


def requires_auth_cookies(portal: str) -> bool:
    return (portal or "").lower() in AUTH_COOKIE_NAMES


async def detect_auth_failure(
    page: BasePage,
    portal: str,
    *,
    selector_version: int = 1,
) -> PortalAuthError | None:
    """Inspect page for wrong-password / checkpoint / captcha / OTP interstitials."""
    pack = get_selector_pack(portal, selector_version)
    url = page.page.url or ""

    if await any_visible(page, pack.all("login_error")):
        return PortalAuthError(
            "Wrong email or password — check credentials and try again",
            code=WRONG_PASSWORD,
        )
    if await any_visible(page, pack.all("checkpoint")) or _url_looks_like_checkpoint(url):
        return PortalAuthError(
            "Portal security checkpoint / challenge required — complete it in a browser, then re-auth",
            code=CHECKPOINT,
        )
    if await any_visible(page, pack.all("captcha")):
        return PortalAuthError(
            "CAPTCHA challenge blocking login — solve it or re-auth with a fresh session",
            code=CAPTCHA,
        )
    if await any_visible(page, pack.all("otp")):
        return PortalAuthError(
            "OTP / 2FA required — add a TOTP secret or enter a one-time code, then re-auth",
            code=OTP_REQUIRED,
        )
    return None


async def ensure_logged_in(
    page: BasePage,
    *,
    portal: str,
    cookies: list[dict[str, Any]] | None = None,
    selector_version: int = 1,
) -> list[dict[str, Any]]:
    """
    Assert the browser session is authenticated.

    Returns the cookie list used for the check. Raises PortalAuthError on soft-fail.
    """
    pack = get_selector_pack(portal, selector_version)
    if cookies is None:
        try:
            cookies = await page.page.context.cookies()
        except Exception:  # noqa: BLE001
            cookies = []

    failure = await detect_auth_failure(page, portal, selector_version=selector_version)
    if failure:
        raise failure

    cookie_ok = has_auth_cookies(portal, cookies)
    logged_in_ui = await any_visible(page, pack.all("logged_in"))

    if requires_auth_cookies(portal):
        # Auth cookie is the source of truth — loose nav links alone are not enough.
        if cookie_ok:
            return cookies
        still_on_login = await any_visible(
            page,
            pack.all("login_user") + pack.all("login_pass") + ["#username", "input[type='password']"],
        )
        if still_on_login:
            raise PortalAuthError(
                "Login rejected — still on sign-in page (wrong password or blocked)",
                code=WRONG_PASSWORD,
            )
        raise PortalAuthError(
            f"Not logged in to {portal} — missing authenticated session cookie",
            code=NOT_LOGGED_IN,
        )

    if logged_in_ui or cookie_ok:
        return cookies

    raise PortalAuthError(
        f"Not logged in to {portal} — session invalid or credentials rejected",
        code=NOT_LOGGED_IN,
    )

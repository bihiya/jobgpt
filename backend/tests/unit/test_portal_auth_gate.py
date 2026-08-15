"""Auth gate: fake credentials must not look healthy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.automation.auth import WRONG_PASSWORD, detect_auth_failure, ensure_logged_in
from app.automation.errors import PortalAuthError
from app.automation.selectors import get_selector_pack
from app.services.session_vault import (
    AUTH_COOKIE_NAMES,
    has_auth_cookies,
    normalize_cookies,
)


def test_linkedin_requires_li_at():
    assert "li_at" in AUTH_COOKIE_NAMES["linkedin"]
    assert has_auth_cookies("linkedin", [{"name": "li_at", "value": "tok"}])
    assert not has_auth_cookies(
        "linkedin",
        [{"name": "bcookie", "value": "anon"}, {"name": "lang", "value": "v=2"}],
    )


def test_indeed_requires_account_cookies():
    assert has_auth_cookies("indeed", [{"name": "PP", "value": "1"}])
    assert not has_auth_cookies("indeed", [{"name": "CTK", "value": "track"}])


def test_logged_in_selectors_are_tight():
    li = get_selector_pack("linkedin")
    assert "a[href*='/feed']" not in li.all("logged_in")
    assert "Start a post" in " ".join(li.all("logged_in"))
    assert li.all("login_error")
    assert li.all("checkpoint")
    assert li.all("captcha")

    ind = get_selector_pack("indeed")
    assert "a[href*='/account']" not in ind.all("logged_in")
    assert "[data-gnav-element-name='AccountMenu']" in ind.all("logged_in")
    assert ind.all("login_error")


def _fake_page(*, url: str = "https://www.linkedin.com/feed/", visible: set[str] | None = None):
    visible = visible or set()
    page = MagicMock()
    page.page = MagicMock()
    page.page.url = url

    async def query_selector(sel: str):
        return object() if sel in visible else None

    page.page.query_selector = AsyncMock(side_effect=query_selector)
    page.page.context.cookies = AsyncMock(return_value=[])
    page.page.title = MagicMock(return_value="LinkedIn")
    page.page.inner_text = AsyncMock(return_value="")
    return page


@pytest.mark.asyncio
async def test_detect_wrong_password():
    page = _fake_page(
        url="https://www.linkedin.com/login",
        visible={"#error-for-password"},
    )
    err = await detect_auth_failure(page, "linkedin")
    assert err is not None
    assert err.code == WRONG_PASSWORD


@pytest.mark.asyncio
async def test_detect_wrong_password_from_body_text():
    page = _fake_page(url="https://www.linkedin.com/login")
    page.page.inner_text = AsyncMock(return_value="Hmm, that's not the right password. Try again.")
    err = await detect_auth_failure(page, "linkedin")
    assert err is not None
    assert err.code == WRONG_PASSWORD
    assert "Wrong email or password" in err.message
    assert "/login" in err.message


@pytest.mark.asyncio
async def test_ensure_logged_in_rejects_anonymous_cookies():
    page = _fake_page(
        url="https://www.linkedin.com/login",
        visible={"#username", "input[type='password']"},
    )
    with pytest.raises(PortalAuthError) as exc:
        await ensure_logged_in(
            page,
            portal="linkedin",
            cookies=[{"name": "bcookie", "value": "anon"}],
        )
    assert exc.value.code in {"WRONG_PASSWORD", "NOT_LOGGED_IN"}


@pytest.mark.asyncio
async def test_ensure_logged_in_accepts_li_at():
    page = _fake_page(url="https://www.linkedin.com/feed/")
    cookies = await ensure_logged_in(
        page,
        portal="linkedin",
        cookies=[{"name": "li_at", "value": "real-session"}],
    )
    assert any(c["name"] == "li_at" for c in cookies)


@pytest.mark.asyncio
async def test_fetch_jobs_raises_on_unsolved_captcha():
    from app.automation.base.portal import BasePortal
    from app.automation.captcha import CaptchaHookResult

    class StubPortal(BasePortal):
        name = "linkedin"

        async def login(self, page):
            return None

        async def search(self, page, query, location=""):
            return None

        async def extract_jobs(self, page):
            return []

        async def apply(self, page, job, resume_path, answers):
            raise NotImplementedError

    portal = StubPortal(credentials={"username": "u", "password": "p"})
    portal.handle_captcha = AsyncMock(
        return_value=CaptchaHookResult(detail="captcha_unsolved")
    )

    class _Ctx:
        async def __aenter__(self):
            raw = MagicMock()
            raw.context.cookies = AsyncMock(return_value=[])
            return (None, None, raw)

        async def __aexit__(self, *args):
            return False

    portal.browser.session = MagicMock(return_value=_Ctx())
    with pytest.raises(PortalAuthError) as exc:
        await portal.fetch_jobs("engineer")
    assert exc.value.code == "CAPTCHA"


def test_portal_service_has_session_requires_auth_cookies():
    from app.services.portal_service import PortalService
    from app.services.session_vault import SessionVault, encrypt_blob

    vault = SessionVault()
    portal = SimpleNamespace(
        id="p1",
        name=SimpleNamespace(value="linkedin"),
        status="connected",
        last_sync_at=None,
        sync_started_at=None,
        created_at=__import__("datetime").datetime.utcnow(),
        credentials=SimpleNamespace(username="u"),
        cookies={},
        session_blob="",
        totp_secret_encrypted="",
        session_updated_at=None,
        selector_version=1,
        health=SimpleNamespace(
            model_dump=lambda: {
                "score": 100,
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_error": "",
                "auto_paused": False,
                "paused_reason": "",
            }
        ),
    )

    # Anonymous cookies must not count as a session.
    portal.cookies = {
        "cookies": normalize_cookies([{"name": "bcookie", "value": "x", "domain": ".linkedin.com"}])
    }
    portal.session_blob = encrypt_blob(portal.cookies["cookies"])
    assert PortalService._has_auth_session(portal) is False

    portal.cookies = {
        "cookies": normalize_cookies([{"name": "li_at", "value": "tok", "domain": ".linkedin.com"}])
    }
    portal.session_blob = encrypt_blob(portal.cookies["cookies"])
    assert PortalService._has_auth_session(portal) is True
    _ = vault


@pytest.mark.asyncio
async def test_describe_page_and_format_landed():
    from app.automation.auth import describe_page, format_landed

    page = _fake_page(url="https://www.linkedin.com/checkpoint/challenge/abc")
    page.page.title = MagicMock(return_value="Security Verification")
    snap = await describe_page(page)
    assert snap["url"].endswith("/checkpoint/challenge/abc")
    assert snap["title"] == "Security Verification"
    assert "Security Verification" in format_landed(snap)
    assert "checkpoint" in format_landed(snap)


@pytest.mark.asyncio
async def test_describe_page_ignores_magicmock_title():
    from app.automation.auth import describe_page

    page = _fake_page(url="https://www.linkedin.com/login")
    page.page.title = MagicMock()  # return_value is another MagicMock
    snap = await describe_page(page)
    assert snap["url"].endswith("/login")
    assert snap["title"] == ""


@pytest.mark.asyncio
async def test_detect_checkpoint_from_security_check_copy():
    from app.automation.auth import CHECKPOINT

    page = _fake_page(url="https://www.linkedin.com/login")
    page.page.inner_text = AsyncMock(
        return_value="Sign in Join now\nLet’s do a quick security check\nLinkedIn © 2026"
    )
    err = await detect_auth_failure(page, "linkedin")
    assert err is not None
    assert err.code == CHECKPOINT
    assert "normal browser" in err.message


@pytest.mark.asyncio
async def test_detect_checkpoint_includes_landed_url():
    from app.automation.auth import CHECKPOINT

    page = _fake_page(url="https://www.linkedin.com/checkpoint/challenge/xyz")
    err = await detect_auth_failure(page, "linkedin")
    assert err is not None
    assert err.code == CHECKPOINT
    assert "checkpoint/challenge/xyz" in err.message


def test_portal_response_timestamps_are_utc_z():
    from datetime import datetime

    from app.models.enums import PortalName, PortalStatus
    from app.services.portal_service import PortalService
    from app.services.session_vault import SessionVault, encrypt_blob, normalize_cookies

    created = datetime(2026, 8, 14, 8, 0, 0)
    portal = SimpleNamespace(
        id="p1",
        name=PortalName.LINKEDIN,
        status=PortalStatus.ERROR,
        last_sync_at=datetime(2026, 8, 9, 8, 0, 0),
        sync_started_at=None,
        created_at=created,
        updated_at=datetime(2026, 8, 14, 13, 52, 0),
        credentials=SimpleNamespace(username="u"),
        cookies={
            "cookies": normalize_cookies([{"name": "bcookie", "value": "x", "domain": ".linkedin.com"}])
        },
        session_blob="",
        totp_secret_encrypted="",
        session_updated_at=None,
        selector_version=1,
        health=SimpleNamespace(
            model_dump=lambda: {
                "score": 48,
                "success_count": 0,
                "failure_count": 1,
                "consecutive_failures": 1,
                "last_error": "[CHECKPOINT] challenge",
                "auto_paused": False,
                "paused_reason": "",
            }
        ),
    )
    portal.session_blob = encrypt_blob(portal.cookies["cookies"])
    resp = PortalService()._to_response(portal)
    assert resp.last_sync_at == "2026-08-09T08:00:00Z"
    assert resp.last_attempt_at == "2026-08-14T13:52:00Z"
    assert resp.created_at.endswith("Z")
    _ = SessionVault


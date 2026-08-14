"""LinkedIn login: wait for the form, skip extra navigation, fill email/password."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.automation.auth import LOGIN_FAILED
from app.automation.errors import PortalAuthError
from app.automation.portals.linkedin import LinkedInPortal
from app.automation.selectors import fill_first, get_selector_pack, wait_any_selector

FEED_URL = "https://www.linkedin.com/feed/"
UAS_LOGIN = (
    "https://www.linkedin.com/uas/login"
    "?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F"
)
LOGIN_URL = "https://www.linkedin.com/login"


class _El:
    def __init__(self, inner: _InnerPage, selector: str) -> None:
        self._inner = inner
        self._selector = selector

    async def is_visible(self) -> bool:
        return self._selector in self._inner.visible


class _InnerPage:
    def __init__(self, start: str, *, visible: set[str] | None = None) -> None:
        self.url = start
        self.visible: set[str] = set(visible or ())
        self.filled: dict[str, str] = {}
        self.clicks: list[str] = []
        self.gotos: list[str] = []
        self.cookies: list[dict[str, str]] = []
        self.frames: list = []
        self.two_step = False
        self._title = "LinkedIn Login, Sign in | LinkedIn"

    def title(self) -> str:
        return self._title

    @property
    def context(self):  # noqa: ANN001
        ctx = MagicMock()
        ctx.cookies = AsyncMock(return_value=list(self.cookies))
        return ctx

    def _parts(self, selector: str) -> list[str]:
        if ", " in selector:
            return [part.strip() for part in selector.split(", ")]
        return [selector]

    async def query_selector(self, selector: str):
        for part in self._parts(selector):
            if part in self.visible:
                return _El(self, part)
        if selector in self.visible:
            return _El(self, selector)
        return None

    async def wait_for_selector(self, selector: str, *, timeout: int = 0, state: str = "visible"):
        el = await self.query_selector(selector)
        if el:
            return el
        raise TimeoutError(f"Timeout {timeout}ms waiting for {selector} ({state})")

    async def wait_for_timeout(self, _ms: int) -> None:
        return None

    async def wait_for_load_state(self, *_a, **_k) -> None:
        return None

    async def goto(self, url: str, **_kwargs: object) -> None:
        self.gotos.append(url)
        if "linkedin.com/feed" in url:
            self.url = UAS_LOGIN
            return
        self.url = url

    async def fill(self, selector: str, value: str, timeout: int = 0) -> None:
        self.filled[selector] = value

    def _password_filled(self) -> bool:
        return any("password" in key for key in self.filled)

    async def click(self, selector: str, timeout: int = 0) -> None:
        self.clicks.append(selector)
        if self.two_step and not self._password_filled():
            self.visible.add("#password")
            return
        if not self._password_filled():
            return
        self.url = FEED_URL
        self._title = "Feed | LinkedIn"
        self.visible = {
            sel
            for sel in self.visible
            if "password" not in sel and "username" not in sel and "session_key" not in sel
        }
        self.cookies = [{"name": "li_at", "value": "ok"}]


class _Page:
    def __init__(self, inner: _InnerPage) -> None:
        self.page = inner

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        await self.page.goto(url)

    async def fill(self, selector: str, value: str) -> None:
        await self.page.fill(selector, value)

    async def safe_click(self, selector: str, timeout: int = 5000) -> bool:
        el = await self.page.query_selector(selector)
        if not el:
            return False
        await self.page.click(selector, timeout=timeout)
        return True


def _portal() -> LinkedInPortal:
    return LinkedInPortal(credentials={"username": "me@example.com", "password": "secret"})


def test_is_login_url_covers_uas_checkpoint_and_authwall() -> None:
    is_login = LinkedInPortal._is_login_url
    assert is_login(UAS_LOGIN)
    assert is_login(LOGIN_URL)
    assert is_login("https://www.linkedin.com/checkpoint/challenge")
    assert is_login("https://www.linkedin.com/checkpoint/lg/login-submit")
    assert is_login("https://www.linkedin.com/authwall?trk=html")
    assert not is_login(FEED_URL)
    assert not is_login("https://www.linkedin.com/jobs/search/?keywords=software%20engineer")


def test_selector_pack_includes_email_and_username_fields() -> None:
    pack = get_selector_pack("linkedin")
    joined_user = " ".join(pack.all("login_user"))
    joined_pass = " ".join(pack.all("login_pass"))
    joined_submit = " ".join(pack.all("login_submit"))
    assert "session_key" in joined_user
    assert "autocomplete='username'" in joined_user
    assert "username webauthn" in joined_user
    assert "type='email'" in joined_user
    assert "session_password" in joined_pass
    assert "autocomplete='current-password'" in joined_pass
    assert "login-submit" in joined_submit


@pytest.mark.asyncio
async def test_wait_any_selector_finds_late_field() -> None:
    page = _Page(_InnerPage(LOGIN_URL, visible={"#username"}))
    assert await wait_any_selector(page, ["#missing", "#username"], timeout=2_000) == "#username"


@pytest.mark.asyncio
async def test_fill_first_waits_then_fills() -> None:
    page = _Page(_InnerPage(LOGIN_URL, visible={"input[type='email']"}))
    used = await fill_first(
        page,
        ["#username", "input[type='email']"],
        "me@example.com",
        timeout=2_000,
    )
    assert used == "input[type='email']"
    assert page.page.filled["input[type='email']"] == "me@example.com"


@pytest.mark.asyncio
async def test_fill_first_skips_hidden_duplicate_inputs() -> None:
    class _LocItem:
        def __init__(self, visible: bool, sink: dict[str, str], selector: str) -> None:
            self._visible = visible
            self._sink = sink
            self._selector = selector

        async def is_visible(self) -> bool:
            return self._visible

        async def fill(self, value: str, timeout: int = 0) -> None:
            self._sink[self._selector] = value

    class _Locator:
        def __init__(self, items: list[_LocItem]) -> None:
            self._items = items

        async def count(self) -> int:
            return len(self._items)

        def nth(self, idx: int) -> _LocItem:
            return self._items[idx]

    inner = _InnerPage(LOGIN_URL, visible={"input[type='email']"})
    hidden = _LocItem(False, inner.filled, "input[type='email']")
    shown = _LocItem(True, inner.filled, "input[type='email']")
    inner.locator = lambda sel: _Locator([hidden, shown])  # type: ignore[method-assign]
    page = _Page(inner)
    used = await fill_first(page, ["input[type='email']"], "me@example.com", timeout=2_000)
    assert used == "input[type='email']"
    assert inner.filled["input[type='email']"] == "me@example.com"


@pytest.mark.asyncio
async def test_linkedin_login_skips_second_goto_when_feed_redirects_to_uas() -> None:
    inner = _InnerPage(
        FEED_URL,
        visible={"#username", "#password", "button[type='submit']"},
    )
    page = _Page(inner)
    await _portal().login(page)
    assert inner.gotos == [FEED_URL]
    assert inner.filled["#username"] == "me@example.com"
    assert inner.filled["#password"] == "secret"
    assert "button[type='submit']" in inner.clicks


@pytest.mark.asyncio
async def test_linkedin_login_fills_session_key_when_id_username_absent() -> None:
    inner = _InnerPage(
        FEED_URL,
        visible={
            "input[name='session_key']",
            "input[name='session_password']",
            "button[data-litms-control-urn='login-submit']",
        },
    )
    page = _Page(inner)
    await _portal().login(page)
    assert inner.filled["input[name='session_key']"] == "me@example.com"
    assert inner.filled["input[name='session_password']"] == "secret"


@pytest.mark.asyncio
async def test_linkedin_login_two_step_clicks_continue_then_password() -> None:
    inner = _InnerPage(FEED_URL, visible={"#username", "button[type='submit']"})
    inner.two_step = True
    page = _Page(inner)
    await _portal().login(page)
    assert inner.filled["#username"] == "me@example.com"
    assert inner.filled["#password"] == "secret"
    assert inner.clicks.count("button[type='submit']") >= 2


@pytest.mark.asyncio
async def test_linkedin_login_missing_fields_reports_landed_url() -> None:
    inner = _InnerPage(FEED_URL)
    page = _Page(inner)
    with pytest.raises(PortalAuthError) as exc:
        await _portal().login(page)
    assert exc.value.code == LOGIN_FAILED
    assert "LOGIN_FAILED" in str(exc.value)
    assert "uas/login" in str(exc.value)
    assert inner.gotos == [FEED_URL]

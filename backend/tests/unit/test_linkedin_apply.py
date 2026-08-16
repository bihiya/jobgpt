"""LinkedIn Easy Apply: job URLs, already-applied, external apply, verified submit."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.automation.base.portal import ExtractedJob
from app.automation.form_fields import FieldResolution
from app.automation.portals.linkedin import (
    LinkedInPortal,
    canonical_job_url,
    linkedin_job_id,
)
from app.automation.selectors import get_selector_pack


JOB_URL = "https://www.linkedin.com/jobs/view/4123456789/"
COMPANY_URL = "https://www.linkedin.com/company/acme/"


class _El:
    def __init__(self, inner: _InnerPage, selector: str, href: str = "") -> None:
        self._inner = inner
        self._selector = selector
        self._href = href

    async def is_visible(self) -> bool:
        return self._selector in self._inner.visible

    async def get_attribute(self, name: str):
        if name == "href":
            return self._href
        return None

    async def inner_text(self) -> str:
        return self._inner.texts.get(self._selector, "")


class _PwItem:
    def __init__(self, inner: _InnerPage, selector: str) -> None:
        self._inner = inner
        self._selector = selector

    async def is_visible(self) -> bool:
        return self._selector in self._inner.visible

    async def click(self, timeout: int = 0) -> None:
        await self._inner.click(self._selector, timeout=timeout)


class _PwLocator:
    def __init__(self, inner: _InnerPage, selector: str) -> None:
        self._inner = inner
        self._selector = selector

    def _hits(self) -> list[str]:
        parts = [part.strip() for part in self._selector.split(",") if part.strip()]
        return [part for part in parts if part in self._inner.visible]

    async def count(self) -> int:
        return len(self._hits())

    def nth(self, idx: int) -> _PwItem:
        hits = self._hits()
        return _PwItem(self._inner, hits[idx] if idx < len(hits) else self._selector)

    def locator(self, sel: str) -> _PwLocator:
        if sel.startswith("visible"):
            return self
        return _PwLocator(self._inner, sel)


class _Card:
    def __init__(self, text: str, links: list[tuple[str, str]]) -> None:
        self._text = text
        self._links = links  # (selector, href)

    async def inner_text(self) -> str:
        return self._text

    async def query_selector(self, selector: str):
        for sel, href in self._links:
            if sel == selector or (selector.startswith("a[href") and "/jobs/view/" in href):
                return _El(MagicMock(visible={sel}, texts={}), sel, href)
        if selector == "a" and self._links:
            sel, href = self._links[0]
            return _El(MagicMock(visible={sel}, texts={}), sel, href)
        return None

    async def query_selector_all(self, selector: str):
        if selector != "a":
            return []
        return [_El(MagicMock(visible={sel}, texts={}), sel, href) for sel, href in self._links]


class _InnerPage:
    def __init__(self, start: str, *, visible: set[str] | None = None, body: str = "") -> None:
        self.url = start
        self.visible: set[str] = set(visible or ())
        self.filled: dict[str, str] = {}
        self.clicks: list[str] = []
        self.gotos: list[str] = []
        self.uploads: list[tuple[str, str]] = []
        self.body = body
        self.texts: dict[str, str] = {}
        self.cards: list[_Card] = []
        self.frames: list = []
        self.html = "<html><body>job</body></html>"
        self._title = "Job | LinkedIn"
        self.redirect_to = ""

    def title(self) -> str:
        return self._title

    @property
    def context(self):  # noqa: ANN001
        ctx = MagicMock()
        ctx.cookies = AsyncMock(return_value=[{"name": "li_at", "value": "tok"}])
        return ctx

    def locator(self, selector: str) -> _PwLocator:
        return _PwLocator(self, selector)

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

    async def query_selector_all(self, selector: str):
        card_sels = {
            ".jobs-search-results__list-item",
            ".job-card-container",
            "li[data-occludable-job-id]",
            "[data-job-id]",
        }
        if selector in card_sels:
            return list(self.cards)
        hits = [part for part in self._parts(selector) if part in self.visible]
        return [_El(self, part) for part in hits]

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
        self.url = self.redirect_to or url

    async def fill(self, selector: str, value: str, timeout: int = 0) -> None:
        self.filled[selector] = value

    async def click(self, selector: str, timeout: int = 0) -> None:
        self.clicks.append(selector)
        easy = "Easy Apply" in selector or "LinkedIn Apply to" in selector
        if easy or "jobs-s-apply" in selector:
            self.visible.update(
                {
                    ".jobs-easy-apply-modal",
                    "button:has-text('Submit application')",
                    "input[type='file']",
                }
            )
            self.visible.discard("button:has-text('Easy Apply')")
            self.visible.discard("button[aria-label*='Easy Apply']")
        if "Submit" in selector:
            self.body = "Application sent. Your application was sent to Acme."
            self.visible.add("text=Application sent")
            self.html = "<html><body>Application sent</body></html>"

    async def inner_text(self, selector: str) -> str:
        if selector == "body":
            return self.body
        return self.texts.get(selector, "")

    async def content(self) -> str:
        return self.html

    async def screenshot(self, path: str, full_page: bool = True) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"png")

    async def set_input_files(self, selector: str, file_path: str) -> None:
        self.uploads.append((selector, file_path))


class _Page:
    def __init__(self, inner: _InnerPage) -> None:
        self.page = inner

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        await self.page.goto(url)

    async def fill(self, selector: str, value: str) -> None:
        await self.page.fill(selector, value)

    async def upload(self, selector: str, file_path: str) -> None:
        await self.page.set_input_files(selector, file_path)

    async def screenshot(self, path: str) -> str:
        await self.page.screenshot(path)
        return path

    async def safe_click(self, selector: str, timeout: int = 5000) -> bool:
        el = await self.page.query_selector(selector)
        if not el:
            return False
        await self.page.click(selector, timeout=timeout)
        return True


def _job(**overrides) -> ExtractedJob:
    data = dict(
        external_id="linkedin-4123456789",
        title="Software Engineer",
        company="Acme",
        apply_url=JOB_URL,
    )
    data.update(overrides)
    return ExtractedJob(**data)


def _portal() -> LinkedInPortal:
    return LinkedInPortal(credentials={})


def test_canonical_job_url_strips_tracking_and_company_links():
    assert linkedin_job_id("https://www.linkedin.com/jobs/view/4123456789/?eBP=abc") == "4123456789"
    assert (
        canonical_job_url("/jobs/view/4123456789/?trk=flagship")
        == "https://www.linkedin.com/jobs/view/4123456789/"
    )
    assert (
        canonical_job_url("https://www.linkedin.com/jobs/search/?currentJobId=4123456789")
        == "https://www.linkedin.com/jobs/view/4123456789/"
    )
    assert canonical_job_url(COMPANY_URL) == COMPANY_URL
    assert linkedin_job_id(COMPANY_URL) == ""


@pytest.mark.asyncio
async def test_extract_jobs_uses_job_view_not_company_logo():
    inner = _InnerPage("https://www.linkedin.com/jobs/search/?keywords=eng")
    inner.cards = [
        _Card(
            "Software Engineer\nAcme\nRemote",
            [
                ("a[href*='/company/']", "/company/acme/"),
                ("a[href*='/jobs/view/']", "/jobs/view/4123456789/?trk=flagship"),
            ],
        )
    ]
    jobs = await _portal().extract_jobs(_Page(inner))
    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].company == "Acme"
    assert jobs[0].apply_url == JOB_URL
    assert jobs[0].external_id == "linkedin-4123456789"


@pytest.mark.asyncio
async def test_apply_verified_easy_apply_submit(tmp_path):
    inner = _InnerPage(
        JOB_URL,
        visible={"button:has-text('Easy Apply')"},
        body="Easy Apply to Software Engineer at Acme",
    )
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF")
    result = await _portal().apply(_Page(inner), _job(), str(resume), {})
    assert result.success is True
    assert "Easy Apply" in result.message
    assert JOB_URL in inner.gotos
    assert any("Easy Apply" in click for click in inner.clicks)
    assert any("Submit" in click for click in inner.clicks)
    assert inner.uploads
    keys = [step["key"] for step in result.steps]
    assert "opened_jd" in keys
    assert "clicked_apply" in keys
    assert "submitted" in keys
    assert "verified" in keys


@pytest.mark.asyncio
async def test_apply_treats_already_applied_as_success():
    inner = _InnerPage(
        JOB_URL,
        visible={"text=You applied on"},
        body="You applied on Aug 1, 2026",
    )
    result = await _portal().apply(_Page(inner), _job(), "/tmp/r.pdf", {})
    assert result.success is True
    assert result.message == "Already applied on LinkedIn"
    assert not any("Easy Apply" in click for click in inner.clicks)


@pytest.mark.asyncio
async def test_apply_rejects_company_site_apply():
    inner = _InnerPage(
        JOB_URL,
        visible={"button[aria-label*='Apply on company']"},
        body="Apply on company website",
    )
    result = await _portal().apply(_Page(inner), _job(), "/tmp/r.pdf", {})
    assert result.success is False
    assert "company-site" in result.message
    assert result.fail_proof_html


@pytest.mark.asyncio
async def test_apply_missing_easy_apply_captures_proof():
    inner = _InnerPage(JOB_URL, visible=set(), body="Job description only")
    result = await _portal().apply(_Page(inner), _job(), "/tmp/r.pdf", {})
    assert result.success is False
    assert result.message == "Easy Apply button not found"
    assert result.screenshot_path
    assert result.fail_proof_html


@pytest.mark.asyncio
async def test_apply_authwall_after_opening_jd():
    inner = _InnerPage(JOB_URL, visible=set(), body="Sign in")
    inner.redirect_to = "https://www.linkedin.com/authwall?trk=html"
    result = await _portal().apply(_Page(inner), _job(), "/tmp/r.pdf", {})
    assert result.success is False
    assert "session expired" in result.message.lower()


@pytest.mark.asyncio
async def test_apply_closed_listing():
    inner = _InnerPage(
        JOB_URL,
        visible=set(),
        body="This job is no longer accepting applications",
    )
    result = await _portal().apply(_Page(inner), _job(), "/tmp/r.pdf", {})
    assert result.success is False
    assert "no longer accepting" in result.message


@pytest.mark.asyncio
async def test_apply_pauses_on_unknown_question():
    inner = _InnerPage(
        JOB_URL,
        visible={"button:has-text('Easy Apply')"},
        body="Easy Apply",
    )

    page = _Page(inner)
    portal = _portal()
    with patch("app.automation.portals.linkedin.resolve_and_fill") as mocked:
        mocked.side_effect = AsyncMock(
            return_value=FieldResolution(unknown=["Are you willing to relocate?"])
        )
        result = await portal.apply(page, _job(), "/tmp/r.pdf", {})
    assert result.success is False
    assert result.needs_input is True
    assert result.unknown_questions == ["Are you willing to relocate?"]


def test_easy_apply_selectors_are_not_greedy():
    pack = get_selector_pack("linkedin")
    assert "button:has-text('Apply')" not in pack.all("easy_apply")
    assert any("openSDUIApplyFlow" in sel for sel in pack.all("easy_apply"))

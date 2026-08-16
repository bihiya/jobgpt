"""Workday apply_landed: apply button, resume, wizard submit, account wall."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.automation.base.portal import ExtractedJob
from app.automation.form_fields import FieldResolution
from app.automation.portals.workday import WorkdayPortal


class _El:
    def __init__(self, inner: _InnerPage, selector: str) -> None:
        self._inner = inner
        self._selector = selector

    async def is_visible(self) -> bool:
        return self._selector in self._inner.visible

    async def get_attribute(self, _name: str):
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


class _InnerPage:
    def __init__(self, start: str, *, visible: set[str] | None = None, body: str = "") -> None:
        self.url = start
        self.visible: set[str] = set(visible or ())
        self.clicks: list[str] = []
        self.uploads: list[tuple[str, str]] = []
        self.body = body
        self.texts: dict[str, str] = {}
        self.frames: list = []
        self.html = "<html><body>workday</body></html>"
        self.filled: dict[str, str] = {}

    @property
    def context(self):  # noqa: ANN001
        return self

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
        self.url = url

    async def click(self, selector: str, timeout: int = 0) -> None:
        self.clicks.append(selector)
        if "jobPostingApplyButton" in selector or selector in {
            "button:has-text('Apply')",
            "a:has-text('Apply')",
        }:
            self.visible.update(
                {
                    "input[data-automation-id='file-upload-input-ref']",
                    "input[type='file']",
                    "button[data-automation-id='bottom-navigation-next-button']",
                    "button[data-automation-id='bottom-navigation-submit-button']",
                }
            )
            self.visible.discard("a[data-automation-id='jobPostingApplyButton']")
        if "submit" in selector.lower() or selector == "button:has-text('Submit')":
            self.body = "Thank you for applying. We have received your application."
            self.visible.add("text=Thank you for applying")
            self.html = "<html><body>Thank you for applying</body></html>"

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

    async def fill(self, selector: str, value: str, timeout: int = 0) -> None:
        self.filled[selector] = value


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
        if el:
            await self.page.click(selector, timeout=timeout)
            return True
        return False


WD_URL = "https://acme.wd5.myworkdayjobs.com/en-US/External/job/Engineer"


def _job() -> ExtractedJob:
    return ExtractedJob(
        external_id="wd-1",
        title="Engineer",
        company="Acme",
        apply_url=WD_URL,
    )


@pytest.mark.asyncio
async def test_workday_apply_landed_submits(tmp_path):
    inner = _InnerPage(
        WD_URL,
        visible={"a[data-automation-id='jobPostingApplyButton']"},
        body="Software Engineer — Apply",
    )
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF")
    with patch(
        "app.automation.portals.workday.resolve_and_fill",
        return_value=FieldResolution(),
    ):
        result = await WorkdayPortal().apply_landed(_Page(inner), _job(), str(resume), {})
    assert result.success is True
    assert "Workday" in result.message
    assert result.metadata.get("apply_channel") == "External apply · Workday"
    assert inner.uploads
    assert any("submit" in click.lower() for click in inner.clicks)
    keys = [step["key"] for step in result.steps]
    assert "apply_channel" in keys
    assert "clicked_apply" in keys
    assert "uploaded_resume" in keys
    assert "submitted" in keys
    assert "verified" in keys


@pytest.mark.asyncio
async def test_workday_account_wall_without_credentials():
    inner = _InnerPage(
        WD_URL,
        visible={"button:has-text('Create Account')", "h1:has-text('Sign In')"},
        body="Create Account",
    )
    result = await WorkdayPortal().apply_landed(_Page(inner), _job(), "/tmp/r.pdf", {})
    assert result.success is False
    assert "candidate account" in result.message.lower()
    assert result.fail_proof_html

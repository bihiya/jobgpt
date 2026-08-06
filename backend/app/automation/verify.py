"""Apply success verification and failure proof capture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.automation.base.page import BasePage
from app.automation.selectors import SelectorPack, any_visible
from app.core.config import settings


@dataclass
class VerifyResult:
    success: bool
    detail: str = ""
    screenshot_path: str = ""
    fail_proof_html: str = ""
    fail_proof_path: str = ""


SUCCESS_TEXT_FALLBACKS = [
    "application sent",
    "application submitted",
    "thank you for applying",
    "your application has been submitted",
    "successfully applied",
    "we have received your application",
]


async def verify_apply_success(
    page: BasePage,
    pack: SelectorPack,
    *,
    prefix: str = "verify",
) -> VerifyResult:
    """Confirm apply succeeded via portal selectors or page text — never assume."""
    if pack.all("success") and await any_visible(page, pack.all("success")):
        shot = await _shot(page, f"{prefix}-ok")
        return VerifyResult(success=True, detail="Matched success selector", screenshot_path=shot)

    try:
        body = (await page.page.inner_text("body")).lower()
    except Exception:  # noqa: BLE001
        body = ""

    for needle in SUCCESS_TEXT_FALLBACKS:
        if needle in body:
            shot = await _shot(page, f"{prefix}-ok")
            return VerifyResult(success=True, detail=f"Matched text: {needle}", screenshot_path=shot)

    url = (page.page.url or "").lower()
    if any(token in url for token in ("confirmation", "thank", "success", "applied")):
        shot = await _shot(page, f"{prefix}-ok")
        return VerifyResult(success=True, detail=f"URL suggests success: {url[:120]}", screenshot_path=shot)

    proof = await capture_fail_proof(page, prefix=f"{prefix}-fail")
    return VerifyResult(
        success=False,
        detail="No success confirmation found after submit",
        screenshot_path=proof["screenshot_path"],
        fail_proof_html=proof["html"],
        fail_proof_path=proof["html_path"],
    )


async def capture_fail_proof(page: BasePage, *, prefix: str = "fail") -> dict[str, str]:
    """Screenshot + truncated DOM snapshot for debugging failed applies."""
    shot = await _shot(page, prefix)
    html = ""
    html_path = ""
    try:
        html = await page.page.content()
        # Cap stored HTML to keep Mongo docs reasonable
        html = html[:120_000]
        path = Path(settings.screenshot_dir) / f"{prefix}-{uuid4().hex}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        html_path = str(path)
    except Exception:  # noqa: BLE001
        html = ""
    return {"screenshot_path": shot, "html": html, "html_path": html_path}


async def _shot(page: BasePage, prefix: str) -> str:
    path = Path(settings.screenshot_dir) / f"{prefix}-{uuid4().hex}.png"
    try:
        return await page.screenshot(str(path))
    except Exception:  # noqa: BLE001
        return ""

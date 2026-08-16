"""Follow company-site Apply clicks that open a new tab or leave the job board."""

from __future__ import annotations

from app.automation.ats import is_offsite
from app.automation.base.page import BasePage
from app.automation.selectors import click_first


async def _call(obj: object, name: str, *args: object, **kwargs: object):
    fn = getattr(obj, name, None)
    if not callable(fn):
        return None
    try:
        return await fn(*args, **kwargs)
    except TypeError:
        try:
            return fn(*args, **kwargs)
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001
        return None


async def wait_for_offsite(
    page: BasePage,
    origin_hosts: tuple[str, ...],
    *,
    timeout_ms: int = 12000,
) -> bool:
    raw = page.page
    wait_url = getattr(raw, "wait_for_url", None)
    if callable(wait_url):
        try:
            await wait_url(
                lambda url: is_offsite(url if isinstance(url, str) else str(url), origin_hosts),
                timeout=timeout_ms,
            )
            return True
        except Exception:  # noqa: BLE001
            pass
    steps = max(1, int(timeout_ms / 400))
    for _ in range(steps):
        current = getattr(raw, "url", "") or ""
        if is_offsite(current, origin_hosts):
            return True
        await _call(raw, "wait_for_timeout", 400)
        if not getattr(raw, "wait_for_timeout", None):
            break
    return is_offsite(getattr(raw, "url", "") or "", origin_hosts)


async def click_and_follow(
    page: BasePage,
    selectors: list[str],
    *,
    origin_hosts: tuple[str, ...],
    timeout_ms: int = 12000,
) -> tuple[str | None, BasePage]:
    """Click Apply and return the page that now holds the company-site form."""
    raw = page.page
    context = getattr(raw, "context", None)
    before_pages = list(getattr(context, "pages", []) or []) if context is not None else [raw]
    popups: list = []

    def _on_popup(new_page: object) -> None:
        popups.append(new_page)

    on = getattr(raw, "on", None)
    off = getattr(raw, "remove_listener", None) or getattr(raw, "off", None)
    if callable(on):
        try:
            on("popup", _on_popup)
        except Exception:  # noqa: BLE001
            on = None

    clicked = await click_first(page, selectors)
    if not clicked:
        if callable(off) and callable(on):
            try:
                off("popup", _on_popup)
            except Exception:  # noqa: BLE001
                pass
        return None, page

    await _call(raw, "wait_for_timeout", 1200)
    await _call(raw, "wait_for_load_state", "domcontentloaded", timeout=min(timeout_ms, 8000))

    if not popups:
        await wait_for_offsite(page, origin_hosts, timeout_ms=timeout_ms)

    if callable(off) and callable(on):
        try:
            off("popup", _on_popup)
        except Exception:  # noqa: BLE001
            pass

    target = popups[-1] if popups else None
    if target is None and context is not None:
        after_pages = list(getattr(context, "pages", []) or [])
        for candidate in after_pages:
            if candidate not in before_pages and candidate is not raw:
                target = candidate
                break

    if target is not None:
        await _call(target, "wait_for_load_state", "domcontentloaded", timeout=8000)
        await wait_for_offsite(BasePage(target), origin_hosts, timeout_ms=min(timeout_ms, 8000))
        return clicked, BasePage(target)

    return clicked, page

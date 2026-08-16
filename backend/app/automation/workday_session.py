"""Workday cookies are per career-site host (nvidia.wd5… ≠ apple.wd5…)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

_SHARED_HOSTS = frozenset(
    {
        "myworkdayjobs.com",
        "myworkday.com",
        "workday.com",
        "www.myworkdayjobs.com",
        "www.myworkday.com",
        "www.workday.com",
    }
)


def cookie_domain(cookie: dict[str, Any] | None) -> str:
    if not isinstance(cookie, dict):
        return ""
    return str(cookie.get("domain") or "").lower().removeprefix(".")


def workday_tenant_host(url: str) -> str:
    """nvidia.wd5.myworkdayjobs.com — empty when the URL is not a Workday tenant."""
    host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    if not host:
        return ""
    if "myworkday" in host or host.endswith("workday.com"):
        return host
    return ""


def cookie_matches_workday_host(cookie: dict[str, Any], host: str) -> bool:
    """True only for this tenant. Shared .myworkdayjobs.com cookies do not match."""
    host = (host or "").lower().removeprefix("www.")
    domain = cookie_domain(cookie)
    if not host or not domain or domain in _SHARED_HOSTS:
        return False
    return domain == host or domain.endswith("." + host)


def cookies_for_workday_host(cookies: list[dict[str, Any]] | None, host: str) -> list[dict[str, Any]]:
    if not host:
        return []
    return [item for item in cookies or [] if cookie_matches_workday_host(item, host)]


def merge_workday_tenant_cookies(
    existing: list[dict[str, Any]] | None,
    incoming: list[dict[str, Any]] | None,
    host: str,
) -> list[dict[str, Any]]:
    """Replace this tenant's cookies; keep every other Workday host untouched."""
    host = (host or "").lower().removeprefix("www.")
    kept = [item for item in existing or [] if not cookie_matches_workday_host(item, host)]
    incoming_host: list[dict[str, Any]] = []
    for item in incoming or []:
        if cookie_matches_workday_host(item, host):
            incoming_host.append(item)
            continue
        if host and not cookie_domain(item) and item.get("name"):
            stamped = dict(item)
            stamped["domain"] = host
            incoming_host.append(stamped)
    return kept + incoming_host

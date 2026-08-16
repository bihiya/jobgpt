"""Portal adapter factory/registry."""

from __future__ import annotations

from typing import Any

from app.automation.base.portal import BasePortal
from app.automation.portals.generic import GenericPortal
from app.automation.portals.greenhouse import GreenhousePortal
from app.automation.portals.indeed import IndeedPortal
from app.automation.portals.lever import LeverPortal
from app.automation.portals.linkedin import LinkedInPortal
from app.automation.portals.workday import WorkdayPortal
from app.models.enums import PortalName

PORTAL_BASE_URLS = {
    PortalName.NAUKRI: "https://www.naukri.com",
    PortalName.FOUNDIT: "https://www.foundit.in",
    PortalName.WELLFOUND: "https://wellfound.com",
    PortalName.ASHBY: "https://jobs.ashbyhq.com",
    PortalName.WORKDAY: "https://www.myworkdayjobs.com",
    PortalName.SMARTRECRUITERS: "https://jobs.smartrecruiters.com",
    PortalName.ORACLE: "https://eeho.fa.us2.oraclecloud.com",
    PortalName.SAP_SUCCESSFACTORS: "https://career2.successfactors.eu",
    PortalName.TALEO: "https://tbe.taleo.net",
}

_ATS_GENERIC_BASES = {
    "ashby": "https://jobs.ashbyhq.com",
    "smartrecruiters": "https://jobs.smartrecruiters.com",
    "taleo": "https://tbe.taleo.net",
    "successfactors": "https://career2.successfactors.eu",
    "icims": "https://careers.icims.com",
    "oracle": "https://eeho.fa.us2.oraclecloud.com",
    "generic": "https://example.com",
}


def get_portal_adapter(
    name: str | PortalName,
    *,
    credentials: dict[str, str] | None = None,
    cookies: list[dict[str, Any]] | None = None,
    proxy: dict[str, str] | None = None,
    headless: bool | None = None,
    totp_secret: str = "",
    otp_code: str = "",
    selector_version: int = 1,
) -> BasePortal:
    portal_name = PortalName(name) if isinstance(name, str) else name
    kwargs = {
        "credentials": credentials,
        "cookies": cookies,
        "proxy": proxy,
        "headless": headless,
        "totp_secret": totp_secret,
        "otp_code": otp_code,
        "selector_version": selector_version,
    }

    if portal_name == PortalName.LINKEDIN:
        return LinkedInPortal(**kwargs)
    if portal_name == PortalName.INDEED:
        return IndeedPortal(**kwargs)
    if portal_name == PortalName.GREENHOUSE:
        return GreenhousePortal(**kwargs)
    if portal_name == PortalName.LEVER:
        return LeverPortal(**kwargs)
    if portal_name == PortalName.WORKDAY:
        return WorkdayPortal(**kwargs)

    base_url = PORTAL_BASE_URLS.get(portal_name, "https://example.com")
    generic_kwargs = {
        "credentials": credentials,
        "cookies": cookies,
        "proxy": proxy,
        "headless": headless,
    }
    return GenericPortal(name=portal_name.value, base_url=base_url, **generic_kwargs)


def adapter_for_ats(
    ats: str,
    *,
    credentials: dict[str, str] | None = None,
    cookies: list[dict[str, Any]] | None = None,
    proxy: dict[str, str] | None = None,
    headless: bool | None = None,
    totp_secret: str = "",
    otp_code: str = "",
    selector_version: int = 1,
) -> BasePortal:
    """Adapter for a company-site ATS detected from the landed URL."""
    key = (ats or "generic").lower()
    first_class = {
        "workday": PortalName.WORKDAY,
        "greenhouse": PortalName.GREENHOUSE,
        "lever": PortalName.LEVER,
    }
    if key in first_class:
        return get_portal_adapter(
            first_class[key],
            credentials=credentials,
            cookies=cookies,
            proxy=proxy,
            headless=headless,
            totp_secret=totp_secret,
            otp_code=otp_code,
            selector_version=selector_version,
        )
    return GenericPortal(
        name=key,
        base_url=_ATS_GENERIC_BASES.get(key, "https://example.com"),
        credentials=credentials,
        cookies=cookies,
        proxy=proxy,
        headless=headless,
    )

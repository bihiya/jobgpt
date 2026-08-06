"""Portal adapter factory/registry."""

from __future__ import annotations

from typing import Any

from app.automation.base.portal import BasePortal
from app.automation.portals.generic import GenericPortal
from app.automation.portals.greenhouse import GreenhousePortal
from app.automation.portals.indeed import IndeedPortal
from app.automation.portals.lever import LeverPortal
from app.automation.portals.linkedin import LinkedInPortal
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


def get_portal_adapter(
    name: str | PortalName,
    *,
    credentials: dict[str, str] | None = None,
    cookies: list[dict[str, Any]] | None = None,
    proxy: dict[str, str] | None = None,
    headless: bool | None = None,
) -> BasePortal:
    portal_name = PortalName(name) if isinstance(name, str) else name
    kwargs = {
        "credentials": credentials,
        "cookies": cookies,
        "proxy": proxy,
        "headless": headless,
    }

    if portal_name == PortalName.LINKEDIN:
        return LinkedInPortal(**kwargs)
    if portal_name == PortalName.INDEED:
        return IndeedPortal(**kwargs)
    if portal_name == PortalName.GREENHOUSE:
        return GreenhousePortal(**kwargs)
    if portal_name == PortalName.LEVER:
        return LeverPortal(**kwargs)

    base_url = PORTAL_BASE_URLS.get(portal_name, "https://example.com")
    return GenericPortal(name=portal_name.value, base_url=base_url, **kwargs)

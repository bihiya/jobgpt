"""Detect company-site ATS hosts and tag LinkedIn vs external apply."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.automation.base.portal import ApplyResult, BasePortal, ExtractedJob

ATS_WORKDAY = "workday"
ATS_GREENHOUSE = "greenhouse"
ATS_LEVER = "lever"
ATS_ASHBY = "ashby"
ATS_SMARTRECRUITERS = "smartrecruiters"
ATS_TALEO = "taleo"
ATS_SUCCESSFACTORS = "successfactors"
ATS_ICIMS = "icims"
ATS_ORACLE = "oracle"
ATS_GENERIC = "generic"

KIND_LINKEDIN = "linkedin"
KIND_EXTERNAL = "external"

ATS_LABELS: dict[str, str] = {
    ATS_WORKDAY: "Workday",
    ATS_GREENHOUSE: "Greenhouse",
    ATS_LEVER: "Lever",
    ATS_ASHBY: "Ashby",
    ATS_SMARTRECRUITERS: "SmartRecruiters",
    ATS_TALEO: "Taleo",
    ATS_SUCCESSFACTORS: "SuccessFactors",
    ATS_ICIMS: "iCIMS",
    ATS_ORACLE: "Oracle Cloud",
    ATS_GENERIC: "Company site",
}

_HOST_RULES: tuple[tuple[str, str], ...] = (
    ("myworkdayjobs.com", ATS_WORKDAY),
    ("myworkday.com", ATS_WORKDAY),
    ("workday.com", ATS_WORKDAY),
    ("greenhouse.io", ATS_GREENHOUSE),
    ("greenhouse.com", ATS_GREENHOUSE),
    ("lever.co", ATS_LEVER),
    ("ashbyhq.com", ATS_ASHBY),
    ("smartrecruiters.com", ATS_SMARTRECRUITERS),
    ("taleo.net", ATS_TALEO),
    ("successfactors.com", ATS_SUCCESSFACTORS),
    ("successfactors.eu", ATS_SUCCESSFACTORS),
    ("icims.com", ATS_ICIMS),
    ("oraclecloud.com", ATS_ORACLE),
)

def hostname(url: str) -> str:
    return (urlparse(url or "").hostname or "").lower().removeprefix("www.")


def detect_ats(url: str) -> str:
    host = hostname(url)
    if not host:
        return ATS_GENERIC
    if host.startswith("wd") and "myworkday" in host:
        return ATS_WORKDAY
    for needle, ats in _HOST_RULES:
        if host == needle or host.endswith("." + needle):
            return ats
    return ATS_GENERIC


def ats_display_name(ats: str) -> str:
    return ATS_LABELS.get((ats or "").lower(), ATS_LABELS[ATS_GENERIC])


def channel_label(*, kind: str, ats: str = "") -> str:
    if kind in {KIND_LINKEDIN, "easy", "linkedin_easy_apply"}:
        return "LinkedIn Easy Apply"
    if kind in {"indeed", "indeed_apply"}:
        return "Indeed apply"
    name = ats_display_name(ats) if ats else ""
    if ats and ats != ATS_GENERIC and name:
        return f"External apply · {name}"
    return "External apply"


def predicted_channel_meta(kind: str, *, ats: str = "") -> dict[str, Any]:
    """Store a fetch-time Easy Apply vs company-site guess on the job."""
    if kind in {KIND_LINKEDIN, "easy", "linkedin_easy_apply"}:
        return {
            "apply_channel": channel_label(kind=KIND_LINKEDIN),
            "apply_channel_kind": KIND_LINKEDIN,
            "apply_channel_predicted": True,
        }
    if kind in {KIND_EXTERNAL, "company", "company_site"}:
        return {
            "apply_channel": channel_label(kind=KIND_EXTERNAL, ats=ats),
            "apply_channel_kind": KIND_EXTERNAL,
            "apply_channel_predicted": True,
            "ats": ats or "",
        }
    return {}


def is_offsite(url: str, origin_hosts: tuple[str, ...]) -> bool:
    host = hostname(url)
    if not host:
        return False
    for origin in origin_hosts:
        origin = origin.lower().removeprefix("www.")
        if host == origin or host.endswith("." + origin):
            return False
    return True


def tag_apply_result(
    result: ApplyResult,
    *,
    kind: str,
    ats: str = "",
    url: str = "",
) -> ApplyResult:
    label = channel_label(kind=kind, ats=ats)
    result.metadata = {
        **(result.metadata or {}),
        "apply_channel": label,
        "apply_channel_kind": (
            KIND_LINKEDIN
            if kind == KIND_LINKEDIN
            else "indeed"
            if kind in {"indeed", "indeed_apply"}
            else KIND_EXTERNAL
        ),
        "ats": ats or "",
        "external_url": (url or "")[:400],
    }
    return result


def record_apply_channel(portal: BasePortal, *, kind: str, ats: str = "", url: str = "") -> str:
    """Record the channel once so LinkedIn → ATS handoff does not double-tag."""
    label = channel_label(kind=kind, ats=ats)
    for step in portal.recorder.steps:
        if step.key == "apply_channel":
            return str(step.label or label)
    portal.recorder.apply_channel(label, kind=kind, ats=ats, url=(url or "")[:300])
    return label


def spawn_child_adapter(parent: BasePortal, ats: str) -> BasePortal:
    """Reuse the live recorder; pull Workday/Greenhouse credentials when saved."""
    from app.automation.portals.registry import adapter_for_ats

    key = (ats or ATS_GENERIC).lower()
    creds = (getattr(parent, "ats_credentials", None) or {}).get(key) or {}
    cookies = (getattr(parent, "ats_cookies", None) or {}).get(key) or []
    totp = (getattr(parent, "ats_totp", None) or {}).get(key) or ""
    adapter = adapter_for_ats(
        key,
        credentials=creds,
        cookies=cookies,
        proxy=parent.proxy,
        headless=getattr(parent.browser, "headless", None),
        selector_version=getattr(parent, "selector_version", 1),
        totp_secret=totp,
        otp_code=getattr(parent, "otp_code", "") or "",
    )
    adapter.recorder = parent.recorder
    adapter.cover_letter_path = getattr(parent, "cover_letter_path", "") or ""
    adapter.extra_files = list(getattr(parent, "extra_files", None) or [])
    return adapter


async def _inject_cookies(page: Any, cookies: list[dict[str, Any]] | None) -> None:
    if not cookies:
        return
    context = getattr(getattr(page, "page", None), "context", None)
    add = getattr(context, "add_cookies", None)
    if not callable(add):
        return
    try:
        await add(cookies)
    except Exception:  # noqa: BLE001 — ATS cookies are best-effort
        return


async def apply_on_landed_ats(
    parent: BasePortal,
    page: Any,
    job: ExtractedJob,
    resume_path: str,
    answers: dict,
    *,
    source: str = "linkedin_external",
) -> ApplyResult:
    """Continue apply on the company-site page that LinkedIn (or Indeed) opened."""
    url = getattr(getattr(page, "page", None), "url", "") or job.apply_url or ""
    ats = detect_ats(url)
    record_apply_channel(parent, kind=KIND_EXTERNAL, ats=ats, url=url)
    parent.recorder.add(
        "external_site",
        f"Opened {ats_display_name(ats)}",
        detail=url[:300],
        ats=ats,
        source=source,
    )
    adapter = spawn_child_adapter(parent, ats)
    cookies = list(getattr(adapter, "cookies", None) or [])
    if ats == ATS_WORKDAY:
        from app.automation.workday_session import cookies_for_workday_host, workday_tenant_host

        cookies = cookies_for_workday_host(cookies, workday_tenant_host(url))
        adapter.cookies = cookies
    await _inject_cookies(page, cookies)
    landed = ExtractedJob(
        external_id=job.external_id,
        title=job.title,
        company=job.company,
        location=job.location,
        salary=job.salary,
        experience=job.experience,
        description=job.description,
        skills=list(job.skills or []),
        apply_url=url or job.apply_url,
    )
    apply_landed = getattr(adapter, "apply_landed", None)
    if callable(apply_landed):
        result = await apply_landed(page, landed, resume_path, answers)
    else:
        result = await adapter.apply(page, landed, resume_path, answers)
    return tag_apply_result(result, kind=KIND_EXTERNAL, ats=ats, url=url)

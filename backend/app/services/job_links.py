"""Build a clickable listing URL from a stored job."""

from __future__ import annotations

from app.automation.portals.linkedin import canonical_job_url, linkedin_job_id


def listing_url_for(portal: str, apply_url: str = "", external_id: str = "") -> str:
    """Prefer the captured apply URL; for LinkedIn, reconstruct /jobs/view/{id}."""
    portal_key = (portal or "").strip().lower()
    url = (apply_url or "").strip()
    if url:
        if portal_key == "linkedin":
            return canonical_job_url(url) or url
        return url
    if portal_key == "linkedin":
        job_id = linkedin_job_id(external_id)
        if not job_id:
            tail = (external_id or "").rsplit("-", 1)[-1]
            job_id = linkedin_job_id(f"/jobs/view/{tail}/")
        if job_id:
            return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return ""

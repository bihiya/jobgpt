"""Detect whether Playwright can run in this process.

The slim Vercel/API install intentionally omits Playwright. Inline fetch/apply
fallbacks must check this before claiming automation started.
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.core.exceptions import ServiceUnavailableError

_PLAYWRIGHT_JOBS = frozenset({"fetch", "apply"})


@lru_cache(maxsize=1)
def playwright_available() -> bool:
    """Return True when the Playwright Python package can be imported."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


def job_requires_playwright(job_type: str) -> bool:
    return job_type in _PLAYWRIGHT_JOBS


def playwright_unavailable_message() -> str:
    if os.getenv("VERCEL"):
        return (
            "Browser automation (Playwright) is not available on this serverless API. "
            "Run the Docker Compose or Kubernetes stack for job fetch/apply workers."
        )
    return (
        "Playwright is not installed in this environment, so job fetch/apply cannot run. "
        "Install the full backend deps (`pip install -r backend/requirements.txt` and "
        "`playwright install chromium`) or use Docker Compose."
    )


def require_playwright_for_job(job_type: str) -> None:
    """Raise ServiceUnavailableError when a Playwright job cannot run here."""
    if not job_requires_playwright(job_type):
        return
    if playwright_available():
        return
    raise ServiceUnavailableError(
        playwright_unavailable_message(),
        code="PLAYWRIGHT_UNAVAILABLE",
    )

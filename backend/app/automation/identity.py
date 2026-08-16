"""Map the user profile onto ATS identity fields (name, email, phone, links)."""

from __future__ import annotations

import re
from typing import Any

_US_HINTS = (
    "united states",
    "usa",
    "u.s.",
    "u.s.a",
    "new york",
    "california",
    "texas",
    "washington",
    "seattle",
    "austin",
    "bay area",
    "san francisco",
    "los angeles",
    "chicago",
    "boston",
    "denver",
    "atlanta",
    "remote",
)


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in (full_name or "").strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def country_from_location(location: str) -> str:
    loc = (location or "").lower()
    if not loc:
        return ""
    if "india" in loc:
        return "India"
    if any(token in loc for token in ("united kingdom", "london", "england", "uk")):
        return "United Kingdom"
    if any(token in loc for token in ("canada", "toronto", "vancouver", "montreal")):
        return "Canada"
    if any(token in loc for token in _US_HINTS) or re.search(r"\b[A-Z]{2}\b", location or ""):
        return "United States of America"
    return ""


def identity_answers(user: Any | None) -> dict[str, str]:
    """Keys resolve_and_fill / Workday widgets match against (label or substring)."""
    if user is None:
        return {}
    profile = getattr(user, "profile", None)
    full = str(getattr(user, "full_name", "") or "").strip()
    first, last = split_full_name(full)
    email = str(getattr(user, "email", "") or "").strip()
    location = str(getattr(profile, "location", "") or "").strip() if profile else ""
    phone = str(getattr(profile, "phone", "") or "").strip() if profile else ""
    linkedin = str(getattr(profile, "linkedin_url", "") or "").strip() if profile else ""
    github = str(getattr(profile, "github_url", "") or "").strip() if profile else ""
    portfolio = str(getattr(profile, "portfolio_url", "") or "").strip() if profile else ""
    country = country_from_location(location)
    out: dict[str, str] = {}
    if first:
        out["First Name"] = first
        out["Given Name"] = first
        out["Legal First Name"] = first
    if last:
        out["Last Name"] = last
        out["Family Name"] = last
        out["Surname"] = last
        out["Legal Last Name"] = last
    if full:
        out["Full Name"] = full
        out["Legal Name"] = full
        out["Name"] = full
    if email:
        out["Email"] = email
        out["Email Address"] = email
        out["Work Email"] = email
    if phone:
        out["Phone"] = phone
        out["Phone Number"] = phone
        out["Mobile"] = phone
        out["Mobile Number"] = phone
        out["Telephone"] = phone
    if location:
        out["City"] = location
        out["Location"] = location
        out["Current location"] = location
        out["What is your current location?"] = location
    if country:
        out["Country"] = country
        out["Country/Region"] = country
        if "United States" in country:
            out["Country Phone Code"] = "United States of America (+1)"
            out["Phone Device Type"] = "Mobile"
    if linkedin:
        out["LinkedIn"] = linkedin
        out["LinkedIn URL"] = linkedin
        out["LinkedIn Profile"] = linkedin
    if github:
        out["GitHub"] = github
        out["GitHub URL"] = github
    if portfolio:
        out["Portfolio"] = portfolio
        out["Website"] = portfolio
        out["Personal Website"] = portfolio
    return {key: value for key, value in out.items() if value}

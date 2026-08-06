"""Classify recruiting emails: interview, JD, offer, rejection, assessment."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from app.models.enums import EmailEventType

INTERVIEW_RE = re.compile(
    r"\b(interview|onsite|on-site|phone screen|video call|meet with|calendar invite|"
    r"interview schedule|scheduled an interview|interview confirmation)\b",
    re.I,
)
JD_RE = re.compile(
    r"\b(job description|role description|position details|here.?s the jd|"
    r"attached (the )?jd|full description|job posting|requisition)\b",
    re.I,
)
OFFER_RE = re.compile(
    r"\b(offer letter|job offer|pleased to offer|extend(ing)? an offer|"
    r"compensation package|welcome to the team)\b",
    re.I,
)
REJECT_RE = re.compile(
    r"\b(unfortunately|not moving forward|other candidates|will not be|"
    r"regret to inform|application was unsuccessful|decided not to proceed)\b",
    re.I,
)
ASSESS_RE = re.compile(
    r"\b(hackerrank|codility|take.?home|online assessment|oa\b|coding challenge|"
    r"assessment link|complete the test)\b",
    re.I,
)
APP_UPDATE_RE = re.compile(
    r"\b(application received|we received your application|thank you for applying|"
    r"application (has been )?submitted|under review)\b",
    re.I,
)

DATE_PATTERNS = [
    re.compile(
        r"\b(?:on|for|at)?\s*"
        r"(?P<day>mon|tue|wed|thu|fri|sat|sun)[a-z]*"
        r"[,]?\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
        r"\s+(?P<dom>\d{1,2})(?:st|nd|rd|th)?"
        r"(?:[,]?\s+(?P<year>\d{4}))?"
        r"(?:\s+(?:at\s+)?(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?",
        re.I,
    ),
    re.compile(
        r"\b(?P<month>\d{1,2})/(?P<dom>\d{1,2})/(?P<year>\d{2,4})"
        r"(?:\s+(?:at\s+)?(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)?))?",
        re.I,
    ),
    re.compile(
        r"\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<dom>\d{2})"
        r"[ T](?P<time>\d{2}:\d{2})",
        re.I,
    ),
]

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


@dataclass
class ClassificationResult:
    event_type: EmailEventType
    confidence: float
    extracted: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


def classify_email(subject: str, body: str, sender: str = "") -> ClassificationResult:
    text = f"{subject}\n{body}"
    scores: list[tuple[EmailEventType, float, str]] = []

    if INTERVIEW_RE.search(text):
        scores.append((EmailEventType.INTERVIEW_SCHEDULE, 0.86, "interview keywords"))
    if JD_RE.search(text):
        scores.append((EmailEventType.JD_RECEIVED, 0.8, "job description keywords"))
    if OFFER_RE.search(text):
        scores.append((EmailEventType.OFFER, 0.9, "offer keywords"))
    if REJECT_RE.search(text):
        scores.append((EmailEventType.REJECTION, 0.82, "rejection keywords"))
    if ASSESS_RE.search(text):
        scores.append((EmailEventType.ASSESSMENT, 0.84, "assessment keywords"))
    if APP_UPDATE_RE.search(text):
        scores.append((EmailEventType.APPLICATION_UPDATE, 0.7, "application update keywords"))

    if not scores:
        return ClassificationResult(EmailEventType.OTHER, 0.2, {}, ["no recruiting signals"])

    scores.sort(key=lambda x: -x[1])
    event_type, confidence, reason = scores[0]
    extracted: dict = {}
    if event_type == EmailEventType.INTERVIEW_SCHEDULE:
        when = extract_datetime(text)
        if when:
            extracted["interview_at"] = when.isoformat()
        loc = extract_location(text)
        if loc:
            extracted["location"] = loc
        link = extract_meeting_link(text)
        if link:
            extracted["meeting_url"] = link
    if event_type == EmailEventType.ASSESSMENT:
        link = extract_url(text)
        if link:
            extracted["assessment_url"] = link
        when = extract_datetime(text)
        if when:
            extracted["due_at"] = when.isoformat()
    if event_type == EmailEventType.JD_RECEIVED:
        title = extract_role_title(subject, body)
        if title:
            extracted["job_title"] = title
    company = guess_company(sender, subject, body)
    if company:
        extracted["company"] = company
    title = extract_role_title(subject, body)
    if title and "job_title" not in extracted:
        extracted["job_title"] = title

    return ClassificationResult(
        event_type=event_type,
        confidence=confidence,
        extracted=extracted,
        reasons=[reason, *[s[2] for s in scores[1:3]]],
    )


def extract_datetime(text: str) -> datetime | None:
    now = datetime.utcnow()
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            gd = m.groupdict()
            if "month" in gd and gd["month"] and gd["month"].isalpha():
                month = MONTHS.get(gd["month"][:3].lower(), now.month)
                year = int(gd["year"]) if gd.get("year") else now.year
                day = int(gd["dom"])
                hour, minute = _parse_time(gd.get("time") or "10:00")
                return datetime(year, month, day, hour, minute)
            if gd.get("year") and gd.get("month") and gd.get("dom"):
                year = int(gd["year"])
                if year < 100:
                    year += 2000
                month = int(gd["month"])
                day = int(gd["dom"])
                hour, minute = _parse_time(gd.get("time") or "10:00")
                return datetime(year, month, day, hour, minute)
        except Exception:  # noqa: BLE001
            continue
    # ISO-ish fallback via email.utils if line looks like a date header
    for line in text.splitlines()[:40]:
        if re.search(r"\d{4}", line) and re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|/|-)", line, re.I):
            try:
                return parsedate_to_datetime(line.strip())
            except Exception:  # noqa: BLE001
                continue
    # relative: "tomorrow at 3pm"
    if re.search(r"\btomorrow\b", text, re.I):
        tm = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))", text, re.I)
        hour, minute = _parse_time(tm.group(1) if tm else "10:00")
        return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return None


def _parse_time(value: str) -> tuple[int, int]:
    value = (value or "10:00").strip().lower().replace(" ", "")
    m = re.match(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", value)
    if not m:
        return 10, 0
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return hour, minute


def extract_location(text: str) -> str:
    m = re.search(r"\b(?:location|where|office)\s*[:\-]\s*(.+)", text, re.I)
    if m:
        return m.group(1).strip()[:120]
    if re.search(r"\bzoom|google meet|teams|webex\b", text, re.I):
        return "Video"
    return ""


def extract_meeting_link(text: str) -> str:
    m = re.search(r"https?://[^\s<>\"]+(?:zoom\.us|meet\.google|teams\.microsoft)[^\s<>\"]*", text, re.I)
    return m.group(0) if m else extract_url(text)


def extract_url(text: str) -> str:
    m = re.search(r"https?://[^\s<>\"]+", text)
    return m.group(0).rstrip(").,]") if m else ""


def extract_role_title(subject: str, body: str) -> str:
    for pattern in [
        r"(?:for|role|position)\s*[:\-]?\s*([A-Z][\w /+&-]{3,60})",
        r"interview\s+for\s+([A-Z][\w /+&-]{3,60})",
        r"re:\s*(.+)",
    ]:
        m = re.search(pattern, subject, re.I)
        if m:
            return m.group(1).strip()[:80]
    m = re.search(r"(?:position|role)\s*[:\-]\s*(.+)", body, re.I)
    if m:
        return m.group(1).strip().split("\n")[0][:80]
    return ""


def guess_company(sender: str, subject: str, body: str) -> str:
    m = re.search(r"@([a-z0-9.-]+)\.", sender or "", re.I)
    if m:
        domain = m.group(1).split(".")[0]
        if domain not in {"gmail", "yahoo", "outlook", "hotmail", "icloud", "googlemail"}:
            return domain.replace("-", " ").title()
    m = re.search(r"\bat\s+([A-Z][\w&. -]{2,40})", subject)
    if m:
        return m.group(1).strip()
    return ""

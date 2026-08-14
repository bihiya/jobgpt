"""UTC datetime helpers for API payloads."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc


def iso_utc(value: datetime | None) -> str | None:
    """Serialize datetimes as ISO-8601 UTC with a Z suffix.

    Naive values are treated as UTC (how we store utcnow() today).
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(microsecond=0).isoformat() + "Z"
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

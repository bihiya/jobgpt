"""UTC ISO serialization for API timestamps."""

from datetime import datetime, timezone, timedelta

from app.core.times import iso_utc


def test_naive_datetime_treated_as_utc_with_z():
    assert iso_utc(datetime(2026, 8, 14, 8, 0, 0)) == "2026-08-14T08:00:00Z"


def test_aware_utc_uses_z_suffix():
    dt = datetime(2026, 8, 14, 8, 0, 0, tzinfo=timezone.utc)
    assert iso_utc(dt) == "2026-08-14T08:00:00Z"


def test_offset_converted_to_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    dt = datetime(2026, 8, 14, 13, 30, 0, tzinfo=ist)
    assert iso_utc(dt) == "2026-08-14T08:00:00Z"


def test_none():
    assert iso_utc(None) is None

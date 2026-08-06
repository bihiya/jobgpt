"""Unit tests for realtime event payload helpers."""

from app.events.realtime import build_event, user_channel


def test_user_channel_format():
    assert user_channel("abc123") == "user:abc123"


def test_build_event_shape():
    event = build_event(
        "job.matched",
        "u1",
        {"job_id": "j1", "match_score": 0.9},
        title="Matched",
        body="Good fit",
        severity="success",
    )
    assert event["event"] == "job.matched"
    assert event["user_id"] == "u1"
    assert event["data"]["job_id"] == "j1"
    assert event["title"] == "Matched"
    assert event["severity"] == "success"
    assert "ts" in event

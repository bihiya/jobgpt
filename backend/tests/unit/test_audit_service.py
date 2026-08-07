"""Audit log response helpers."""

from datetime import datetime
from enum import Enum

from app.models.automation_log import AuditLog
from app.services.audit_service import AuditService, build_field_changes, changes_metadata


class _Status(Enum):
    TRACKED = "tracked"


def test_audit_to_response_shape():
    service = AuditService()
    row = AuditLog.model_construct(
        id="507f1f77bcf86cd799439011",
        user_id="u1",
        actor_id="u1",
        action="job.tracked",
        message="Tracked Role",
        resource="job:j1",
        resource_type="job",
        resource_id="j1",
        job_id="j1",
        application_id="",
        source="user",
        severity="success",
        ip="",
        user_agent="",
        metadata={},
        created_at=datetime.utcnow(),
    )
    payload = service._to_response(row, actor_name="Lav Gupta")
    assert payload.action == "job.tracked"
    assert payload.job_id == "j1"
    assert payload.user_id == "u1"
    assert payload.severity == "success"
    assert "Tracked" in payload.message
    assert payload.actor_name == "Lav Gupta"
    assert "Lav Gupta" in payload.summary
    assert payload.outcome == "Passed"
    assert payload.next_step


def test_build_field_changes_includes_before_after():
    changes = build_field_changes(
        {"auto_apply": False, "match_threshold": 0.7, "updated_at": "old"},
        {"auto_apply": True, "match_threshold": 0.7, "updated_at": "new"},
    )
    assert changes == [{"field": "auto_apply", "from": False, "to": True}]


def test_build_field_changes_normalizes_enums():
    changes = build_field_changes({"status": _Status.TRACKED}, {"status": "tracked"})
    assert changes == []


def test_changes_metadata_shape():
    meta = changes_metadata(
        {"headless": True},
        {"headless": False, "updated_at": datetime.utcnow()},
        extra={"portal": "linkedin"},
    )
    assert meta["fields"] == ["headless"]
    assert meta["changes"] == [{"field": "headless", "from": True, "to": False}]
    assert meta["portal"] == "linkedin"

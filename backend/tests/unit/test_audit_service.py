"""Audit log response helpers."""

from datetime import datetime

from app.models.automation_log import AuditLog
from app.services.audit_service import AuditService


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
    payload = service._to_response(row)
    assert payload.action == "job.tracked"
    assert payload.job_id == "j1"
    assert payload.user_id == "u1"
    assert payload.severity == "success"
    assert "Tracked" in payload.message

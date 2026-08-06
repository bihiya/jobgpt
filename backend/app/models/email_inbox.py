"""Inbound email account + classified messages for interview/JD sync."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from beanie import Document, Indexed
from pydantic import Field

from app.models.enums import EmailEventType, EmailSyncStatus


class EmailAccount(Document):
    user_id: Annotated[str, Indexed()]
    label: str = "Primary"
    email_address: str = ""
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    username: str = ""
    # Fernet blob (same vault as portal sessions)
    password_encrypted: str = ""
    use_ssl: bool = True
    mailbox: str = "INBOX"
    enabled: bool = True
    auto_apply: bool = True  # auto-update jobs/reminders on classify
    last_sync_at: datetime | None = None
    last_uid: int = 0
    last_error: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "email_accounts"
        indexes = [[("user_id", 1), ("email_address", 1)]]


class InboundEmail(Document):
    user_id: Annotated[str, Indexed()]
    account_id: Annotated[str, Indexed()] = ""
    message_id: Annotated[str, Indexed()] = ""
    uid: int = 0
    subject: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    received_at: datetime | None = None
    snippet: str = ""
    body_text: str = ""
    event_type: EmailEventType = EmailEventType.OTHER
    confidence: float = 0.0
    matched_job_id: str = ""
    matched_company: str = ""
    extracted: dict[str, Any] = Field(default_factory=dict)
    # e.g. interview_at, location, job_title, assessment_deadline
    sync_status: EmailSyncStatus = EmailSyncStatus.PENDING
    applied_actions: list[str] = Field(default_factory=list)
    raw_headers: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "inbound_emails"
        indexes = [
            [("user_id", 1), ("received_at", -1)],
            [("user_id", 1), ("event_type", 1)],
            [("user_id", 1), ("message_id", 1)],
        ]

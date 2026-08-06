"""Shared enumerations for domain models."""

from __future__ import annotations

from app.compat import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class PortalName(StrEnum):
    LINKEDIN = "linkedin"
    NAUKRI = "naukri"
    INDEED = "indeed"
    FOUNDIT = "foundit"
    WELLFOUND = "wellfound"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    SMARTRECRUITERS = "smartrecruiters"
    ORACLE = "oracle"
    SAP_SUCCESSFACTORS = "sap_successfactors"
    TALEO = "taleo"


class PortalStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class CompanyStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class CompanyPlatform(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    CUSTOM = "custom"


class JobStatus(StrEnum):
    NEW = "new"
    TRACKED = "tracked"
    MATCHED = "matched"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    IGNORED = "ignored"
    DUPLICATE = "duplicate"


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    FOLLOW_UP = "follow_up"
    NEEDS_INPUT = "needs_input"  # unknown form question — pause for user
    NEEDS_OTP = "needs_otp"  # portal 2FA — wait for user OTP


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AlertChannel(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class ReportFormat(StrEnum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ReportStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"

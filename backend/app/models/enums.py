"""Shared enumerations for domain models."""

from enum import StrEnum


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
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    IGNORED = "ignored"


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class ReportFormat(StrEnum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ReportStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"

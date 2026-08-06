"""Beanie document model registry."""

from app.models.application import Application
from app.models.automation_log import AuditLog, AutomationLog
from app.models.company import Company
from app.models.job import Job
from app.models.notification import Notification
from app.models.portal import Portal
from app.models.report import Report
from app.models.resume import Resume
from app.models.scheduler_job import SchedulerJob
from app.models.settings import UserSettings
from app.models.user import RefreshToken, Role, User

DOCUMENT_MODELS = [
    User,
    Role,
    RefreshToken,
    Resume,
    Company,
    Portal,
    Job,
    Application,
    AutomationLog,
    AuditLog,
    Report,
    Notification,
    UserSettings,
    SchedulerJob,
]

__all__ = [
    "DOCUMENT_MODELS",
    "User",
    "Role",
    "RefreshToken",
    "Resume",
    "Company",
    "Portal",
    "Job",
    "Application",
    "AutomationLog",
    "AuditLog",
    "Report",
    "Notification",
    "UserSettings",
    "SchedulerJob",
]

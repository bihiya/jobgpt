"""Service factories for FastAPI dependency injection."""

from app.services.application_service import ApplicationService
from app.services.auth_service import AuthService
from app.services.automation_service import AutomationService
from app.services.company_service import CompanyService
from app.services.job_service import JobService
from app.services.portal_service import PortalService
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService


def get_auth_service() -> AuthService:
    return AuthService()


def get_user_service() -> UserService:
    return UserService()


def get_job_service() -> JobService:
    return JobService()


def get_application_service() -> ApplicationService:
    return ApplicationService()


def get_company_service() -> CompanyService:
    return CompanyService()


def get_portal_service() -> PortalService:
    return PortalService()


def get_report_service() -> ReportService:
    return ReportService()


def get_automation_service() -> AutomationService:
    return AutomationService()


def get_settings_service() -> SettingsService:
    return SettingsService()

"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.applications.router import router as applications_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.automation.router import router as automation_router
from app.api.v1.companies.router import router as companies_router
from app.api.v1.jobs.router import router as jobs_router
from app.api.v1.portals.router import router as portals_router
from app.api.v1.reports.router import router as reports_router
from app.api.v1.scheduler.router import router as scheduler_router
from app.api.v1.settings.router import router as settings_router
from app.api.v1.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(jobs_router)
api_router.include_router(applications_router)
api_router.include_router(companies_router)
api_router.include_router(portals_router)
api_router.include_router(reports_router)
api_router.include_router(automation_router)
api_router.include_router(settings_router)
api_router.include_router(scheduler_router)

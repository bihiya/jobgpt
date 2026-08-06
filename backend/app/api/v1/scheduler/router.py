"""Scheduler job endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.models.scheduler_job import SchedulerJob
from app.models.user import User

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class SchedulerJobUpdate(BaseModel):
    is_enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=60, le=86400)


class SchedulerJobResponse(BaseModel):
    id: str
    name: str
    job_type: str
    interval_seconds: int
    is_enabled: bool
    last_run_at: str | None
    next_run_at: str | None


async def _ensure_defaults(user_id: str) -> list[SchedulerJob]:
    existing = await SchedulerJob.find({"user_id": user_id}).to_list()
    if existing:
        return existing
    defaults = [
        ("Fetch Jobs", "fetch"),
        ("Match Jobs", "match"),
        ("Apply Jobs", "apply"),
        ("Generate Reports", "report"),
    ]
    created = []
    for name, job_type in defaults:
        job = SchedulerJob(
            user_id=user_id,
            name=name,
            job_type=job_type,
            interval_seconds=settings.scheduler_interval_seconds,
            is_enabled=True,
        )
        await job.insert()
        created.append(job)
    return created


@router.get("/jobs", response_model=list[SchedulerJobResponse])
async def list_scheduler_jobs(user: User = Depends(get_current_user)):
    jobs = await _ensure_defaults(str(user.id))
    return [
        SchedulerJobResponse(
            id=str(j.id),
            name=j.name,
            job_type=j.job_type,
            interval_seconds=j.interval_seconds,
            is_enabled=j.is_enabled,
            last_run_at=j.last_run_at.isoformat() if j.last_run_at else None,
            next_run_at=j.next_run_at.isoformat() if j.next_run_at else None,
        )
        for j in jobs
    ]


@router.patch("/jobs/{job_id}", response_model=SchedulerJobResponse)
async def update_scheduler_job(
    job_id: str,
    payload: SchedulerJobUpdate,
    user: User = Depends(get_current_user),
):
    job = await SchedulerJob.get(job_id)
    if not job or job.user_id != str(user.id):
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Scheduler job not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(job, key, value)
    await job.save()
    return SchedulerJobResponse(
        id=str(job.id),
        name=job.name,
        job_type=job.job_type,
        interval_seconds=job.interval_seconds,
        is_enabled=job.is_enabled,
        last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
        next_run_at=job.next_run_at.isoformat() if job.next_run_at else None,
    )


# silence unused import warning for datetime in type checkers that require presence
_ = datetime

"""Job tracking endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user
from app.models.enums import JobStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.job import (
    JobFilterParams,
    JobIngestRequest,
    JobMoveRequest,
    JobMoveResponse,
    JobResponse,
    JobUpdateRequest,
)
from app.dependencies.services import get_job_service
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/ingest", response_model=JobResponse, status_code=201)
async def ingest_job(
    payload: JobIngestRequest,
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    """Chrome extension / share-to-JobPilot ingest endpoint."""
    return await service.ingest_external(str(user.id), payload)


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    q: str | None = None,
    portal: str | None = None,
    company: str | None = None,
    status: JobStatus | None = None,
    min_score: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "fetched_at",
    sort_dir: str = "desc",
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    params = JobFilterParams(
        q=q,
        portal=portal,
        company=company,
        status=status,
        min_score=min_score,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return await service.list_jobs(str(user.id), params)


@router.get("/tracked", response_model=PaginatedResponse[JobResponse])
async def tracked_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.list_by_statuses(str(user.id), [JobStatus.TRACKED, JobStatus.MATCHED], page, page_size)


@router.get("/applied", response_model=PaginatedResponse[JobResponse])
async def applied_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.list_by_statuses(str(user.id), [JobStatus.APPLIED, JobStatus.APPLYING], page, page_size)


@router.get("/history", response_model=PaginatedResponse[JobResponse])
async def job_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.list_by_statuses(
        str(user.id),
        [JobStatus.APPLIED, JobStatus.FAILED, JobStatus.IGNORED, JobStatus.INTERVIEW, JobStatus.OFFER, JobStatus.SHORTLISTED],
        page,
        page_size,
    )


@router.get("/pipeline")
async def job_pipeline(
    per_column: int = Query(40, ge=5, le=100),
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.pipeline(str(user.id), per_column=per_column)


@router.post("/{job_id}/move", response_model=JobMoveResponse)
async def move_job(
    job_id: str,
    payload: JobMoveRequest,
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    """Move a job on the pipeline. Dropping onto queued starts auto-apply."""
    return await service.move_to_column(
        str(user.id),
        job_id,
        payload.column,
        resume_id=payload.resume_id,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.get(str(user.id), job_id)


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    payload: JobUpdateRequest,
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.update(str(user.id), job_id, payload)


@router.post("/{job_id}/track", response_model=JobResponse)
async def track_job(
    job_id: str,
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.track(str(user.id), job_id)


@router.post("/{job_id}/ignore", response_model=JobResponse)
async def ignore_job(
    job_id: str,
    user: User = Depends(get_current_user),
    service: JobService = Depends(get_job_service),
):
    return await service.ignore(str(user.id), job_id)

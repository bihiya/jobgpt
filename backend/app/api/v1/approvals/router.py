"""Human-in-the-loop approval endpoints (PWA-friendly)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.enums import ApprovalStatus
from app.models.user import User
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecisionRequest(BaseModel):
    note: str = ""


class BatchApproveRequest(BaseModel):
    min_score: float | None = Field(default=None, ge=0, le=1)
    portal: str | None = None
    approval_ids: list[str] | None = None
    limit: int | None = Field(default=None, ge=1, le=100)
    note: str = ""
    approve: bool = True


@router.get("")
async def list_approvals(
    status: ApprovalStatus | None = ApprovalStatus.PENDING,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    return await ApprovalService().list(str(user.id), status, page, page_size)


@router.get("/blockers")
async def list_blockers(user: User = Depends(get_current_user)):
    """OTP / unknown-question pauses needing human help."""
    return await ApprovalService().list_blockers(str(user.id))


@router.post("/batch")
async def batch_approve(
    payload: BatchApproveRequest,
    user: User = Depends(get_current_user),
):
    return await ApprovalService().batch_decide(
        str(user.id),
        approve=payload.approve,
        min_score=payload.min_score,
        portal=payload.portal,
        approval_ids=payload.approval_ids,
        limit=payload.limit,
        note=payload.note,
    )


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: str,
    payload: DecisionRequest | None = None,
    user: User = Depends(get_current_user),
):
    return await ApprovalService().decide(
        str(user.id), approval_id, approve=True, note=(payload.note if payload else "")
    )


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: str,
    payload: DecisionRequest | None = None,
    user: User = Depends(get_current_user),
):
    return await ApprovalService().decide(
        str(user.id), approval_id, approve=False, note=(payload.note if payload else "")
    )

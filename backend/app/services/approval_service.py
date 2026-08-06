"""Human-in-the-loop approval queue."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil

from app.core.exceptions import NotFoundError
from app.core.kafka import publish
from app.events.realtime import emit_realtime
from app.models.approval import Approval
from app.models.enums import ApprovalStatus, JobStatus
from app.models.job import Job
from app.schemas.common import PaginatedResponse
from app.services.notifications.dispatcher import NotificationDispatcher


class ApprovalService:
    def __init__(self) -> None:
        self.notifier = NotificationDispatcher()

    async def enqueue(self, user_id: str, job: Job, summary: str = "") -> Approval:
        existing = await Approval.find_one(
            {"user_id": user_id, "job_id": str(job.id), "status": ApprovalStatus.PENDING}
        )
        if existing:
            return existing
        approval = Approval(
            user_id=user_id,
            job_id=str(job.id),
            match_score=job.match_score,
            summary=summary or f"{job.title} at {job.company}",
            expires_at=datetime.utcnow() + timedelta(days=3),
        )
        await approval.insert()
        job.status = JobStatus.AWAITING_APPROVAL
        job.updated_at = datetime.utcnow()
        await job.save()
        await self.notifier.dispatch(
            user_id,
            event="approval.needed",
            title="Approval needed",
            body=f"Review {job.title} at {job.company} (score {int(job.match_score * 100)}%)",
            type_="warning",
            metadata={"job_id": str(job.id), "approval_id": str(approval.id)},
        )
        return approval

    async def list(
        self,
        user_id: str,
        status: ApprovalStatus | None = ApprovalStatus.PENDING,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[dict]:
        filters: dict = {"user_id": user_id}
        if status:
            filters["status"] = status
        total = await Approval.find(filters).count()
        items = (
            await Approval.find(filters)
            .sort([("created_at", -1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return PaginatedResponse(
            items=[
                {
                    "id": str(a.id),
                    "job_id": a.job_id,
                    "status": a.status,
                    "match_score": a.match_score,
                    "summary": a.summary,
                    "created_at": a.created_at.isoformat(),
                    "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                }
                for a in items
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if page_size else 0,
        )

    async def decide(
        self,
        user_id: str,
        approval_id: str,
        *,
        approve: bool,
        note: str = "",
    ) -> dict:
        approval = await Approval.get(approval_id)
        if not approval or approval.user_id != user_id:
            raise NotFoundError("Approval not found")
        if approval.status != ApprovalStatus.PENDING:
            raise NotFoundError("Approval already decided")

        approval.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        approval.decided_at = datetime.utcnow()
        approval.note = note
        await approval.save()

        job = await Job.get(approval.job_id)
        if job:
            if approve:
                job.status = JobStatus.APPROVED
                await job.save()
                await publish(
                    "job.apply",
                    {
                        "user_id": user_id,
                        "job_id": str(job.id),
                        "approval_id": str(approval.id),
                        "auto": False,
                    },
                    key=user_id,
                )
            else:
                job.status = JobStatus.REJECTED
                await job.save()
        await emit_realtime(
            user_id,
            "approval.decided",
            {
                "approval_id": str(approval.id),
                "job_id": approval.job_id,
                "status": approval.status,
                "approved": approve,
            },
            title="Approval updated",
            body="Approved — applying now" if approve else "Rejected",
            severity="success" if approve else "info",
        )
        return {"id": str(approval.id), "status": approval.status}

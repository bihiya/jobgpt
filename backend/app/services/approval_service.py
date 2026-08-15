"""Human-in-the-loop approval queue."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil

from app.core.exceptions import NotFoundError, RateLimitError
from app.core.times import iso_utc
from app.events.realtime import emit_realtime
from app.models.application import Application
from app.models.approval import Approval
from app.models.enums import ApplicationStatus, ApprovalStatus, JobStatus
from app.models.job import Job
from app.producers.events import publish_job_apply
from app.repository.settings_repository import SettingsRepository
from app.schemas.common import PaginatedResponse
from app.services.apply_rate_limit import ApplyRateLimiter
from app.services.notifications.dispatcher import NotificationDispatcher


class ApprovalService:
    def __init__(self) -> None:
        self.notifier = NotificationDispatcher()
        self.settings = SettingsRepository()
        self.rate_limiter = ApplyRateLimiter()

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
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "approval.needed",
            message=f"Approval needed for {job.title}",
            job_id=str(job.id),
            resource_type="approval",
            resource_id=str(approval.id),
            source="worker",
            severity="warning",
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
        enriched = []
        for a in items:
            job = await Job.get(a.job_id)
            enriched.append(
                {
                    "id": str(a.id),
                    "job_id": a.job_id,
                    "status": a.status,
                    "match_score": a.match_score,
                    "summary": a.summary,
                    "portal": getattr(job, "portal", "") if job else "",
                    "title": getattr(job, "title", "") if job else "",
                    "company": getattr(job, "company", "") if job else "",
                    "created_at": a.created_at.isoformat(),
                    "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                }
            )
        return PaginatedResponse(
            items=enriched,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if page_size else 0,
        )

    async def list_blockers(self, user_id: str) -> list[dict]:
        """OTP / unknown-question / captcha / login-expired items needing human help."""
        apps = (
            await Application.find(
                {
                    "user_id": user_id,
                    "status": {
                        "$in": [ApplicationStatus.NEEDS_INPUT, ApplicationStatus.NEEDS_OTP]
                    },
                }
            )
            .sort([("updated_at", -1)])
            .limit(50)
            .to_list()
        )
        out: list[dict] = []
        for app in apps:
            job = await Job.get(app.job_id)
            blocker = app.blocker_type or (
                "otp" if app.status == ApplicationStatus.NEEDS_OTP else "unknown_question"
            )
            # Captcha pauses often surface as needs_otp / session step metadata
            steps = app.session_steps or []
            if any((s.get("key") == "captcha" and s.get("status") in {"warn", "error"}) for s in steps):
                if blocker != "otp":
                    blocker = "captcha"
            out.append(
                {
                    "id": f"app-{app.id}",
                    "application_id": str(app.id),
                    "job_id": app.job_id,
                    "status": app.status,
                    "blocker_type": blocker,
                    "unknown_questions": app.unknown_questions,
                    "error_message": app.error_message,
                    "session_steps": app.session_steps,
                    "portal": getattr(job, "portal", "") if job else "",
                    "title": getattr(job, "title", "") if job else "",
                    "company": getattr(job, "company", "") if job else "",
                    "updated_at": app.updated_at.isoformat() if app.updated_at else None,
                }
            )

        # Portal session / health blockers (login expired)
        from app.models.portal import Portal

        portals = await Portal.find({"user_id": user_id}).to_list()
        for portal in portals:
            health = getattr(portal, "health", None)
            auto_paused = bool(getattr(health, "auto_paused", False)) if health else False
            from app.services.session_vault import portal_has_auth_session

            has_session = portal_has_auth_session(portal)
            last_error = (getattr(health, "last_error", "") if health else "") or ""
            login_expired = (
                auto_paused
                or (not has_session and bool(portal.credentials.username))
                or "login" in last_error.lower()
                or "auth" in last_error.lower()
                or "session" in last_error.lower()
            )
            if not login_expired and not auto_paused:
                continue
            out.append(
                {
                    "id": f"portal-{portal.id}",
                    "application_id": "",
                    "job_id": "",
                    "portal_id": str(portal.id),
                    "status": "login_expired" if login_expired else "portal_paused",
                    "blocker_type": "login_expired" if login_expired else "portal_paused",
                    "unknown_questions": [],
                    "error_message": last_error
                    or getattr(health, "paused_reason", "")
                    or "Portal session expired — re-authenticate",
                    "session_steps": [],
                    "portal": portal.name.value if hasattr(portal.name, "value") else str(portal.name),
                    "title": f"{portal.name} connection",
                    "company": "",
                    "updated_at": iso_utc(
                        getattr(portal, "session_updated_at", None) or portal.updated_at
                    ),
                }
            )
        return out

    async def decide(
        self,
        user_id: str,
        approval_id: str,
        *,
        approve: bool,
        note: str = "",
        skip_rate_limit: bool = False,
    ) -> dict:
        approval = await Approval.get(approval_id)
        if not approval or approval.user_id != user_id:
            raise NotFoundError("Approval not found")
        if approval.status != ApprovalStatus.PENDING:
            raise NotFoundError("Approval already decided")

        job = await Job.get(approval.job_id)
        if approve and not skip_rate_limit:
            settings = await self.settings.get_or_create(user_id)
            portal = getattr(job, "portal", "") if job else ""
            limit = await self.rate_limiter.check(user_id, settings, portal=portal)
            if not limit.allowed:
                raise RateLimitError(limit.reason)

        approval.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        approval.decided_at = datetime.utcnow()
        approval.note = note
        await approval.save()

        if job:
            if approve:
                job.status = JobStatus.APPROVED
                await job.save()
                await publish_job_apply(
                    user_id,
                    str(job.id),
                    approval_id=str(approval.id),
                    auto=False,
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
        from app.services.audit_service import audit_event

        job_label = (job.title if job else "") or approval.summary or approval.job_id
        await audit_event(
            user_id,
            "approval.approved" if approve else "approval.rejected",
            message=(
                f"Approved “{job_label}” — apply will start next"
                if approve
                else f"Rejected “{job_label}” — will not apply"
            ),
            job_id=approval.job_id,
            resource_type="approval",
            resource_id=str(approval.id),
            severity="success" if approve else "warning",
            metadata={
                "note": note,
                "outcome": "Passed" if approve else "Stopped",
                "next_step": (
                    "Watch Automation for apply progress."
                    if approve
                    else "No further action on this job."
                ),
            },
        )
        return {"id": str(approval.id), "status": approval.status}

    async def batch_decide(
        self,
        user_id: str,
        *,
        approve: bool = True,
        min_score: float | None = None,
        portal: str | None = None,
        approval_ids: list[str] | None = None,
        limit: int | None = None,
        note: str = "",
    ) -> dict:
        """
        Smart batch approve — e.g. approve all ≥85% LinkedIn Easy Apply
        respecting daily caps + cooldown.
        """
        settings = await self.settings.get_or_create(user_id)
        threshold = min_score if min_score is not None else float(
            getattr(settings, "batch_min_score", 0.85) or 0.85
        )
        max_batch = limit if limit is not None else int(
            getattr(settings, "max_applications_per_day", 15) or 15
        )

        filters: dict = {"user_id": user_id, "status": ApprovalStatus.PENDING}
        pending = await Approval.find(filters).sort([("match_score", -1)]).to_list()
        if approval_ids:
            allowed = set(approval_ids)
            pending = [a for a in pending if str(a.id) in allowed]

        decided: list[dict] = []
        skipped: list[dict] = []

        for approval in pending:
            if len(decided) >= max_batch:
                skipped.append({"id": str(approval.id), "reason": "batch_limit"})
                continue
            if approval.match_score < threshold:
                skipped.append({"id": str(approval.id), "reason": "below_min_score"})
                continue
            job = await Job.get(approval.job_id)
            if portal and job and getattr(job, "portal", "") != portal:
                skipped.append({"id": str(approval.id), "reason": "portal_mismatch"})
                continue
            try:
                result = await self.decide(
                    user_id,
                    str(approval.id),
                    approve=approve,
                    note=note or f"batch≥{int(threshold * 100)}%",
                    skip_rate_limit=False,
                )
                decided.append(result)
            except RateLimitError as exc:
                skipped.append({"id": str(approval.id), "reason": str(exc)})
                break
            except Exception as exc:  # noqa: BLE001
                skipped.append({"id": str(approval.id), "reason": str(exc)})

        await emit_realtime(
            user_id,
            "approval.batch",
            {
                "approved": len(decided),
                "skipped": len(skipped),
                "min_score": threshold,
                "portal": portal or "",
            },
            title="Batch approve complete",
            body=f"{len(decided)} approved, {len(skipped)} skipped",
            severity="success" if decided else "warning",
        )
        return {
            "approved": decided,
            "skipped": skipped,
            "min_score": threshold,
            "portal": portal,
            "count": len(decided),
        }

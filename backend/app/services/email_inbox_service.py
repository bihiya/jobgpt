"""Connect IMAP accounts, sync + classify recruiting mail, update pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.events.realtime import emit_realtime
from app.models.email_inbox import EmailAccount, InboundEmail
from app.models.enums import EmailEventType, EmailSyncStatus, JobStatus
from app.models.job import Job
from app.models.reminder import Reminder
from app.schemas.common import PaginatedResponse
from app.services.email_classifier import classify_email
from app.services.imap_client import ImapInboxClient
from app.services.session_vault import decrypt_blob, encrypt_blob

logger = get_logger(__name__)


class EmailInboxService:
    def _to_account(self, acc: EmailAccount) -> dict:
        return {
            "id": str(acc.id),
            "label": acc.label,
            "email_address": acc.email_address,
            "imap_host": acc.imap_host,
            "imap_port": acc.imap_port,
            "username": acc.username,
            "use_ssl": acc.use_ssl,
            "mailbox": acc.mailbox,
            "enabled": acc.enabled,
            "auto_apply": acc.auto_apply,
            "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
            "last_error": acc.last_error,
            "has_password": bool(acc.password_encrypted),
        }

    def _to_message(self, msg: InboundEmail) -> dict:
        return {
            "id": str(msg.id),
            "account_id": msg.account_id,
            "message_id": msg.message_id,
            "subject": msg.subject,
            "sender": msg.sender,
            "recipients": msg.recipients,
            "received_at": msg.received_at.isoformat() if msg.received_at else None,
            "snippet": msg.snippet,
            "body_text": msg.body_text[:4000],
            "event_type": msg.event_type,
            "confidence": msg.confidence,
            "matched_job_id": msg.matched_job_id,
            "matched_company": msg.matched_company,
            "extracted": msg.extracted,
            "sync_status": msg.sync_status,
            "applied_actions": msg.applied_actions,
            "created_at": msg.created_at.isoformat(),
        }

    async def list_accounts(self, user_id: str) -> list[dict]:
        items = await EmailAccount.find({"user_id": user_id}).to_list()
        return [self._to_account(a) for a in items]

    async def upsert_account(self, user_id: str, payload: dict) -> dict:
        account_id = payload.get("id")
        password = payload.get("password") or ""
        if account_id:
            acc = await EmailAccount.get(account_id)
            if not acc or acc.user_id != user_id:
                raise NotFoundError("Email account not found")
        else:
            if not payload.get("username") or not password:
                raise ValidationAppError("username and password are required")
            acc = EmailAccount(user_id=user_id)

        for key in (
            "label",
            "email_address",
            "imap_host",
            "imap_port",
            "username",
            "use_ssl",
            "mailbox",
            "enabled",
            "auto_apply",
        ):
            if key in payload and payload[key] is not None:
                setattr(acc, key, payload[key])
        if not acc.email_address:
            acc.email_address = acc.username
        if password:
            acc.password_encrypted = encrypt_blob(password)
        acc.updated_at = datetime.utcnow()
        if acc.id:
            await acc.save()
        else:
            await acc.insert()
        return self._to_account(acc)

    async def delete_account(self, user_id: str, account_id: str) -> None:
        acc = await EmailAccount.get(account_id)
        if not acc or acc.user_id != user_id:
            raise NotFoundError("Email account not found")
        await acc.delete()

    async def test_account(self, user_id: str, account_id: str) -> dict:
        client = await self._client_for(user_id, account_id)
        return client.test_connection()

    async def _client_for(self, user_id: str, account_id: str) -> ImapInboxClient:
        acc = await EmailAccount.get(account_id)
        if not acc or acc.user_id != user_id:
            raise NotFoundError("Email account not found")
        password = decrypt_blob(acc.password_encrypted)
        if not isinstance(password, str) or not password:
            raise ValidationAppError("Account password missing — reconnect IMAP")
        return ImapInboxClient(
            host=acc.imap_host,
            port=acc.imap_port,
            username=acc.username,
            password=password,
            use_ssl=acc.use_ssl,
            mailbox=acc.mailbox,
        )

    async def list_messages(
        self,
        user_id: str,
        *,
        event_type: EmailEventType | None = None,
        status: EmailSyncStatus | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> PaginatedResponse[dict]:
        filters: dict = {"user_id": user_id}
        if event_type:
            filters["event_type"] = event_type
        if status:
            filters["sync_status"] = status
        total = await InboundEmail.find(filters).count()
        items = (
            await InboundEmail.find(filters)
            .sort([("received_at", -1), ("created_at", -1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
            .to_list()
        )
        return PaginatedResponse(
            items=[self._to_message(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if page_size else 0,
        )

    async def sync_account(self, user_id: str, account_id: str, *, limit: int = 40) -> dict:
        acc = await EmailAccount.get(account_id)
        if not acc or acc.user_id != user_id:
            raise NotFoundError("Email account not found")
        client = await self._client_for(user_id, account_id)
        try:
            fetched = client.fetch_since_uid(acc.last_uid, limit=limit)
        except Exception as exc:  # noqa: BLE001
            acc.last_error = str(exc)[:500]
            acc.updated_at = datetime.utcnow()
            await acc.save()
            logger.warning("imap_sync_failed", account_id=account_id, error=str(exc))
            raise ValidationAppError(f"IMAP sync failed: {exc}") from exc

        created = 0
        applied = 0
        max_uid = acc.last_uid
        for item in fetched:
            max_uid = max(max_uid, item.uid)
            existing = await InboundEmail.find_one(
                {"user_id": user_id, "message_id": item.message_id}
            )
            if existing:
                continue
            classification = classify_email(item.subject, item.body_text, item.sender)
            job = await self._match_job(user_id, classification.extracted, item.subject, item.body_text)
            doc = InboundEmail(
                user_id=user_id,
                account_id=account_id,
                message_id=item.message_id,
                uid=item.uid,
                subject=item.subject,
                sender=item.sender,
                recipients=item.recipients,
                received_at=item.received_at or datetime.utcnow(),
                snippet=item.snippet,
                body_text=item.body_text,
                event_type=classification.event_type,
                confidence=classification.confidence,
                matched_job_id=str(job.id) if job else "",
                matched_company=classification.extracted.get("company", ""),
                extracted={**classification.extracted, "reasons": classification.reasons},
                sync_status=EmailSyncStatus.PENDING,
                raw_headers=item.headers,
            )
            await doc.insert()
            created += 1
            if acc.auto_apply and classification.event_type != EmailEventType.OTHER:
                await self.apply_message(user_id, str(doc.id), auto=True)
                applied += 1

        acc.last_uid = max_uid
        acc.last_sync_at = datetime.utcnow()
        acc.last_error = ""
        acc.updated_at = datetime.utcnow()
        await acc.save()
        await emit_realtime(
            user_id,
            "email.synced",
            {"account_id": account_id, "created": created, "applied": applied},
            title="Email inbox synced",
            body=f"{created} new · {applied} auto-applied",
            severity="success" if created else "info",
        )
        return {"created": created, "applied": applied, "fetched": len(fetched)}

    async def sync_all(self, user_id: str | None = None) -> dict:
        filters: dict = {"enabled": True}
        if user_id:
            filters["user_id"] = user_id
        accounts = await EmailAccount.find(filters).to_list()
        totals = {"accounts": 0, "created": 0, "applied": 0, "errors": 0}
        for acc in accounts:
            try:
                result = await self.sync_account(acc.user_id, str(acc.id))
                totals["accounts"] += 1
                totals["created"] += result["created"]
                totals["applied"] += result["applied"]
            except Exception as exc:  # noqa: BLE001
                totals["errors"] += 1
                logger.warning("email_sync_all_error", account_id=str(acc.id), error=str(exc))
        return totals

    async def ingest_raw(self, user_id: str, payload: dict) -> dict:
        """Manual / webhook ingest without IMAP (forwarded emails, demos)."""
        subject = payload.get("subject") or ""
        body = payload.get("body_text") or payload.get("body") or ""
        sender = payload.get("sender") or ""
        if not subject and not body:
            raise ValidationAppError("subject or body_text required")
        classification = classify_email(subject, body, sender)
        job = await self._match_job(user_id, classification.extracted, subject, body)
        message_id = payload.get("message_id") or f"ingest-{datetime.utcnow().timestamp()}"
        existing = await InboundEmail.find_one({"user_id": user_id, "message_id": message_id})
        if existing:
            return self._to_message(existing)
        doc = InboundEmail(
            user_id=user_id,
            account_id=payload.get("account_id") or "",
            message_id=message_id,
            subject=subject,
            sender=sender,
            recipients=payload.get("recipients") or [],
            received_at=datetime.utcnow(),
            snippet=(body or subject)[:240],
            body_text=body[:20000],
            event_type=classification.event_type,
            confidence=classification.confidence,
            matched_job_id=str(job.id) if job else "",
            matched_company=classification.extracted.get("company", ""),
            extracted={**classification.extracted, "reasons": classification.reasons},
            sync_status=EmailSyncStatus.PENDING,
        )
        await doc.insert()
        auto = bool(payload.get("auto_apply", True))
        if auto and classification.event_type != EmailEventType.OTHER:
            await self.apply_message(user_id, str(doc.id), auto=True)
        await emit_realtime(
            user_id,
            "email.ingested",
            {
                "email_id": str(doc.id),
                "event_type": doc.event_type,
                "subject": doc.subject,
            },
            title="Email classified",
            body=f"{doc.event_type}: {doc.subject[:80]}",
            severity="info",
        )
        refreshed = await InboundEmail.get(doc.id)
        return self._to_message(refreshed or doc)

    async def apply_message(self, user_id: str, email_id: str, *, auto: bool = False) -> dict:
        msg = await InboundEmail.get(email_id)
        if not msg or msg.user_id != user_id:
            raise NotFoundError("Email not found")
        actions: list[str] = []
        job = None
        if msg.matched_job_id:
            job = await Job.get(msg.matched_job_id)
        if not job:
            job = await self._match_job(user_id, msg.extracted, msg.subject, msg.body_text)
            if job:
                msg.matched_job_id = str(job.id)

        if msg.event_type == EmailEventType.INTERVIEW_SCHEDULE:
            if job:
                job.status = JobStatus.INTERVIEW
                job.updated_at = datetime.utcnow()
                await job.save()
                actions.append(f"job→interview:{job.id}")
            when_raw = msg.extracted.get("interview_at")
            when = datetime.fromisoformat(when_raw) if when_raw else datetime.utcnow() + timedelta(days=2)
            reminder = Reminder(
                user_id=user_id,
                application_id="",
                job_id=str(job.id) if job else "",
                title=f"Interview: {msg.extracted.get('job_title') or (job.title if job else msg.subject)[:80]}",
                due_at=when,
                channel="email_sync",
            )
            await reminder.insert()
            actions.append(f"reminder:{reminder.id}")
        elif msg.event_type == EmailEventType.OFFER:
            if job:
                job.status = JobStatus.OFFER
                job.updated_at = datetime.utcnow()
                await job.save()
                actions.append(f"job→offer:{job.id}")
        elif msg.event_type == EmailEventType.REJECTION:
            if job:
                job.status = JobStatus.REJECTED
                job.updated_at = datetime.utcnow()
                await job.save()
                actions.append(f"job→rejected:{job.id}")
        elif msg.event_type == EmailEventType.JD_RECEIVED:
            if job and msg.body_text:
                # Append / replace description with emailed JD snippet
                job.description = (msg.body_text[:8000] or job.description).strip()
                if msg.extracted.get("job_title"):
                    # keep existing title unless empty-ish
                    pass
                job.updated_at = datetime.utcnow()
                if job.status in {JobStatus.NEW, JobStatus.TRACKED, JobStatus.MATCHED, JobStatus.APPLIED}:
                    # keep status; mark metadata via description update only
                    pass
                await job.save()
                actions.append(f"jd_updated:{job.id}")
            elif not job and msg.extracted.get("job_title"):
                job = Job(
                    user_id=user_id,
                    external_id=f"email-{msg.message_id[:40]}",
                    title=msg.extracted["job_title"],
                    company=msg.extracted.get("company") or msg.matched_company or "Unknown",
                    description=msg.body_text[:8000],
                    portal="email",
                    source="email",
                    status=JobStatus.TRACKED,
                    apply_url="",
                    fetched_at=datetime.utcnow(),
                )
                await job.insert()
                msg.matched_job_id = str(job.id)
                actions.append(f"job_created:{job.id}")
        elif msg.event_type == EmailEventType.ASSESSMENT:
            when_raw = msg.extracted.get("due_at")
            when = datetime.fromisoformat(when_raw) if when_raw else datetime.utcnow() + timedelta(days=3)
            reminder = Reminder(
                user_id=user_id,
                application_id="",
                job_id=str(job.id) if job else "",
                title=f"Assessment due: {msg.extracted.get('job_title') or msg.subject[:60]}",
                due_at=when,
                channel="email_sync",
            )
            await reminder.insert()
            actions.append(f"assessment_reminder:{reminder.id}")
        elif msg.event_type == EmailEventType.APPLICATION_UPDATE:
            actions.append("noted")
        else:
            actions.append("noop")

        msg.sync_status = EmailSyncStatus.APPLIED
        msg.applied_actions = actions
        msg.updated_at = datetime.utcnow()
        await msg.save()
        await emit_realtime(
            user_id,
            "email.applied",
            {
                "email_id": str(msg.id),
                "event_type": msg.event_type,
                "actions": actions,
                "job_id": msg.matched_job_id,
                "auto": auto,
            },
            title="Email applied to pipeline",
            body=f"{msg.event_type}: {msg.subject[:80]}",
            severity="success",
        )
        from app.services.audit_service import audit_event

        await audit_event(
            user_id,
            "email.applied",
            message=f"Applied email event {msg.event_type}",
            job_id=msg.matched_job_id,
            resource_type="email",
            resource_id=str(msg.id),
            severity="success",
            metadata={"actions": actions, "auto": auto},
        )
        return self._to_message(msg)

    async def ignore_message(self, user_id: str, email_id: str) -> dict:
        msg = await InboundEmail.get(email_id)
        if not msg or msg.user_id != user_id:
            raise NotFoundError("Email not found")
        msg.sync_status = EmailSyncStatus.IGNORED
        msg.updated_at = datetime.utcnow()
        await msg.save()
        return self._to_message(msg)

    async def _match_job(self, user_id: str, extracted: dict, subject: str, body: str) -> Job | None:
        company = (extracted.get("company") or "").strip()
        title = (extracted.get("job_title") or "").strip()
        text = f"{subject}\n{body}".lower()
        candidates = await Job.find({"user_id": user_id}).sort([("updated_at", -1)]).limit(80).to_list()
        best: Job | None = None
        best_score = 0
        for job in candidates:
            score = 0
            if company and company.lower() in (job.company or "").lower():
                score += 3
            if company and company.lower() in text and company.lower() in (job.company or "").lower():
                score += 1
            if title and title.lower() in (job.title or "").lower():
                score += 3
            if job.company and job.company.lower() in text:
                score += 2
            if job.title and job.title.lower()[:20] in text:
                score += 2
            if score > best_score:
                best_score = score
                best = job
        return best if best_score >= 3 else None

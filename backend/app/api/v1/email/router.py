"""Email inbox — IMAP sync + classified recruiting events."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.models.enums import EmailEventType, EmailSyncStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.services.email_inbox_service import EmailInboxService

router = APIRouter(prefix="/email", tags=["email"])


class EmailAccountUpsert(BaseModel):
    id: str | None = None
    label: str = "Primary"
    email_address: str = ""
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    mailbox: str = "INBOX"
    enabled: bool = True
    auto_apply: bool = True


class EmailIngestRequest(BaseModel):
    subject: str = ""
    body_text: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    message_id: str = ""
    account_id: str = ""
    auto_apply: bool = True


@router.get("/accounts")
async def list_accounts(user: User = Depends(get_current_user)):
    return await EmailInboxService().list_accounts(str(user.id))


@router.post("/accounts")
async def upsert_account(payload: EmailAccountUpsert, user: User = Depends(get_current_user)):
    return await EmailInboxService().upsert_account(str(user.id), payload.model_dump())


@router.delete("/accounts/{account_id}", response_model=MessageResponse)
async def delete_account(account_id: str, user: User = Depends(get_current_user)):
    await EmailInboxService().delete_account(str(user.id), account_id)
    return MessageResponse(detail="Deleted")


@router.post("/accounts/{account_id}/test")
async def test_account(account_id: str, user: User = Depends(get_current_user)):
    return await EmailInboxService().test_account(str(user.id), account_id)


@router.post("/accounts/{account_id}/sync")
async def sync_account(account_id: str, user: User = Depends(get_current_user)):
    return await EmailInboxService().sync_account(str(user.id), account_id)


@router.post("/sync")
async def sync_all(user: User = Depends(get_current_user)):
    return await EmailInboxService().sync_all(str(user.id))


@router.get("/messages")
async def list_messages(
    event_type: EmailEventType | None = None,
    status: EmailSyncStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    return await EmailInboxService().list_messages(
        str(user.id),
        event_type=event_type,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("/ingest")
async def ingest_email(payload: EmailIngestRequest, user: User = Depends(get_current_user)):
    """Ingest a forwarded / pasted email without IMAP (also used for demos)."""
    return await EmailInboxService().ingest_raw(str(user.id), payload.model_dump())


@router.post("/messages/{email_id}/apply")
async def apply_message(email_id: str, user: User = Depends(get_current_user)):
    return await EmailInboxService().apply_message(str(user.id), email_id)


@router.post("/messages/{email_id}/ignore")
async def ignore_message(email_id: str, user: User = Depends(get_current_user)):
    return await EmailInboxService().ignore_message(str(user.id), email_id)

"""IMAP fetch helper (stdlib imaplib) for recruiting inbox sync."""

from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any


@dataclass
class FetchedMessage:
    uid: int
    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    received_at: datetime | None
    body_text: str
    snippet: str
    headers: dict[str, str]


def _decode_mime(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out: list[str] = []
    for data, charset in parts:
        if isinstance(data, bytes):
            out.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(str(data))
    return "".join(out).strip()


def _body_from_message(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        # fallback html stripped lightly
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="replace")
                return re_strip_html(html)
        return ""
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace")
    if msg.get_content_type() == "text/html":
        return re_strip_html(text)
    return text


def re_strip_html(html: str) -> str:
    import re

    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class ImapInboxClient:
    def __init__(
        self,
        *,
        host: str,
        port: int = 993,
        username: str,
        password: str,
        use_ssl: bool = True,
        mailbox: str = "INBOX",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.mailbox = mailbox

    def fetch_since_uid(self, last_uid: int = 0, limit: int = 40) -> list[FetchedMessage]:
        if self.use_ssl:
            client: Any = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            client = imaplib.IMAP4(self.host, self.port)
        try:
            client.login(self.username, self.password)
            client.select(self.mailbox, readonly=True)
            criteria = f"UID {max(last_uid + 1, 1)}:*" if last_uid else "ALL"
            typ, data = client.uid("search", None, criteria)
            if typ != "OK" or not data or not data[0]:
                return []
            uids = [int(x) for x in data[0].split() if x.isdigit()]
            if last_uid:
                uids = [u for u in uids if u > last_uid]
            uids = uids[-limit:]
            messages: list[FetchedMessage] = []
            for uid in uids:
                typ, msg_data = client.uid("fetch", str(uid), "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode_mime(msg.get("Subject"))
                sender = _decode_mime(msg.get("From"))
                to = _decode_mime(msg.get("To"))
                message_id = (msg.get("Message-ID") or f"uid-{uid}").strip()
                received_at = None
                date_hdr = msg.get("Date")
                if date_hdr:
                    try:
                        received_at = parsedate_to_datetime(date_hdr)
                        if received_at and received_at.tzinfo:
                            received_at = received_at.replace(tzinfo=None)
                    except Exception:  # noqa: BLE001
                        received_at = None
                body = _body_from_message(msg)
                messages.append(
                    FetchedMessage(
                        uid=uid,
                        message_id=message_id,
                        subject=subject,
                        sender=sender,
                        recipients=[p.strip() for p in to.split(",") if p.strip()],
                        received_at=received_at,
                        body_text=body[:20000],
                        snippet=(body or subject)[:240],
                        headers={
                            "from": sender,
                            "to": to,
                            "subject": subject,
                            "date": date_hdr or "",
                        },
                    )
                )
            return messages
        finally:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass

    def test_connection(self) -> dict[str, Any]:
        if self.use_ssl:
            client: Any = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            client = imaplib.IMAP4(self.host, self.port)
        try:
            client.login(self.username, self.password)
            typ, _ = client.select(self.mailbox, readonly=True)
            return {"ok": typ == "OK", "mailbox": self.mailbox}
        finally:
            try:
                client.logout()
            except Exception:  # noqa: BLE001
                pass

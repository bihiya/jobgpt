"""Encrypted portal session cookie + TOTP vault."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.logging import get_logger
from app.models.portal import Portal

logger = get_logger(__name__)


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_blob(payload: Any) -> str:
    raw = json.dumps(payload, default=str).encode("utf-8")
    return _fernet().encrypt(raw).decode("utf-8")


def decrypt_blob(token: str) -> Any:
    if not token:
        return None
    try:
        raw = _fernet().decrypt(token.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError, ValueError) as exc:
        logger.warning("vault_decrypt_failed", error=str(exc))
        return None


def normalize_cookies(raw: Any) -> list[dict[str, Any]]:
    """Accept Playwright cookie list or {name: value} map → Playwright list."""
    if not raw:
        return []
    if isinstance(raw, list):
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if not name or value is None:
                continue
            cookie = {
                "name": str(name),
                "value": str(value),
                "domain": item.get("domain") or ".linkedin.com",
                "path": item.get("path") or "/",
            }
            if item.get("expires") is not None:
                cookie["expires"] = item["expires"]
            if "httpOnly" in item:
                cookie["httpOnly"] = bool(item["httpOnly"])
            if "secure" in item:
                cookie["secure"] = bool(item["secure"])
            if item.get("sameSite"):
                cookie["sameSite"] = item["sameSite"]
            out.append(cookie)
        return out
    if isinstance(raw, dict):
        # legacy {name: value} or {cookies: [...]}
        if "cookies" in raw and isinstance(raw["cookies"], list):
            return normalize_cookies(raw["cookies"])
        domain = str(raw.get("domain") or "")
        return [
            {
                "name": str(k),
                "value": str(v),
                "domain": domain or ".example.com",
                "path": "/",
            }
            for k, v in raw.items()
            if k not in {"domain", "path", "cookies"} and v is not None
        ]
    return []


# LinkedIn li_at is base64url and often includes '=' padding or %XX encoding.
_LI_AT_TOKEN = re.compile(r"^[A-Za-z0-9_%=+-]{20,}$")
_COOKIE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def _as_li_at(value: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "li_at",
            "value": value,
            "domain": ".linkedin.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
        }
    ]


def _cookie(
    name: str,
    value: str,
    domain: str,
    *,
    http_only: bool | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": "/",
        "secure": True,
        "httpOnly": name in {"li_at", "li_a", "JSESSIONID"} if http_only is None else http_only,
    }


def _from_name_value_labels(text: str, domain: str) -> list[dict[str, Any]]:
    name_m = re.search(r"(?im)^(?:name|cookie)\s*:\s*(\S+)\s*$", text)
    value_m = re.search(r"(?im)^value\s*:\s*(\S+)\s*$", text)
    if name_m and value_m:
        return [_cookie(name_m.group(1), value_m.group(1), domain)]
    return []


def _from_table_or_netscape(text: str, domain: str) -> list[dict[str, Any]]:
    """DevTools TSV (`li_at<TAB>token`) or Netscape cookie file."""
    cookies: list[dict[str, Any]] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("#httponly_"):
            line = line[10:]
        parts = re.split(r"[\t]+", line)
        if len(parts) == 1:
            parts = re.split(r" {2,}", line)
        if len(parts) >= 7 and parts[5] and parts[6] and _COOKIE_NAME.match(parts[5]):
            host = parts[0].removeprefix("#HttpOnly_")
            cookies.append(
                _cookie(
                    parts[5],
                    parts[6],
                    host if host.startswith(".") or "linkedin" in host.lower() else domain,
                )
            )
            continue
        if (
            len(parts) >= 2
            and _COOKIE_NAME.match(parts[0])
            and parts[0].lower() not in {"name", "cookie", "key", "domain"}
            and parts[1]
        ):
            cookies.append(_cookie(parts[0], parts[1], domain))
    return cookies


def parse_cookie_paste(raw: Any, *, portal: str = "linkedin") -> list[dict[str, Any]]:
    """Parse DevTools / Cookie-Editor / wrapped `li_at` paste into Playwright cookies."""
    domain = DEFAULT_DOMAINS.get((portal or "").lower(), ".linkedin.com")
    if raw is None or raw == "" or raw == {} or raw == []:
        return []
    if isinstance(raw, (list, dict)):
        cookies = normalize_cookies(raw)
        for item in cookies:
            if not item.get("domain") or item.get("domain") == ".example.com":
                item["domain"] = domain
        return cookies
    text = str(raw).replace("\r", "").strip().strip('"').strip("'")
    if not text:
        return []
    labeled = _from_name_value_labels(text, domain)
    if labeled:
        return labeled
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) >= 2 and lines[0].lower().replace(" ", "").rstrip(":") in {"li_at", "name:li_at"}:
        text = f"li_at={''.join(lines[1:])}"
    elif text[0] not in "{[":
        text = "".join(lines) if "=" not in text else "\n".join(lines)
    if text[0] in "{[":
        try:
            return parse_cookie_paste(json.loads(text), portal=portal)
        except json.JSONDecodeError:
            pass
    header = text
    if header.lower().startswith("cookie:"):
        header = header.split(":", 1)[1].strip()
    if header.lower().startswith("li_at:") and "=" not in header.split(":", 1)[0]:
        header = "li_at=" + header.split(":", 1)[1].strip()
    if "=" in header:
        cookies: list[dict[str, Any]] = []
        for part in header.replace("\n", "").split(";"):
            piece = part.strip()
            if "=" not in piece:
                continue
            name, value = piece.split("=", 1)
            name, value = name.strip(), value.strip().strip('"')
            if not name or not value:
                continue
            # Bare base64 tokens often end with '=' — do not treat them as name=value.
            if value in {"=", "=="} and len(name) >= 16:
                continue
            if len(name) > 40 or not _COOKIE_NAME.match(name):
                continue
            cookies.append(_cookie(name, value, domain))
        if cookies:
            return cookies
    table = _from_table_or_netscape(str(raw).replace("\r", ""), domain)
    if table:
        return table
    compact = re.sub(r"\s+", "", text)
    if _is_bare_li_at(compact):
        return _as_li_at(compact)
    return []


def _is_bare_li_at(compact: str) -> bool:
    """Accept AQED… tokens or long base64 blobs — not English error text."""
    if not _LI_AT_TOKEN.fullmatch(compact):
        return False
    if compact.startswith("AQED") and len(compact) >= 20:
        return True
    return len(compact) >= 80


DEFAULT_DOMAINS = {
    "linkedin": ".linkedin.com",
    "indeed": ".indeed.com",
    "greenhouse": ".greenhouse.io",
    "lever": ".lever.co",
}

# Cookies that prove an authenticated session (not anonymous tracking cookies).
AUTH_COOKIE_NAMES: dict[str, frozenset[str]] = {
    "linkedin": frozenset({"li_at"}),
    # Indeed sets several account-scoped cookies after a real sign-in.
    "indeed": frozenset({"PP", "SHARED_SESSION", "SOCK", "SHOE", "indeed_rcc"}),
}


def cookie_name_set(cookies: list[dict[str, Any]] | None) -> set[str]:
    names: set[str] = set()
    for item in cookies or []:
        if isinstance(item, dict) and item.get("name"):
            names.add(str(item["name"]))
    return names


def has_auth_cookies(portal_name: str, cookies: list[dict[str, Any]] | None) -> bool:
    """True only when portal-specific auth cookies are present."""
    required = AUTH_COOKIE_NAMES.get((portal_name or "").lower())
    if not required:
        return bool(cookies)
    return bool(cookie_name_set(cookies) & required)


def portal_has_auth_session(portal: Portal) -> bool:
    """Whether the vault holds a validated auth session (not anonymous cookies)."""
    name = getattr(portal.name, "value", portal.name)
    cookies = SessionVault().load_cookies(portal)
    return has_auth_cookies(str(name), cookies)


class SessionVault:
    """Load/save portal cookies + TOTP secrets with optional encryption."""

    def load_cookies(self, portal: Portal) -> list[dict[str, Any]]:
        if getattr(portal, "session_blob", ""):
            data = decrypt_blob(portal.session_blob)
            cookies = normalize_cookies(data)
            if cookies:
                return cookies
        return normalize_cookies(getattr(portal, "cookies", None))

    def save_cookies(self, portal: Portal, cookies: list[dict[str, Any]]) -> None:
        normalized = normalize_cookies(cookies)
        if not normalized:
            self.clear_session(portal)
            return
        portal.cookies = {"cookies": normalized}
        portal.session_blob = encrypt_blob(normalized)
        portal.session_updated_at = datetime.utcnow()

    def clear_session(self, portal: Portal) -> None:
        portal.cookies = {}
        portal.session_blob = ""
        portal.session_updated_at = None

    def load_totp_secret(self, portal: Portal) -> str:
        enc = getattr(portal, "totp_secret_encrypted", "") or ""
        if enc:
            secret = decrypt_blob(enc)
            if isinstance(secret, str):
                return secret
            if isinstance(secret, dict):
                return str(secret.get("secret") or "")
        return getattr(portal, "totp_secret", "") or ""

    def save_totp_secret(self, portal: Portal, secret: str) -> None:
        secret = (secret or "").strip().replace(" ", "")
        portal.totp_secret = ""  # never keep plaintext after vault write
        portal.totp_secret_encrypted = encrypt_blob(secret) if secret else ""

    def default_domain(self, portal_name: str) -> str:
        return DEFAULT_DOMAINS.get((portal_name or "").lower(), ".example.com")

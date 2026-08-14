"""Encrypted portal session cookie + TOTP vault."""

from __future__ import annotations

import base64
import hashlib
import json
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

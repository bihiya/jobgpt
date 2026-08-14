"""Portal credential merge / response shape (never leak password)."""

from types import SimpleNamespace

from app.models.portal import PortalCredentials
from app.services.portal_service import PortalService


def test_merge_keeps_password_when_blank():
    current = PortalCredentials(username="old@x.com", password="secret")
    merged = PortalService._merge_credentials(
        current,
        {"username": "new@x.com", "password": ""},
    )
    assert merged.username == "new@x.com"
    assert merged.password == "secret"


def test_merge_replaces_password_when_set():
    current = PortalCredentials(username="a@x.com", password="old")
    merged = PortalService._merge_credentials(
        current,
        {"username": "a@x.com", "password": "new-pass"},
    )
    assert merged.password == "new-pass"


def test_merge_clear_wipes_both():
    current = PortalCredentials(username="a@x.com", password="secret")
    merged = PortalService._merge_credentials(current, {}, clear=True)
    assert merged.username == ""
    assert merged.password == ""


def test_response_shows_username_not_password():
    from datetime import datetime

    from app.models.enums import PortalName, PortalStatus
    from app.services.session_vault import encrypt_blob, normalize_cookies

    portal = SimpleNamespace(
        id="p1",
        name=PortalName.LINKEDIN,
        status=PortalStatus.CONNECTED,
        last_sync_at=None,
        sync_started_at=None,
        created_at=datetime(2026, 8, 14, 8, 0, 0),
        updated_at=datetime(2026, 8, 14, 8, 0, 0),
        credentials=SimpleNamespace(username="you@example.com", password="super-secret"),
        cookies={"cookies": normalize_cookies([{"name": "bcookie", "value": "x", "domain": ".linkedin.com"}])},
        session_blob="",
        totp_secret_encrypted="",
        session_updated_at=None,
        selector_version=1,
        health=SimpleNamespace(
            model_dump=lambda: {
                "score": 100,
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_error": "",
                "auto_paused": False,
                "paused_reason": "",
            }
        ),
    )
    portal.session_blob = encrypt_blob(portal.cookies["cookies"])
    resp = PortalService()._to_response(portal)
    dumped = resp.model_dump()
    assert resp.username == "you@example.com"
    assert resp.has_credentials is True
    assert resp.has_password is True
    assert "password" not in dumped
    assert "super-secret" not in str(dumped)
    assert resp.correlation_id == ""
    assert resp.model_copy(update={"correlation_id": "sync-1"}).correlation_id == "sync-1"

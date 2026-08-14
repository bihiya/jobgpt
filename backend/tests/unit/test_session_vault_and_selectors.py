from app.automation.selectors import get_selector_pack
from app.automation.session_recorder import ApplySessionRecorder
from app.services.session_vault import decrypt_blob, encrypt_blob, normalize_cookies


def test_normalize_cookies_list_and_map():
    listed = normalize_cookies(
        [{"name": "li_at", "value": "abc", "domain": ".linkedin.com", "path": "/"}]
    )
    assert listed[0]["name"] == "li_at"
    mapped = normalize_cookies({"li_at": "abc", "domain": ".linkedin.com"})
    assert any(c["name"] == "li_at" for c in mapped)
    nested = normalize_cookies({"cookies": listed})
    assert len(nested) == 1


def test_vault_roundtrip():
    token = encrypt_blob([{"name": "x", "value": "1", "domain": ".x.com", "path": "/"}])
    assert isinstance(token, str) and token
    data = decrypt_blob(token)
    assert data[0]["name"] == "x"


def test_clear_session_wipes_cookies():
    from types import SimpleNamespace

    from app.services.session_vault import SessionVault

    portal = SimpleNamespace(cookies={"cookies": [{"name": "li_at", "value": "x"}]}, session_blob="abc", session_updated_at="now")
    SessionVault().clear_session(portal)
    assert portal.cookies == {}
    assert portal.session_blob == ""
    assert portal.session_updated_at is None


def test_selector_packs_versioned():
    li = get_selector_pack("linkedin")
    assert li.version == 1
    assert li.all("easy_apply")
    assert li.all("login_error")
    assert "a[href*='/feed']" not in li.all("logged_in")
    assert get_selector_pack("greenhouse").all("success")
    assert get_selector_pack("unknown").version == 0


def test_session_recorder_timeline():
    rec = ApplySessionRecorder()
    rec.opened_jd("https://example.com/job")
    rec.clicked_apply("button:has-text('Easy Apply')")
    rec.filled_fields(3)
    rec.submitted()
    rec.verified(True, "Matched success selector")
    steps = rec.to_list()
    assert [s["key"] for s in steps] == [
        "opened_jd",
        "clicked_apply",
        "filled_fields",
        "submitted",
        "verified",
    ]
    assert steps[2]["metadata"]["count"] == 3

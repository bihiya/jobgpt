import pytest

from app.automation.selectors import get_selector_pack
from app.automation.session_recorder import ApplySessionRecorder
from app.services.session_vault import (
    decrypt_blob,
    encrypt_blob,
    has_auth_cookies,
    normalize_cookies,
    parse_cookie_paste,
)


def test_normalize_cookies_list_and_map():
    listed = normalize_cookies(
        [{"name": "li_at", "value": "abc", "domain": ".linkedin.com", "path": "/"}]
    )
    assert listed[0]["name"] == "li_at"
    mapped = normalize_cookies({"li_at": "abc", "domain": ".linkedin.com"})
    assert any(c["name"] == "li_at" for c in mapped)
    nested = normalize_cookies({"cookies": listed})
    assert len(nested) == 1


def test_parse_cookie_paste_accepts_header_json_and_bare_token():
    header = parse_cookie_paste("li_at=tok123; JSESSIONID=abc", portal="linkedin")
    assert has_auth_cookies("linkedin", header)
    assert {c["name"] for c in header} == {"li_at", "JSESSIONID"}
    listed = parse_cookie_paste(
        '[{"name":"li_at","value":"abc","domain":".linkedin.com"}]',
        portal="linkedin",
    )
    assert listed[0]["value"] == "abc"
    bare = parse_cookie_paste("AQED" + "x" * 24, portal="linkedin")
    assert bare[0]["name"] == "li_at"
    wrapped = parse_cookie_paste("AQED" + "x" * 12 + "\n" + "y" * 12, portal="linkedin")
    assert wrapped[0]["name"] == "li_at"
    assert wrapped[0]["value"] == "AQED" + "x" * 12 + "y" * 12
    labeled = parse_cookie_paste("li_at\n" + "AQED" + "z" * 24, portal="linkedin")
    assert labeled[0]["value"].startswith("AQED")
    padded = parse_cookie_paste("AQED" + "x" * 24 + "==", portal="linkedin")
    assert padded[0]["name"] == "li_at"
    assert padded[0]["value"].endswith("==")
    tsv = parse_cookie_paste("li_at\t" + "AQED" + "t" * 24 + "\t.linkedin.com\t/", portal="linkedin")
    assert tsv[0]["name"] == "li_at"
    assert tsv[0]["value"] == "AQED" + "t" * 24
    named = parse_cookie_paste("Name: li_at\nValue: " + "AQED" + "n" * 24, portal="linkedin")
    assert named[0]["value"] == "AQED" + "n" * 24
    assert parse_cookie_paste("") == []
    assert parse_cookie_paste("not-a-cookie") == []
    assert parse_cookie_paste("Login failed selectors missed") == []


def test_vault_roundtrip():
    token = encrypt_blob([{"name": "x", "value": "1", "domain": ".x.com", "path": "/"}])
    assert isinstance(token, str) and token
    data = decrypt_blob(token)
    assert data[0]["name"] == "x"


def test_clear_session_wipes_cookies():
    from types import SimpleNamespace

    from app.services.session_vault import SessionVault

    portal = SimpleNamespace(
        cookies={"cookies": [{"name": "li_at", "value": "x"}]},
        session_blob="abc",
        session_updated_at="now",
        session_identity=SimpleNamespace(display_name="Ada"),
    )
    SessionVault().clear_session(portal)
    assert portal.cookies == {}
    assert portal.session_blob == ""
    assert portal.session_updated_at is None
    assert portal.session_identity.display_name == ""


def test_selector_packs_versioned():
    li = get_selector_pack("linkedin")
    assert li.version == 1
    assert li.all("easy_apply")
    assert "button:has-text('Apply')" not in li.all("easy_apply")
    assert any("Easy Apply" in sel or "LinkedIn Apply to" in sel for sel in li.all("easy_apply"))
    assert li.all("already_applied")
    assert li.all("external_apply")
    assert li.all("job_links")
    assert any("/jobs/view/" in sel for sel in li.all("job_links"))
    assert li.all("job_detail")
    assert "#job-details" in li.all("job_detail")
    assert li.all("login_error")
    assert "a[href*='/feed']" not in li.all("logged_in")
    assert get_selector_pack("greenhouse").all("success")
    assert get_selector_pack("workday").all("submit")
    assert get_selector_pack("workday").all("apply_manually")
    assert get_selector_pack("workday").all("autofill_resume")
    assert get_selector_pack("workday").all("use_last_application")
    assert get_selector_pack("workday").all("email_verify")
    assert get_selector_pack("workday").all("mfa")
    assert get_selector_pack("workday").all("job_closed")
    assert get_selector_pack("workday").all("wizard_title")
    assert any("bottom-navigation-next-button" in sel for sel in get_selector_pack("workday").all("next"))
    assert get_selector_pack("unknown").version == 0


def test_session_recorder_timeline():
    rec = ApplySessionRecorder()
    rec.opened_jd("https://example.com/job")
    rec.clicked_apply("button:has-text('Easy Apply')")
    rec.apply_channel("LinkedIn Easy Apply", kind="linkedin")
    rec.filled_fields(3)
    rec.submitted()
    rec.verified(True, "Matched success selector")
    steps = rec.to_list()
    assert [s["key"] for s in steps] == [
        "opened_jd",
        "clicked_apply",
        "apply_channel",
        "filled_fields",
        "submitted",
        "verified",
    ]
    assert steps[1]["label"] == "Clicked LinkedIn Easy Apply"
    assert steps[2]["label"] == "LinkedIn Easy Apply"
    assert steps[3]["metadata"]["count"] == 3


def test_session_recorder_seeds_and_notifies_on_step():
    seen = []
    rec = ApplySessionRecorder(on_step=lambda step: seen.append(step.key))
    rec.seed(
        [
            {
                "key": "queued",
                "label": "Queued for auto-apply",
                "status": "pending",
                "detail": "Waiting for worker to start",
                "at": "2026-08-16T11:00:00Z",
            }
        ]
    )
    rec.add("started", "Worker started applying", detail="linkedin")
    assert [s["key"] for s in rec.to_list()] == ["queued", "started"]
    assert seen == ["started"]
    rec.complete_pending("queued", detail="Worker picked up")
    assert rec.to_list()[0]["status"] == "ok"
    assert rec.to_list()[0]["detail"] == "Worker picked up"


@pytest.mark.asyncio
async def test_session_recorder_flush_awaits_async_on_step():
    import asyncio

    seen: list[str] = []

    async def on_step(step):
        await asyncio.sleep(0.01)
        seen.append(step.key)

    rec = ApplySessionRecorder(on_step=on_step)
    rec.add("browser", "Launching browser", status="pending")
    assert seen == []
    await rec.flush()
    assert seen == ["browser"]


def test_compact_sync_steps_trims_fields():
    from app.automation.session_recorder import compact_sync_steps

    compact = compact_sync_steps(
        [
            {
                "key": "login",
                "label": "Login page opened",
                "status": "ok",
                "detail": "https://www.linkedin.com/login",
                "at": "2026-08-14T08:00:00Z",
                "html": "<huge>",
            }
        ]
    )
    assert compact == [
        {
            "key": "login",
            "label": "Login page opened",
            "status": "ok",
            "detail": "https://www.linkedin.com/login",
            "at": "2026-08-14T08:00:00Z",
        }
    ]
    assert "html" not in compact[0]

"""Workday cookies stay on one career-site host."""

from app.automation.workday_session import (
    cookie_matches_workday_host,
    cookies_for_workday_host,
    merge_workday_tenant_cookies,
    workday_tenant_host,
)


def test_workday_tenant_host():
    assert (
        workday_tenant_host("https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/x")
        == "nvidia.wd5.myworkdayjobs.com"
    )
    assert workday_tenant_host("https://www.linkedin.com/jobs/view/1") == ""


def test_cookies_do_not_cross_workday_tenants():
    nvidia = {"name": "WD-SESSION", "value": "n", "domain": "nvidia.wd5.myworkdayjobs.com"}
    apple = {"name": "WD-SESSION", "value": "a", "domain": "apple.wd5.myworkdayjobs.com"}
    shared = {"name": "wd-browser-id", "value": "x", "domain": ".myworkdayjobs.com"}
    host = "nvidia.wd5.myworkdayjobs.com"
    assert cookie_matches_workday_host(nvidia, host)
    assert not cookie_matches_workday_host(apple, host)
    assert not cookie_matches_workday_host(shared, host)
    assert cookies_for_workday_host([nvidia, apple, shared], host) == [nvidia]


def test_merge_keeps_other_tenant_sessions():
    nvidia = {"name": "WD-SESSION", "value": "n1", "domain": "nvidia.wd5.myworkdayjobs.com"}
    apple = {"name": "WD-SESSION", "value": "a1", "domain": "apple.wd5.myworkdayjobs.com"}
    nvidia2 = {"name": "WD-SESSION", "value": "n2", "domain": "nvidia.wd5.myworkdayjobs.com"}
    merged = merge_workday_tenant_cookies([nvidia, apple], [nvidia2], "nvidia.wd5.myworkdayjobs.com")
    by_host = {item["domain"]: item["value"] for item in merged}
    assert by_host["nvidia.wd5.myworkdayjobs.com"] == "n2"
    assert by_host["apple.wd5.myworkdayjobs.com"] == "a1"

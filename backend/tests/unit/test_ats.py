"""ATS host detection and LinkedIn vs external apply labels."""

from app.automation.ats import (
    channel_label,
    detect_ats,
    is_offsite,
    predicted_channel_meta,
    tag_apply_result,
)
from app.automation.base.portal import ApplyResult
from app.automation.portals.registry import adapter_for_ats, get_portal_adapter
from app.automation.portals.workday import WorkdayPortal
from app.models.enums import PortalName


def test_detect_ats_from_well_known_hosts():
    assert detect_ats("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/x") == "workday"
    assert detect_ats("https://company.wd1.myworkdayjobs.com/en-US/External") == "workday"
    assert detect_ats("https://company.myworkday.com/en-US/job") == "workday"
    assert detect_ats("https://boards.greenhouse.io/acme/jobs/123") == "greenhouse"
    assert detect_ats("https://job-boards.greenhouse.io/acme/jobs/123") == "greenhouse"
    assert detect_ats("https://jobs.lever.co/acme/abc") == "lever"
    assert detect_ats("https://jobs.ashbyhq.com/acme/role") == "ashby"
    assert detect_ats("https://jobs.smartrecruiters.com/Acme/123") == "smartrecruiters"
    assert detect_ats("https://acme.taleo.net/careersection/jobdetail.ftl") == "taleo"
    assert detect_ats("https://careers.icims.com/jobs/123") == "icims"
    assert detect_ats("https://www.linkedin.com/jobs/view/1/") == "generic"
    assert detect_ats("") == "generic"


def test_channel_labels():
    assert channel_label(kind="linkedin") == "LinkedIn Easy Apply"
    assert channel_label(kind="external", ats="workday") == "External apply · Workday"
    assert channel_label(kind="external", ats="greenhouse") == "External apply · Greenhouse"
    assert channel_label(kind="external", ats="generic") == "External apply"
    assert channel_label(kind="indeed") == "Indeed apply"


def test_predicted_channel_meta_for_fetch():
    easy = predicted_channel_meta("linkedin")
    assert easy["apply_channel"] == "LinkedIn Easy Apply"
    assert easy["apply_channel_kind"] == "linkedin"
    assert easy["apply_channel_predicted"] is True
    company = predicted_channel_meta("external")
    assert company["apply_channel"] == "External apply"
    assert company["apply_channel_kind"] == "external"
    assert company["apply_channel_predicted"] is True
    assert predicted_channel_meta("") == {}


def test_offsite_detection():
    assert is_offsite("https://nvidia.wd5.myworkdayjobs.com/x", ("linkedin.com", "lnkd.in"))
    assert not is_offsite("https://www.linkedin.com/jobs/view/1", ("linkedin.com",))
    assert not is_offsite("https://www.indeed.com/viewjob?jk=1", ("indeed.com",))


def test_tag_apply_result_sets_metadata():
    result = tag_apply_result(ApplyResult(success=True, message="ok"), kind="external", ats="workday", url="https://x.wd1.myworkdayjobs.com/j")
    assert result.metadata["apply_channel"] == "External apply · Workday"
    assert result.metadata["apply_channel_kind"] == "external"
    assert result.metadata["ats"] == "workday"


def test_registry_uses_workday_portal():
    adapter = get_portal_adapter(PortalName.WORKDAY)
    assert isinstance(adapter, WorkdayPortal)
    child = adapter_for_ats("workday")
    assert isinstance(child, WorkdayPortal)
    gh = adapter_for_ats("greenhouse")
    assert gh.name == "greenhouse"
    generic = adapter_for_ats("ashby")
    assert generic.name == "ashby"

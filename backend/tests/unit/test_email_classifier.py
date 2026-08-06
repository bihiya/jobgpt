from app.models.enums import EmailEventType
from app.services.email_classifier import classify_email, extract_datetime


def test_classify_interview_schedule():
    result = classify_email(
        "Interview scheduled with Acme",
        "Hi, we'd like to schedule an interview on Tue Mar 10 at 3pm via Zoom https://zoom.us/j/123",
        "recruiter@acme.com",
    )
    assert result.event_type == EmailEventType.INTERVIEW_SCHEDULE
    assert result.confidence >= 0.8
    assert result.extracted.get("company") == "Acme"
    assert "interview_at" in result.extracted or result.extracted.get("meeting_url")


def test_classify_jd_received():
    result = classify_email(
        "Job description for Platform Engineer",
        "Here's the full job description for the Platform Engineer role at Harbor.",
        "talent@harbor.ai",
    )
    assert result.event_type == EmailEventType.JD_RECEIVED


def test_classify_offer_and_rejection():
    offer = classify_email("Your offer letter", "We are pleased to offer you the position.", "hr@x.com")
    reject = classify_email(
        "Update on your application",
        "Unfortunately we will not be moving forward with other candidates.",
        "hr@x.com",
    )
    assert offer.event_type == EmailEventType.OFFER
    assert reject.event_type == EmailEventType.REJECTION


def test_extract_tomorrow():
    when = extract_datetime("Let's talk tomorrow at 2pm")
    assert when is not None
    assert when.hour == 14

"""Activity narrative copy helpers."""

from app.services.activity_narratives import narrate_activity, outcome_label


def test_outcome_passed_failed():
    assert outcome_label("success", "approval.approved") == "Passed"
    assert outcome_label("error", "application.failed") == "Failed"
    assert outcome_label("warning", "approval.needed") == "Needs attention"


def test_user_narrative_includes_actor_and_next_step():
    story = narrate_activity(
        actor_name="Lav Gupta",
        action="settings.updated",
        message="changed auto_apply, match_threshold",
        source="user",
        severity="success",
    )
    assert story["summary"].startswith("Lav Gupta")
    assert "Passed" in story["outcome"] or "Passed" in story["summary"]
    assert "fetch" in story["next_step"].lower() or "apply" in story["next_step"].lower()


def test_worker_narrative_uses_jobpilot():
    story = narrate_activity(
        actor_name="",
        action="job.matched",
        message="Matched Senior Frontend Engineer (92%)",
        source="worker",
        severity="success",
    )
    assert story["actor_name"] == "JobPilot"
    assert "JobPilot" in story["summary"]
    assert story["outcome"] == "Passed"

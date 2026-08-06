from app.schemas.report import WeeklyStoryResponse


def test_weekly_story_schema_narrative_fields():
    story = WeeklyStoryResponse(
        headline="12 applied · 3 replies · 1 interviews",
        narrative="This week you applied to 12 roles.",
        applied=12,
        replies=3,
        interviews=1,
        offers=0,
        approvals_pending=2,
        blockers=1,
        top_portal="linkedin",
        highlights=["You pushed 12 applications this week."],
    )
    assert story.applied == 12
    assert "linkedin" == story.top_portal
    assert story.highlights[0].startswith("You pushed")

"""Unit tests for match scoring."""

from types import SimpleNamespace

from app.services.match_service import MatchService


def _user(**profile_kwargs):
    return SimpleNamespace(profile=SimpleNamespace(**profile_kwargs))


def _job(**kwargs):
    defaults = {
        "title": "Engineer",
        "description": "",
        "skills": [],
        "location": "",
        "experience": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_match_score_high_for_overlapping_skills():
    service = MatchService()
    user = _user(
        skills=["python", "fastapi", "mongodb"],
        keywords=["backend", "api"],
        location="Remote",
        experience_years=5,
    )
    job = _job(
        title="Backend Engineer",
        location="Remote",
        experience="4 years",
        description="Build APIs with FastAPI",
        skills=["python", "fastapi"],
    )
    score = service.score(user, job)  # type: ignore[arg-type]
    assert score >= 0.6


def test_match_score_low_without_overlap():
    service = MatchService()
    user = _user(
        skills=["java"],
        keywords=["android"],
        location="NYC",
        experience_years=1,
    )
    job = _job(
        title="Data Scientist",
        location="London",
        experience="8 years",
        description="Machine learning research",
        skills=["pytorch", "nlp"],
    )
    score = service.score(user, job)  # type: ignore[arg-type]
    assert score < 0.5

"""Unit tests for match scoring."""

from app.models.job import Job
from app.models.user import User, UserProfile
from app.services.match_service import MatchService


def test_match_score_high_for_overlapping_skills():
    service = MatchService()
    user = User(
        email="ada@example.com",
        hashed_password="x",
        full_name="Ada",
        profile=UserProfile(
            skills=["python", "fastapi", "mongodb"],
            keywords=["backend", "api"],
            location="Remote",
            experience_years=5,
        ),
    )
    job = Job(
        user_id="u1",
        external_id="j1",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        experience="4 years",
        description="Build APIs with FastAPI",
        skills=["python", "fastapi"],
        portal="linkedin",
    )
    score = service.score(user, job)
    assert score >= 0.6


def test_match_score_low_without_overlap():
    service = MatchService()
    user = User(
        email="ada@example.com",
        hashed_password="x",
        full_name="Ada",
        profile=UserProfile(skills=["java"], keywords=["android"], location="NYC", experience_years=1),
    )
    job = Job(
        user_id="u1",
        external_id="j2",
        title="Data Scientist",
        company="Acme",
        location="London",
        experience="8 years",
        description="Machine learning research",
        skills=["pytorch", "nlp"],
        portal="indeed",
    )
    score = service.score(user, job)
    assert score < 0.5

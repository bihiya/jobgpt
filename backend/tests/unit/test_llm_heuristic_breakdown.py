import asyncio
from types import SimpleNamespace

from app.services.llm.ranking import LLMRankingService


def test_heuristic_breakdown_reasons():
    service = LLMRankingService()
    user = SimpleNamespace(
        profile=SimpleNamespace(
            skills=["python", "fastapi"],
            keywords=["backend"],
            location="Remote",
            experience_years=5,
        )
    )
    job = SimpleNamespace(
        title="Backend Engineer",
        description="Build APIs with FastAPI",
        skills=["python", "fastapi", "aws"],
        location="Remote",
        experience="4 years",
    )

    async def run():
        return await service.rank(user, job)  # type: ignore[arg-type]

    breakdown = asyncio.get_event_loop().run_until_complete(run())
    assert breakdown.total >= 0.5
    assert breakdown.missing_skills == ["aws"]
    assert any("skill" in r.lower() for r in breakdown.reasons)

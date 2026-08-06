"""LLM-assisted job ranking with heuristic fallback."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.job import Job, MatchBreakdown
from app.models.user import User
from app.services.match_service import MatchService

logger = get_logger(__name__)


class LLMRankingService:
    """
    Combines heuristic MatchService with optional LLM refinement.
    Set LLM_API_URL + LLM_API_KEY to enable remote ranking.
    """

    def __init__(self, matcher: MatchService | None = None) -> None:
        self.matcher = matcher or MatchService()

    async def rank(self, user: User, job: Job) -> MatchBreakdown:
        heuristic = self._heuristic_breakdown(user, job)
        if not settings.llm_enabled:
            return heuristic

        try:
            llm = await self._llm_score(user, job)
            # Blend: 60% heuristic + 40% LLM when available
            blended = round(0.6 * heuristic.total + 0.4 * llm["score"], 4)
            reasons = heuristic.reasons + [llm.get("rationale", "")]
            return MatchBreakdown(
                total=blended,
                skills=heuristic.skills,
                keywords=heuristic.keywords,
                location=heuristic.location,
                experience=heuristic.experience,
                llm_score=llm["score"],
                llm_rationale=llm.get("rationale", ""),
                reasons=[r for r in reasons if r][:8],
                missing_skills=heuristic.missing_skills,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_ranking_fallback", error=str(exc))
            heuristic.reasons.append("LLM unavailable — used heuristic score only")
            return heuristic

    def _heuristic_breakdown(self, user: User, job: Job) -> MatchBreakdown:
        profile = user.profile
        skills = self.matcher._overlap(profile.skills, job.skills)
        keywords = self.matcher._text_hit(profile.keywords, f"{job.title} {job.description}")
        location = self.matcher._location_match(profile.location, job.location)
        experience = self.matcher._experience_match(profile.experience_years, job.experience)
        total = round(
            skills * 0.4 + keywords * 0.25 + location * 0.15 + experience * 0.2,
            4,
        )
        user_skills = {s.lower() for s in profile.skills}
        job_skills = {s.lower() for s in job.skills}
        missing = sorted(job_skills - user_skills)[:10]
        reasons = []
        if skills >= 0.5:
            reasons.append(f"Strong skill overlap ({int(skills * 100)}%)")
        elif skills > 0:
            reasons.append(f"Partial skill overlap ({int(skills * 100)}%)")
        else:
            reasons.append("Little skill overlap with your profile")
        if keywords > 0:
            reasons.append(f"Keyword hits in title/description ({int(keywords * 100)}%)")
        if location >= 0.7:
            reasons.append("Location matches your preference")
        if experience >= 0.7:
            reasons.append("Experience requirement looks compatible")
        if missing:
            reasons.append(f"Missing skills: {', '.join(missing[:5])}")
        return MatchBreakdown(
            total=total,
            skills=skills,
            keywords=keywords,
            location=location,
            experience=experience,
            reasons=reasons,
            missing_skills=missing,
        )

    async def _llm_score(self, user: User, job: Job) -> dict[str, Any]:
        prompt = {
            "role": "system",
            "content": (
                "Score job fit 0-1. Reply JSON only: "
                '{"score":0.0,"rationale":"..."}'
            ),
        }
        user_msg = {
            "role": "user",
            "content": json.dumps(
                {
                    "profile": {
                        "skills": user.profile.skills,
                        "keywords": user.profile.keywords,
                        "location": user.profile.location,
                        "experience_years": user.profile.experience_years,
                    },
                    "job": {
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "skills": job.skills,
                        "description": (job.description or "")[:2000],
                    },
                }
            ),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                settings.llm_api_url,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [prompt, user_msg],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(match.group(0) if match else content)
            score = float(parsed.get("score", 0))
            return {"score": min(max(score, 0.0), 1.0), "rationale": parsed.get("rationale", "")}

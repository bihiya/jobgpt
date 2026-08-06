"""Job-resume matching service."""

from app.models.job import Job
from app.models.user import User


class MatchService:
    """Score jobs against user profile using weighted heuristic matching."""

    WEIGHTS = {
        "skills": 0.4,
        "keywords": 0.25,
        "location": 0.15,
        "experience": 0.2,
    }

    def score(self, user: User, job: Job) -> float:
        profile = user.profile
        skills_score = self._overlap(profile.skills, job.skills)
        keywords_score = self._text_hit(profile.keywords, f"{job.title} {job.description}")
        location_score = self._location_match(profile.location, job.location)
        experience_score = self._experience_match(profile.experience_years, job.experience)

        total = (
            skills_score * self.WEIGHTS["skills"]
            + keywords_score * self.WEIGHTS["keywords"]
            + location_score * self.WEIGHTS["location"]
            + experience_score * self.WEIGHTS["experience"]
        )
        return round(min(max(total, 0.0), 1.0), 4)

    @staticmethod
    def _normalize(items: list[str]) -> set[str]:
        return {item.strip().lower() for item in items if item and item.strip()}

    def _overlap(self, left: list[str], right: list[str]) -> float:
        a, b = self._normalize(left), self._normalize(right)
        if not a or not b:
            return 0.0
        return len(a & b) / len(a)

    def _text_hit(self, keywords: list[str], text: str) -> float:
        if not keywords:
            return 0.0
        haystack = text.lower()
        hits = sum(1 for kw in self._normalize(keywords) if kw in haystack)
        return hits / len(keywords)

    @staticmethod
    def _location_match(preferred: str, job_location: str) -> float:
        if not preferred:
            return 0.5
        preferred_l = preferred.lower()
        job_l = (job_location or "").lower()
        if not job_l:
            return 0.3
        if preferred_l in job_l or job_l in preferred_l:
            return 1.0
        if "remote" in preferred_l and "remote" in job_l:
            return 1.0
        return 0.2

    @staticmethod
    def _experience_match(years: float, experience_text: str) -> float:
        if not experience_text:
            return 0.5
        text = experience_text.lower()
        # Extract first integer-like year requirement if present
        digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in text).split()
        if not digits:
            return 0.5
        try:
            required = float(digits[0])
        except ValueError:
            return 0.5
        if years >= required:
            return 1.0
        if years >= required - 1:
            return 0.7
        return 0.3

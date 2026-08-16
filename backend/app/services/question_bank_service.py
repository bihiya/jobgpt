"""Smart question bank — store and retrieve answers for form fields."""

from __future__ import annotations

import re
from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.question_bank import QuestionAnswer


def normalize_question(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    cleaned = re.sub(r"[^a-z0-9 ?'/.-]", "", cleaned)
    return cleaned[:300]


class QuestionBankService:
    async def upsert(
        self,
        user_id: str,
        question: str,
        answer: str,
        tags: list[str] | None = None,
        portals: list[str] | None = None,
    ) -> QuestionAnswer:
        key = normalize_question(question)
        existing = await QuestionAnswer.find_one(
            {"user_id": user_id, "question_normalized": key}
        )
        if existing:
            existing.answer = answer
            existing.tags = tags or existing.tags
            existing.portals = portals or existing.portals
            existing.updated_at = datetime.utcnow()
            await existing.save()
            return existing
        doc = QuestionAnswer(
            user_id=user_id,
            question=question,
            question_normalized=key,
            answer=answer,
            tags=tags or [],
            portals=portals or [],
        )
        await doc.insert()
        return doc

    async def list(self, user_id: str) -> list[dict]:
        # Cosmos Mongo rejects ORDER BY on paths without a composite index
        # ("The index path corresponding to the specified order-by item is excluded").
        # Sort in process so apply workers do not crash after "started".
        items = await QuestionAnswer.find({"user_id": user_id}).to_list()
        items.sort(key=lambda i: int(getattr(i, "use_count", 0) or 0), reverse=True)
        return [
            {
                "id": str(i.id),
                "question": i.question,
                "answer": i.answer,
                "tags": i.tags,
                "portals": i.portals,
                "use_count": i.use_count,
            }
            for i in items
        ]

    async def resolve_answers(self, user_id: str, questions: list[str]) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for q in questions:
            key = normalize_question(q)
            item = await QuestionAnswer.find_one(
                {"user_id": user_id, "question_normalized": key}
            )
            if not item:
                # fuzzy contains match
                item = await QuestionAnswer.find_one(
                    {
                        "user_id": user_id,
                        "question_normalized": {"$regex": re.escape(key[:40])},
                    }
                )
            if item:
                item.use_count += 1
                item.last_used_at = datetime.utcnow()
                await item.save()
                resolved[q] = item.answer
        return resolved

    async def delete(self, user_id: str, qa_id: str) -> None:
        item = await QuestionAnswer.get(qa_id)
        if not item or item.user_id != user_id:
            raise NotFoundError("Question not found")
        await item.delete()

    async def seed_defaults(self, user_id: str, profile: dict) -> int:
        defaults = [
            ("How many years of experience do you have?", str(profile.get("experience_years", "0"))),
            ("What is your notice period?", f"{profile.get('notice_period_days', 0)} days"),
            ("What is your current location?", profile.get("location", "")),
            ("Are you authorized to work?", "Yes"),
            ("Do you require sponsorship?", "No"),
            ("Expected salary", ""),
        ]
        count = 0
        for q, a in defaults:
            if not a:
                continue
            await self.upsert(user_id, q, a, tags=["default"])
            count += 1
        return count

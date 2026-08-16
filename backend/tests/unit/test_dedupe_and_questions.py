from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.dedupe_service import DedupeService
from app.services.question_bank_service import QuestionBankService, normalize_question


def test_content_hash_stable():
    a = DedupeService.content_hash("Engineer", "Acme", "https://x/y", "1")
    b = DedupeService.content_hash("engineer", "acme", "https://x/y", "1")
    assert a == b
    assert len(a) == 64


def test_normalize_question():
    assert normalize_question("  How many Years of Experience?  ") == "how many years of experience?"


def _qa(qid: str, question: str, use_count: int):
    return SimpleNamespace(
        id=qid,
        question=question,
        answer=f"a-{qid}",
        tags=[],
        portals=[],
        use_count=use_count,
    )


@pytest.mark.asyncio
async def test_question_bank_list_sorts_in_process_without_mongo_order_by():
    items = [_qa("1", "notice", 1), _qa("2", "years", 9), _qa("3", "city", 3)]
    find_result = SimpleNamespace(to_list=AsyncMock(return_value=list(items)))
    find_result.sort = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("Cosmos cannot ORDER BY use_count")
    )

    with patch("app.services.question_bank_service.QuestionAnswer") as model:
        model.find = lambda *_a, **_k: find_result
        listed = await QuestionBankService().list("u1")

    assert [row["question"] for row in listed] == ["years", "city", "notice"]
    find_result.to_list.assert_awaited_once()

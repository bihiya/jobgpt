"""Cosmos Mongo API ORDER BY fallback helpers."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.mongodb import is_cosmos_mongo_url, is_order_by_index_error, sort_documents
from app.repository.base import BaseRepository

COSMOS_ORDER_BY_ERROR = (
    "Error=2, Details='Response status code does not indicate success: "
    'BadRequest (400); Reason: (Message: {"Errors":["The index path '
    'corresponding to the specified order-by item is excluded."]}'
)


def test_detects_cosmos_mongo_urls():
    assert is_cosmos_mongo_url("mongodb://jobpilot.mongo.cosmos.azure.com:10255/")
    assert is_cosmos_mongo_url("mongodb://localhost/?retryWrites=false") is False
    assert is_order_by_index_error(Exception(COSMOS_ORDER_BY_ERROR))
    assert is_order_by_index_error(Exception("duplicate key error")) is False


def test_sort_documents_newest_first():
    older = SimpleNamespace(created_at=datetime(2026, 1, 1), name="old")
    newer = SimpleNamespace(created_at=datetime(2026, 8, 15), name="new")
    missing = SimpleNamespace(created_at=None, name="missing")
    ordered = sort_documents([older, missing, newer], [("created_at", -1)])
    assert [item.name for item in ordered] == ["new", "old", "missing"]
    ascending = sort_documents([older, missing, newer], [("created_at", 1)])
    assert [item.name for item in ascending] == ["missing", "old", "new"]


@pytest.mark.asyncio
async def test_find_many_falls_back_when_cosmos_rejects_order_by():
    newer = SimpleNamespace(created_at=datetime.utcnow())
    older = SimpleNamespace(created_at=datetime.utcnow() - timedelta(days=1))
    sorted_query = MagicMock()
    sorted_query.skip.return_value.limit.return_value.to_list = AsyncMock(
        side_effect=Exception(COSMOS_ORDER_BY_ERROR)
    )
    unsorted_query = MagicMock()
    unsorted_query.to_list = AsyncMock(return_value=[older, newer])
    unsorted_query.skip.return_value.limit.return_value.to_list = AsyncMock(
        return_value=[older, newer]
    )

    class FakeModel:
        Settings = SimpleNamespace(name="resumes")

        @classmethod
        def find(cls, _filters):
            if not hasattr(cls, "_calls"):
                cls._calls = 0
            cls._calls += 1
            if cls._calls == 1:
                query = MagicMock()
                query.sort.return_value = sorted_query
                query.skip.return_value.limit.return_value.to_list = AsyncMock(
                    return_value=[older, newer]
                )
                return query
            return unsorted_query

    repo = BaseRepository(FakeModel)
    items = await repo.find_many({"user_id": "u1"}, limit=50, sort=[("created_at", -1)])
    assert items == [newer, older]


@pytest.mark.asyncio
async def test_find_many_reraises_unrelated_query_errors():
    class FakeModel:
        Settings = SimpleNamespace(name="resumes")

        @classmethod
        def find(cls, _filters):
            query = MagicMock()
            query.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(
                side_effect=RuntimeError("socket timeout")
            )
            return query

    repo = BaseRepository(FakeModel)
    with pytest.raises(RuntimeError, match="socket timeout"):
        await repo.find_many({"user_id": "u1"}, sort=[("created_at", -1)])

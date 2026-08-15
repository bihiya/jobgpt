"""Generic repository base class."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from beanie import Document
from beanie.odm.operators.find.comparison import Eq, In
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db.mongodb import is_order_by_index_error, sort_documents

logger = get_logger(__name__)

T = TypeVar("T", bound=Document)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T]) -> None:
        self.model = model

    async def create(self, data: dict[str, Any] | BaseModel) -> T:
        payload = data.model_dump() if isinstance(data, BaseModel) else data
        doc = self.model(**payload)
        await doc.insert()
        return doc

    async def get_by_id(self, doc_id: str) -> T | None:
        return await self.model.get(doc_id)

    async def update(self, doc: T, data: dict[str, Any] | BaseModel) -> T:
        payload = data.model_dump(exclude_unset=True) if isinstance(data, BaseModel) else data
        for key, value in payload.items():
            setattr(doc, key, value)
        await doc.save()
        return doc

    async def delete(self, doc: T) -> None:
        await doc.delete()

    async def find_many(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        query = self.model.find(filters or {})
        if sort:
            try:
                return await query.sort(sort).skip(skip).limit(limit).to_list()
            except Exception as exc:  # noqa: BLE001
                # Cosmos DB Mongo API rejects ORDER BY unless a composite index
                # covers the filter + sort paths ("order-by item is excluded").
                if not is_order_by_index_error(exc):
                    raise
                logger.warning(
                    "mongo_sort_index_fallback",
                    collection=getattr(
                        getattr(self.model, "Settings", None),
                        "name",
                        self.model.__name__,
                    ),
                    error=str(exc)[:240],
                )
                items = await self.model.find(filters or {}).to_list()
                items = sort_documents(items, sort)
                return items[skip : skip + limit]
        return await query.skip(skip).limit(limit).to_list()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        return await self.model.find(filters or {}).count()

    async def find_one(self, filters: dict[str, Any]) -> T | None:
        return await self.model.find_one(filters)

    async def find_by_ids(self, ids: list[str]) -> list[T]:
        return await self.model.find(In(self.model.id, ids)).to_list()

    async def find_eq(self, field: str, value: Any) -> list[T]:
        return await self.model.find(Eq(field, value)).to_list()

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> list[T]:
        """Batch insert for high-throughput ingestion."""
        docs = [self.model(**row) for row in rows]
        if not docs:
            return []
        await self.model.insert_many(docs)
        return docs

    async def bulk_update(self, filters: dict[str, Any], update: dict[str, Any]) -> int:
        """Batch update matching documents; returns modified count when available."""
        result = await self.model.find(filters).update_many({"$set": update})
        return int(getattr(result, "modified_count", 0) or 0)

    async def find_projected(
        self,
        filters: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Selective field projection to reduce payload size."""
        projection = {field: 1 for field in fields} if fields else None
        cursor = self.model.get_motor_collection().find(filters or {}, projection)
        cursor = cursor.skip(skip).limit(limit)
        return [doc async for doc in cursor]

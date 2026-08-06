"""Generic repository base class."""

from typing import Any, Generic, TypeVar

from beanie import Document
from beanie.odm.operators.find.comparison import Eq, In
from pydantic import BaseModel

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

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        query = self.model.find(filters or {})
        if sort:
            query = query.sort(sort)
        return await query.skip(skip).limit(limit).to_list()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        return await self.model.find(filters or {}).count()

    async def find_one(self, filters: dict[str, Any]) -> T | None:
        return await self.model.find_one(filters)

    async def find_by_ids(self, ids: list[str]) -> list[T]:
        return await self.model.find(In(self.model.id, ids)).to_list()

    async def find_eq(self, field: str, value: Any) -> list[T]:
        return await self.model.find(Eq(field, value)).to_list()

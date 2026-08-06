"""Pagination helpers with field selection / projection."""

from __future__ import annotations

from math import ceil
from typing import Any, Iterable

from pydantic import BaseModel, Field


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_dir: str = "desc"
    fields: str | None = None  # comma-separated field selection

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def sort(self) -> list[tuple[str, int]]:
        direction = -1 if self.sort_dir.lower() == "desc" else 1
        return [(self.sort_by, direction)]

    def field_list(self) -> list[str] | None:
        if not self.fields:
            return None
        return [f.strip() for f in self.fields.split(",") if f.strip()]


def paginate_dict(
    items: list[dict[str, Any]],
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if page_size else 0,
    }


def project_fields(docs: Iterable[dict[str, Any]], fields: list[str] | None) -> list[dict[str, Any]]:
    if not fields:
        return list(docs)
    projected = []
    for doc in docs:
        projected.append({k: doc.get(k) for k in fields if k in doc or k == "id"})
    return projected

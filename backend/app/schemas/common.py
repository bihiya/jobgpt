"""Shared response schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    detail: str
    code: str
    request_id: str | None = None
    errors: list[Any] = Field(default_factory=list)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

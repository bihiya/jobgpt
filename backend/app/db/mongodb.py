"""MongoDB connection with connection pooling and Beanie initialization."""

from __future__ import annotations

from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from app.core.logging import get_logger
from app.models import DOCUMENT_MODELS

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None


def is_cosmos_mongo_url(url: str) -> bool:
    """True when the Mongo connection string points at Azure Cosmos DB's API."""
    lowered = url.lower()
    return "cosmos.azure.com" in lowered or "cosmosdb" in lowered


def is_order_by_index_error(exc: BaseException) -> bool:
    """True for Cosmos Mongo API failures caused by ORDER BY without a composite index."""
    message = str(exc).lower()
    return "order-by" in message or "specified order-by item is excluded" in message


def sort_documents(items: list[Any], sort: list[tuple[str, int]]) -> list[Any]:
    """Stable in-memory sort matching Mongo ``[(field, 1|-1), ...]`` order.

    Null/missing values sort first on ascending and last on descending, like MongoDB.
    """
    result = list(items)
    for field, direction in reversed(sort):
        reverse = int(direction) < 0

        def _value(doc: Any, attr: str = field) -> Any:
            value = getattr(doc, attr, None)
            if value is None and isinstance(doc, dict):
                value = doc.get(attr)
            return value

        defined = [doc for doc in result if _value(doc) is not None]
        missing = [doc for doc in result if _value(doc) is None]
        defined.sort(key=_value, reverse=reverse)
        result = missing + defined if not reverse else defined + missing
    return result


def _mongo_retry_writes(url: str) -> bool:
    """Return whether retryable writes should be enabled for this Mongo URL.

    Azure Cosmos DB's Mongo API rejects retryable writes; forcing retryWrites=True
    breaks inserts (e.g. user registration) even when the URI has retrywrites=false.
    """
    if is_cosmos_mongo_url(url):
        return False
    if "retrywrites=false" in url.lower():
        return False
    return True


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global _client
    retry_writes = _mongo_retry_writes(settings.mongodb_url)
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        maxPoolSize=settings.mongodb_max_pool_size,
        minPoolSize=settings.mongodb_min_pool_size,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        retryWrites=retry_writes,
        # HTTP keep-alive equivalent for MongoDB sockets
        maxIdleTimeMS=60_000,
    )
    try:
        db = client[settings.mongodb_db]
        await init_beanie(database=db, document_models=DOCUMENT_MODELS)
    except Exception:
        client.close()
        _client = None
        raise
    _client = client
    logger.info(
        "mongodb_connected",
        db=settings.mongodb_db,
        max_pool=settings.mongodb_max_pool_size,
    )
    return db


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("mongodb_disconnected")


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db]

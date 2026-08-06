"""MongoDB connection and Beanie initialization."""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from app.core.logging import get_logger
from app.models import DOCUMENT_MODELS

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_url)
    db = _client[settings.mongodb_db]
    await init_beanie(database=db, document_models=DOCUMENT_MODELS)
    logger.info("mongodb_connected", db=settings.mongodb_db)
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

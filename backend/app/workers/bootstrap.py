"""Shared worker bootstrap for MongoDB + logging."""

import asyncio
from collections.abc import Awaitable, Callable

from app.core.logging import get_logger, setup_logging
from app.db.mongodb import close_mongo_connection, connect_to_mongo

logger = get_logger(__name__)


async def run_with_db(coro_factory: Callable[[], Awaitable[None]]) -> None:
    setup_logging()
    await connect_to_mongo()
    try:
        await coro_factory()
    finally:
        await close_mongo_connection()


def main(coro_factory: Callable[[], Awaitable[None]]) -> None:
    asyncio.run(run_with_db(coro_factory))

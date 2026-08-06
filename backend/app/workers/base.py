"""Base Kafka worker loop."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from app.core.kafka import create_consumer
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseWorker(ABC):
    topics: list[str] = []
    group_id: str | None = None

    def __init__(self) -> None:
        self._running = False

    @abstractmethod
    async def handle(self, topic: str, payload: dict[str, Any]) -> None: ...

    async def start(self) -> None:
        consumer = create_consumer(self.topics, group_id=self.group_id)
        await consumer.start()
        self._running = True
        logger.info("worker_started", worker=self.__class__.__name__, topics=self.topics)
        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    await self.handle(msg.topic, msg.value)
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "worker_handle_failed",
                        worker=self.__class__.__name__,
                        topic=msg.topic,
                        error=str(exc),
                    )
        finally:
            await consumer.stop()
            logger.info("worker_stopped", worker=self.__class__.__name__)

    def stop(self) -> None:
        self._running = False


async def run_worker(worker: BaseWorker) -> None:
    await worker.start()


def run_worker_sync(worker: BaseWorker) -> None:
    asyncio.run(worker.start())

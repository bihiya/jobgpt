"""Base Kafka worker loop with dead-letter queue for poison messages."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from app.core.kafka import create_consumer, publish
from app.core.logging import get_logger

logger = get_logger(__name__)

DLQ_TOPIC = "job.dlq"


class BaseWorker(ABC):
    topics: list[str] = []
    group_id: str | None = None
    max_handle_attempts: int = 3

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
                payload = msg.value if isinstance(msg.value, dict) else {"raw": msg.value}
                attempts = int(payload.get("_attempts", 0))
                try:
                    await self.handle(msg.topic, payload)
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "worker_handle_failed",
                        worker=self.__class__.__name__,
                        topic=msg.topic,
                        error=str(exc),
                        attempts=attempts,
                    )
                    await self._route_failure(msg.topic, payload, str(exc), attempts)
        finally:
            await consumer.stop()
            logger.info("worker_stopped", worker=self.__class__.__name__)

    async def _route_failure(
        self,
        topic: str,
        payload: dict[str, Any],
        error: str,
        attempts: int,
    ) -> None:
        next_attempts = attempts + 1
        envelope = {
            **payload,
            "_attempts": next_attempts,
            "_error": error,
            "_source_topic": topic,
            "_worker": self.__class__.__name__,
        }
        if next_attempts >= self.max_handle_attempts:
            await publish(DLQ_TOPIC, envelope, key=str(payload.get("user_id", "system")))
            logger.error("message_sent_to_dlq", topic=topic, attempts=next_attempts)
            return
        # Retry by re-publishing to original topic
        await publish(topic, envelope, key=str(payload.get("user_id", "system")))

    def stop(self) -> None:
        self._running = False


async def run_worker(worker: BaseWorker) -> None:
    await worker.start()


def run_worker_sync(worker: BaseWorker) -> None:
    asyncio.run(worker.start())

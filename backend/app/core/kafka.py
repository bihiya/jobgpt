"""Kafka producer/consumer client helpers."""

import json
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_producer: AIOKafkaProducer | None = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=settings.kafka_client_id,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        logger.info("kafka_producer_started")
    return _producer


async def close_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("kafka_producer_stopped")


async def publish(topic: str, payload: dict[str, Any], key: str | None = None) -> None:
    producer = await get_producer()
    encoded_key = key.encode("utf-8") if key else None
    await producer.send_and_wait(topic, payload, key=encoded_key)
    logger.info("kafka_message_published", topic=topic, key=key)


def create_consumer(topics: list[str], group_id: str | None = None) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id or settings.kafka_group_id,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

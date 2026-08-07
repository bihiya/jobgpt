"""Kafka producer/consumer client helpers."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

_producer: AIOKafkaProducer | None = None
_producer_lock = asyncio.Lock()
_KAFKA_CONNECT_TIMEOUT_S = 3.0
_KAFKA_PUBLISH_TIMEOUT_S = 5.0


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if not settings.kafka_enabled:
        raise ServiceUnavailableError(
            "Kafka is disabled (KAFKA_ENABLED=false)",
            code="KAFKA_DISABLED",
        )
    if _producer is not None:
        return _producer

    async with _producer_lock:
        if _producer is not None:
            return _producer
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=settings.kafka_client_id,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=int(_KAFKA_PUBLISH_TIMEOUT_S * 1000),
            metadata_max_age_ms=10_000,
        )
        try:
            await asyncio.wait_for(producer.start(), timeout=_KAFKA_CONNECT_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001
            try:
                await producer.stop()
            except Exception:  # noqa: BLE001
                pass
            logger.warning(
                "kafka_producer_start_failed",
                error=str(exc),
                servers=settings.kafka_bootstrap_servers,
            )
            raise ServiceUnavailableError(
                "Kafka is unavailable. Start Kafka locally or set KAFKA_ENABLED=false "
                "to use the development inline worker fallback.",
                code="KAFKA_UNAVAILABLE",
            ) from exc
        _producer = producer
        logger.info("kafka_producer_started", servers=settings.kafka_bootstrap_servers)
        return _producer


async def close_producer() -> None:
    global _producer
    async with _producer_lock:
        if _producer is not None:
            await _producer.stop()
            _producer = None
            logger.info("kafka_producer_stopped")


async def publish(topic: str, payload: dict[str, Any], key: str | None = None) -> None:
    """Publish to Kafka. Raises ServiceUnavailableError on timeout/connect failure."""
    if not settings.kafka_enabled:
        raise ServiceUnavailableError(
            "Kafka is disabled (KAFKA_ENABLED=false)",
            code="KAFKA_DISABLED",
        )
    try:
        producer = await get_producer()
        encoded_key = key.encode("utf-8") if key else None
        await asyncio.wait_for(
            producer.send_and_wait(topic, payload, key=encoded_key),
            timeout=_KAFKA_PUBLISH_TIMEOUT_S,
        )
    except ServiceUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        # Drop broken producer so the next call retries cleanly.
        global _producer
        async with _producer_lock:
            if _producer is not None:
                try:
                    await _producer.stop()
                except Exception:  # noqa: BLE001
                    pass
                _producer = None
        logger.warning("kafka_publish_failed", topic=topic, error=str(exc))
        raise ServiceUnavailableError(
            "Kafka publish failed or timed out. Is Kafka running on "
            f"{settings.kafka_bootstrap_servers}?",
            code="KAFKA_UNAVAILABLE",
        ) from exc
    logger.info("kafka_message_published", topic=topic, key=key)


def create_consumer(topics: list[str], group_id: str | None = None) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id or settings.kafka_group_id,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        request_timeout_ms=int(_KAFKA_PUBLISH_TIMEOUT_S * 1000),
    )

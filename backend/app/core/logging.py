"""Structured logging with correlation IDs."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.config import settings

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def add_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    cid = correlation_id_ctx.get()
    rid = request_id_ctx.get()
    if cid:
        event_dict["correlation_id"] = cid
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

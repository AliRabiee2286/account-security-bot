"""Technical log: structlog JSON, request_id on every line, redaction before any sink (S-010)."""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.redaction import redact
from app.core.request_context import get_actor, get_request_id


def _add_context(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    event_dict.setdefault("request_id", get_request_id())
    if (actor := get_actor()) is not None:
        event_dict.setdefault("actor", actor)
    return event_dict


def _redact(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    return redact(dict(event_dict))  # type: ignore[no-any-return]


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_context,
            structlog.processors.format_exc_info,
            _redact,  # MUST stay last before the renderer
            structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]

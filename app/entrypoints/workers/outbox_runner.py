"""arq-compatible outbox runner.

Important transaction rule: claim commits before external side effect. A crashed worker leaves
"delivering"; reclaim_stuck moves old deliveries back to pending. Handlers must be idempotent.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

from app.core.db import unit_of_work
from app.core.logging import get_logger
from app.core.outbox_dispatch import ClaimedMessage, claim_one, mark_delivered, mark_failed
from app.core.request_context import set_request_id

Handler = Callable[[ClaimedMessage], Awaitable[None]]
log = get_logger(__name__)


async def reclaim_stuck(*, age: timedelta = timedelta(minutes=10)) -> int:
    async with unit_of_work() as session:
        result = await session.execute(
            text("""
          UPDATE core.outbox SET status='pending', available_at=now(), delivering_at=NULL
           WHERE status='delivering' AND delivering_at < now() - CAST(:age AS interval)
        """),
            {"age": age},
        )
        return cast(CursorResult[Any], result).rowcount


async def run_once(handlers: dict[str, Handler]) -> bool:
    # Claim transaction commits when this context exits, releasing row lock before network I/O.
    async with unit_of_work() as session:
        message = await claim_one(session)
    if message is None:
        return False
    set_request_id(message.request_id)
    try:
        handler = handlers.get(message.event_type)
        if handler is None:
            raise RuntimeError(f"no handler registered for {message.event_type}")
        await handler(message)
    except Exception as exc:
        async with unit_of_work() as session:
            changed = await mark_failed(session, message.id, message.attempts, str(exc))
        if not changed:
            log.info("outbox.fence_rejected", operation="mark_failed", changed=False)
        return True
    else:
        async with unit_of_work() as session:
            changed = await mark_delivered(session, message.id, message.attempts)
        if not changed:
            log.info("outbox.fence_rejected", operation="mark_delivered", changed=False)
        return True

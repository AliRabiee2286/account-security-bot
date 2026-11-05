"""Reliable outbox delivery primitives: claim with SKIP LOCKED, bounded retries, dead-letter.

The handler receives only a message id and references. It must be idempotent by event id.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class ClaimedMessage:
    id: UUID
    event_type: str
    payload: dict[str, Any]
    request_id: str
    attempts: int


class EventHandler(Protocol):
    async def __call__(self, message: ClaimedMessage) -> None: ...


def backoff(attempts: int) -> timedelta:
    return timedelta(seconds=min(300, 2 ** max(0, attempts - 1)))


async def claim_one(session: AsyncSession) -> ClaimedMessage | None:
    result = await session.execute(
        text("""
      SELECT id, event_type, payload, request_id, attempts
        FROM core.outbox
       WHERE status = 'pending' AND available_at <= now()
       ORDER BY available_at, created_at
       LIMIT 1 FOR UPDATE SKIP LOCKED
    """)
    )
    row = result.mappings().first()
    if row is None:
        return None
    await session.execute(
        text("""
      UPDATE core.outbox SET status = 'delivering', attempts = attempts + 1, delivering_at = now()
       WHERE id = :id
    """),
        {"id": row["id"]},
    )
    return ClaimedMessage(
        row["id"], row["event_type"], row["payload"], row["request_id"], row["attempts"] + 1
    )


async def mark_delivered(session: AsyncSession, message_id: UUID, attempts: int) -> bool:
    result = await session.execute(
        text("""
      UPDATE core.outbox
         SET status = 'delivered', delivered_at = now(), delivering_at = NULL
       WHERE id = :id AND status = 'delivering' AND attempts = :attempts
    """),
        {"id": message_id, "attempts": attempts},
    )
    return cast(CursorResult[Any], result).rowcount == 1


async def mark_failed(session: AsyncSession, message_id: UUID, attempts: int, error: str) -> bool:
    status = "dead" if attempts >= MAX_ATTEMPTS else "pending"
    result = await session.execute(
        text("""
      UPDATE core.outbox
         SET status = :status,
             available_at = now() + CAST(:delay AS interval),
             last_error = :error,
             delivering_at = NULL
       WHERE id = :id AND status = 'delivering' AND attempts = :attempts
    """),
        {
            "id": message_id,
            "attempts": attempts,
            "status": status,
            "delay": backoff(attempts),
            "error": error[:500],
        },
    )
    return cast(CursorResult[Any], result).rowcount == 1

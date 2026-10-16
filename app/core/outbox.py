"""Transactional Outbox: external side effects are recorded in the same transaction,
then delivered by a worker with retries and idempotency (S-019)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin
from app.core.redaction import redact
from app.core.request_context import get_request_id


class OutboxMessage(IdMixin, Base):
    __tablename__ = "outbox"
    __table_args__ = {"schema": "core"}  # noqa: RUF012

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )  # references only, no secrets
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(String(500))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivering_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


async def enqueue(session: AsyncSession, event_type: str, payload: dict[str, Any]) -> None:
    session.add(
        OutboxMessage(event_type=event_type, payload=redact(payload), request_id=get_request_id())
    )

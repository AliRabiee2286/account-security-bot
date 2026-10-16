from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.ids import uuid7


class AuditEvent(Base):
    """Append-only. Partitioned monthly by occurred_at. UPDATE/DELETE blocked by DB trigger."""

    __tablename__ = "audit_events"
    __table_args__ = {"schema": "audit"}  # noqa: RUF012

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # employee|system|telegram_user
    actor_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. identity.employee.approved
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # success|denied|error
    reason: Mapped[str | None] = mapped_column(String(500))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    prev_hash: Mapped[str | None] = mapped_column(String(64))  # S-015 hash chain (filled by writer)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class Incident(IdMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = {"schema": "incidents"}  # noqa: RUF012 - SQLAlchemy table metadata
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low|medium|critical
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # employee|admin|scanner
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("identity.employees.id"), nullable=False)
    social_account_id: Mapped[UUID | None] = mapped_column(ForeignKey("social.social_accounts.id"))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    removal_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)

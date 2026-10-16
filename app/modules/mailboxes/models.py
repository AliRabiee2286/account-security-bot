from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class Mailbox(IdMixin, TimestampMixin, Base):
    __tablename__ = "mailboxes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','suspended','revoked')", name="status_valid"
        ),
        {"schema": "mailboxes"},
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(200), unique=True)
    address: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    current_owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.employees.id"))
    quota_group: Mapped[str | None] = mapped_column(String(100))
    recovery_secret_ciphertext: Mapped[bytes | None] = mapped_column()
    recovery_key_version: Mapped[int | None] = mapped_column()
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

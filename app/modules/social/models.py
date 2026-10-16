from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class SocialAccount(IdMixin, TimestampMixin, Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted','support_approved','verifying','verified',"
            "'verification_failed','suspended')",
            name="status_valid",
        ),
        {"schema": "social"},
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    mailbox_id: Mapped[UUID] = mapped_column(ForeignKey("mailboxes.mailboxes.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("identity.employees.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted")
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False)  # oauth | manual
    oauth_token_ciphertext: Mapped[bytes | None] = mapped_column()
    oauth_key_version: Mapped[int | None] = mapped_column()


class OneTimeForm(Base):
    __tablename__ = "one_time_forms"
    __table_args__ = {"schema": "social"}  # noqa: RUF012 - SQLAlchemy table metadata
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

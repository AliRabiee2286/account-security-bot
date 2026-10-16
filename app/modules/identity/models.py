from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin

SCHEMA = {"schema": "identity"}
EMPLOYEE_STATUSES = ("pending", "active", "suspended", "offboarded")


class Department(IdMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = SCHEMA
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.departments.id"))


class Role(IdMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = SCHEMA
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_role_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.roles.id"))
    is_observer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = SCHEMA
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    requires_second_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observer_may_execute: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = SCHEMA
    role_id: Mapped[UUID] = mapped_column(ForeignKey("identity.roles.id"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("identity.permissions.code"), primary_key=True
    )


class Employee(IdMixin, TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(f"status IN {EMPLOYEE_STATUSES}", name="status_valid"),
        SCHEMA,
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    role_id: Mapped[UUID] = mapped_column(ForeignKey("identity.roles.id"), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(ForeignKey("identity.departments.id"))
    approved_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

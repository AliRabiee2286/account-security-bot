from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class EmployeeRegistered(DomainEvent):
    name: ClassVar[str] = "identity.employee.registered"
    employee_id: UUID


@dataclass(frozen=True, kw_only=True)
class EmployeeApproved(DomainEvent):
    name: ClassVar[str] = "identity.employee.approved"
    employee_id: UUID
    approved_by: UUID

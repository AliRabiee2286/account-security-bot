from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MailboxProvisioned(DomainEvent):
    name: ClassVar[str] = "mailboxes.mailbox.provisioned"
    mailbox_id: UUID
    employee_id: UUID


@dataclass(frozen=True, kw_only=True)
class MailboxSuspended(DomainEvent):
    name: ClassVar[str] = "mailboxes.mailbox.suspended"
    mailbox_id: UUID
    reason: str

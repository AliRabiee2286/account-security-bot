from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.core.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class SocialAccountSubmitted(DomainEvent):
    name: ClassVar[str] = "social.account.submitted"
    account_id: UUID


@dataclass(frozen=True, kw_only=True)
class SocialAccountVerified(DomainEvent):
    name: ClassVar[str] = "social.account.verified"
    account_id: UUID

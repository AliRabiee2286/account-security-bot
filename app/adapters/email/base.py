"""D-003 / D-010: Email Provider contract. Atomic Mail and any JMAP server are adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ProvisionedMailbox:
    address: str
    provider_ref: str
    recovery_secret: bytes | None  # seed phrase etc. Caller MUST seal it immediately (S-003)


@dataclass(frozen=True)
class MessageSummary:
    provider_id: str
    sender: str
    subject: str
    received_at: datetime


@runtime_checkable
class EmailProvider(Protocol):
    code: str

    async def create_mailbox(self, *, local_part_hint: str) -> ProvisionedMailbox: ...
    async def suspend(self, provider_ref: str) -> None: ...
    async def search(
        self, provider_ref: str, *, sender_domains: list[str], since: datetime | None = None
    ) -> list[MessageSummary]:
        """Used for D-002 verification: find official platform emails in the inbox."""
        ...


_REGISTRY: dict[str, type[EmailProvider]] = {}


def register(code: str):  # type: ignore[no-untyped-def]
    def deco(cls: type[EmailProvider]) -> type[EmailProvider]:
        _REGISTRY[code] = cls
        return cls

    return deco


def get_provider_class(code: str) -> type[EmailProvider]:
    try:
        return _REGISTRY[code]
    except KeyError as exc:
        raise LookupError(f"email provider '{code}' is not registered") from exc

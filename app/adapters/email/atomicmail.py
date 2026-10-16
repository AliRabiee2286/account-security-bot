"""Atomic Mail adapter (JMAP). Implemented in Phase 3; contract fixed now.

Known constraints (phase0/platform_api_research.md): open alpha, no SLA, scrypt PoW (~30s) per
inbox, no custom domain, no IMAP/SMTP. PoW must run in a dedicated process pool worker.
"""

from __future__ import annotations

from datetime import datetime

from app.adapters.email.base import MessageSummary, ProvisionedMailbox, register


@register("atomicmail")
class AtomicMailProvider:
    code = "atomicmail"

    async def create_mailbox(self, *, local_part_hint: str) -> ProvisionedMailbox:
        raise NotImplementedError("Phase 3")

    async def suspend(self, provider_ref: str) -> None:
        raise NotImplementedError("Phase 3")

    async def search(
        self, provider_ref: str, *, sender_domains: list[str], since: datetime | None = None
    ) -> list[MessageSummary]:
        raise NotImplementedError("Phase 3")

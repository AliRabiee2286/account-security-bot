from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def last_hash_locked(self) -> str | None:
        # Serialize chain writers with a transaction-scoped advisory lock.
        await self.s.execute(text("SELECT pg_advisory_xact_lock(hashtext('audit_chain'))"))
        stmt = select(AuditEvent.row_hash).order_by(
            AuditEvent.occurred_at.desc(), AuditEvent.id.desc()
        )
        return (await self.s.execute(stmt.limit(1))).scalar_one_or_none()

    def add(self, event: AuditEvent) -> None:
        self.s.add(event)

"""Public contract of the audit module (D-009 rule 1)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_contract import SecurityAuditRecorder
from app.modules.audit.service import Result, record


async def audit_security_event(
    session: AsyncSession,
    *,
    action: str,
    actor_id: UUID,
    target_id: UUID,
) -> None:
    """Adapt the public audit service to the callback contract used by core."""
    await record(
        session,
        action=action,
        actor_type="employee",
        actor_id=str(actor_id),
        target_type="session",
        target_id=str(target_id),
    )


__all__ = ["Result", "SecurityAuditRecorder", "audit_security_event", "record"]

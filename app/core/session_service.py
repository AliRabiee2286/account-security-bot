from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_contract import SecurityAuditRecorder
from app.core.session import SESSION_TTL, issue_session


async def create_session(session: AsyncSession, *, employee_id: UUID, amr: tuple[str, ...]) -> str:
    raw, token_hash = issue_session()
    await session.execute(
        text("""
      INSERT INTO identity.sessions(id, employee_id, token_hash, expires_at, amr)
      VALUES (gen_random_uuid(), :employee_id, :token_hash, :expires_at, :amr)
    """),
        {
            "employee_id": employee_id,
            "token_hash": token_hash,
            "expires_at": datetime.now(UTC) + SESSION_TTL,
            "amr": ",".join(amr),
        },
    )
    return raw


async def revoke_session(
    session: AsyncSession,
    *,
    session_id: UUID,
    actor_id: UUID,
    audit_recorder: SecurityAuditRecorder,
) -> None:
    await session.execute(
        text("""UPDATE identity.sessions SET revoked_at=now()
                                  WHERE id=:id AND revoked_at IS NULL"""),
        {"id": session_id},
    )
    await audit_recorder(
        session,
        action="auth.session.revoked",
        actor_id=actor_id,
        target_id=session_id,
    )

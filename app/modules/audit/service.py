from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.core.redaction import redact
from app.core.request_context import get_request_id
from app.modules.audit.hashing import chain_hash
from app.modules.audit.models import AuditEvent
from app.modules.audit.repository import AuditRepository

Result = Literal["success", "denied", "error"]


async def record(
    session: AsyncSession,
    *,
    action: str,
    actor_type: str,
    actor_id: str | None,
    result: Result = "success",
    target_type: str | None = None,
    target_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write an audit row in the caller's transaction (database principle #6)."""
    repo = AuditRepository(session)
    prev = await repo.last_hash_locked()
    event_id, occurred_at = uuid7(), datetime.now(UTC)
    body = {
        "id": str(event_id),
        "occurred_at": occurred_at.isoformat(),
        "request_id": get_request_id(),
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "result": result,
        "reason": reason,
        "metadata": redact(metadata or {}),
    }
    repo.add(
        AuditEvent(
            id=event_id,
            occurred_at=occurred_at,
            request_id=body["request_id"],
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result,
            reason=reason,
            metadata_=body["metadata"],
            prev_hash=prev,
            row_hash=chain_hash(prev, body),
        )
    )

"""Two-person approval records. A request and approver must be distinct identities."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PermissionDenied
from app.modules.audit import api as audit


async def request_approval(
    session: AsyncSession, *, action: str, target_type: str, target_id: UUID, requested_by: UUID
) -> UUID:
    result = await session.execute(
        text("""
      INSERT INTO identity.approval_requests(id, action, target_type, target_id, requested_by)
      VALUES (gen_random_uuid(), :action, :target_type, :target_id, :requested_by) RETURNING id
    """),
        {
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "requested_by": requested_by,
        },
    )
    approval_id = cast(UUID, result.scalar_one())
    await audit.record(
        session,
        action="approval.requested",
        actor_type="employee",
        actor_id=str(requested_by),
        target_type="approval_request",
        target_id=str(approval_id),
    )
    return approval_id


async def approve(session: AsyncSession, *, approval_id: UUID, approver_id: UUID) -> None:
    result = await session.execute(
        text("""
      UPDATE identity.approval_requests SET approved_by=:approver, approved_at=now()
       WHERE id=:id AND approved_by IS NULL AND requested_by <> :approver
       RETURNING id, action, target_type, target_id, requested_by
    """),
        {"id": approval_id, "approver": approver_id},
    )
    row = result.mappings().first()
    if row is None:
        raise PermissionDenied("missing request, already approved, or self-approval")
    await audit.record(
        session,
        action="approval.granted",
        actor_type="employee",
        actor_id=str(approver_id),
        target_type=row["target_type"],
        target_id=str(row["target_id"]),
    )

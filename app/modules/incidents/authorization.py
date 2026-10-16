"""Incident authorization facade. All sensitive transitions go through identity's public API."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PermissionDenied
from app.modules.identity import api as identity


async def require_sensitive_incident_action(
    session: AsyncSession, *, actor_id: UUID, target_id: UUID
) -> None:
    decision = await identity.authorize_employee_action(
        session,
        actor_id=actor_id,
        permission=identity.permissions.CONTENT_REMOVE,
        target_id=target_id,
    )
    if not decision.allowed:
        raise PermissionDenied(decision.reason)
    if decision.needs_second_approval:
        raise PermissionDenied("second approval required")

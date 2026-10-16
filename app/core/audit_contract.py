"""Typed callback contract used by core security services."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class SecurityAuditRecorder(Protocol):
    """Application-owned callback for recording security events."""

    async def __call__(
        self,
        session: AsyncSession,
        *,
        action: str,
        actor_id: UUID,
        target_id: UUID,
    ) -> None: ...


__all__ = ["SecurityAuditRecorder"]

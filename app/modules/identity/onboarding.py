"""Phase 2 onboarding: Telegram identity proof + admin approval, never auto-admit."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, PermissionDenied, ValidationFailed
from app.core.request_context import set_actor
from app.modules.audit import api as audit
from app.modules.identity.models import Employee
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import EmployeeDTO, RegisterRequest
from app.modules.identity.service import register


async def telegram_register(
    session: AsyncSession, *, telegram_user_id: int, full_name: str
) -> EmployeeDTO:
    """Telegram ID is evidence of chat origin, not employment. Result stays pending."""
    set_actor(f"tg:{telegram_user_id}")
    return await register(
        session, RegisterRequest(telegram_user_id=telegram_user_id, full_name=full_name)
    )


async def reject_pending(
    session: AsyncSession, *, actor_id: UUID, employee_id: UUID, reason: str
) -> None:
    repo = IdentityRepository(session)
    actor = await repo.get(actor_id)
    target = await repo.get(employee_id, for_update=True)
    if actor is None or target is None:
        raise NotFound("employee")
    decision = await __import__("app.modules.identity.service", fromlist=["check"]).check(
        session, actor, "employee.approve", target
    )
    if not decision.allowed:
        raise PermissionDenied(decision.reason)
    if target.status != "pending":
        raise ValidationFailed("employee is not pending")
    target.status = "suspended"
    await audit.record(
        session,
        action="identity.employee.rejected",
        actor_type="employee",
        actor_id=str(actor_id),
        target_type="employee",
        target_id=str(employee_id),
        reason=reason,
    )


async def require_active(session: AsyncSession, employee_id: UUID) -> Employee:
    employee = await IdentityRepository(session).get(employee_id)
    if employee is None or employee.status != "active":
        raise PermissionDenied("active employee required")
    return employee

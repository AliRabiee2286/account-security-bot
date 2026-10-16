from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApprovalRequired, NotFound, PermissionDenied, ValidationFailed
from app.core.events import bus
from app.modules.audit import api as audit
from app.modules.identity import permissions as P
from app.modules.identity.events import EmployeeApproved, EmployeeRegistered
from app.modules.identity.models import Employee
from app.modules.identity.rbac import Decision, authorize, department_subtree
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import EmployeeDTO, RegisterRequest


async def get_active_employee(session: AsyncSession, employee_id: UUID) -> EmployeeDTO | None:
    """Public read contract for other modules; do not expose ORM models across module boundaries."""
    emp = await IdentityRepository(session).get(employee_id)
    return EmployeeDTO.model_validate(emp) if emp and emp.status == "active" else None


async def find_active_by_telegram(session: AsyncSession, tg_id: int) -> EmployeeDTO | None:
    """S-005 allowlist: only active employees get a real answer from the bot."""
    emp = await IdentityRepository(session).by_telegram_id(tg_id)
    return EmployeeDTO.model_validate(emp) if emp and emp.status == "active" else None


async def register(session: AsyncSession, req: RegisterRequest) -> EmployeeDTO:
    """Self-registration always lands in 'pending'. Nobody is admitted automatically."""
    repo = IdentityRepository(session)
    existing = await repo.by_telegram_id(req.telegram_user_id)
    if existing is not None:
        return EmployeeDTO.model_validate(existing)
    role = await repo.role_by_code("employee")
    emp = Employee(telegram_user_id=req.telegram_user_id, full_name=req.full_name, role_id=role.id)
    repo.add(emp)
    await session.flush()
    await audit.record(
        session,
        action="identity.employee.registered",
        actor_type="telegram_user",
        actor_id=str(req.telegram_user_id),
        target_type="employee",
        target_id=str(emp.id),
    )
    await bus.publish(EmployeeRegistered(employee_id=emp.id))
    return EmployeeDTO.model_validate(emp)


async def check(
    session: AsyncSession,
    actor: Employee,
    permission: str,
    target: Employee | None,
    *,
    operation: Literal["view", "execute"] = "execute",
) -> Decision:
    repo = IdentityRepository(session)
    role = await repo.role(actor.role_id)
    scope: frozenset[UUID] | None = None
    if role.code not in ("super_observer", "security_lead"):  # global-scope roles
        if actor.department_id is None:
            scope = frozenset()
        else:
            scope = department_subtree(actor.department_id, await repo.department_parents())
    decision = authorize(
        graph=await repo.role_graph(),
        perms=await repo.permission_defs(),
        actor_role=actor.role_id,
        actor_is_observer=role.is_observer,
        permission=permission,
        actor_scope=scope,
        target_department=target.department_id if target else None,
        actor_id=actor.id,
        target_employee_id=target.id if target else None,
        operation=operation,
    )
    if not decision.allowed:
        await audit.record(
            session,
            action=f"authz.{permission}",
            actor_type="employee",
            actor_id=str(actor.id),
            result="denied",
            target_type="employee",
            target_id=str(target.id) if target else None,
            reason=decision.reason,
        )
    return decision


async def approve(session: AsyncSession, *, actor_id: UUID, employee_id: UUID) -> EmployeeDTO:
    repo = IdentityRepository(session)
    actor = await repo.get(actor_id)
    target = await repo.get(employee_id, for_update=True)
    if actor is None or actor.status != "active":
        raise PermissionDenied("inactive actor")
    if target is None:
        raise NotFound("employee")
    if target.status != "pending":
        raise ValidationFailed("employee is not pending", status=target.status)
    if actor.id == target.id:
        raise PermissionDenied("self approval is forbidden")
    decision = await check(session, actor, P.EMPLOYEE_APPROVE, target)
    if not decision.allowed:
        raise PermissionDenied(decision.reason)
    if decision.needs_second_approval:
        raise ApprovalRequired(P.EMPLOYEE_APPROVE)
    target.status, target.approved_by, target.approved_at = "active", actor.id, datetime.now(UTC)
    await audit.record(
        session,
        action="identity.employee.approved",
        actor_type="employee",
        actor_id=str(actor.id),
        target_type="employee",
        target_id=str(target.id),
    )
    await bus.publish(EmployeeApproved(employee_id=target.id, approved_by=actor.id))
    return EmployeeDTO.model_validate(target)


async def authorize_employee_action(
    session: AsyncSession,
    *,
    actor_id: UUID,
    permission: str,
    target_id: UUID | None = None,
    operation: Literal["view", "execute"] = "execute",
) -> Decision:
    """Public permission check; view decisions authorize reads only, never execution."""
    repo = IdentityRepository(session)
    actor = await repo.get(actor_id)
    target = await repo.get(target_id) if target_id is not None else None
    if actor is None or actor.status != "active":
        return Decision(False, reason="inactive_actor")
    if target_id is not None and target is None:
        return Decision(False, reason="target_not_found")
    return await check(session, actor, permission, target, operation=operation)

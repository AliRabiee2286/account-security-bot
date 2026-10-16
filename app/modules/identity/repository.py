from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Department, Employee, Permission, Role, RolePermission
from app.modules.identity.permissions import CATALOGUE
from app.modules.identity.rbac import PermissionDef, RoleGraph, RoleNode


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def by_telegram_id(self, tg_id: int) -> Employee | None:
        stmt = select(Employee).where(Employee.telegram_user_id == tg_id)
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def get(self, employee_id: UUID, *, for_update: bool = False) -> Employee | None:
        stmt = select(Employee).where(Employee.id == employee_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def role_by_code(self, code: str) -> Role:
        return (await self.s.execute(select(Role).where(Role.code == code))).scalar_one()

    async def role(self, role_id: UUID) -> Role:
        return (await self.s.execute(select(Role).where(Role.id == role_id))).scalar_one()

    async def role_graph(self) -> RoleGraph:
        roles = (await self.s.execute(select(Role))).scalars().all()
        links = (await self.s.execute(select(RolePermission))).scalars().all()
        by_role: dict[UUID, set[str]] = {r.id: set() for r in roles}
        for link in links:
            by_role[link.role_id].add(link.permission_code)
        return RoleGraph(
            RoleNode(r.id, r.code, r.parent_role_id, frozenset(by_role[r.id])) for r in roles
        )

    async def permission_defs(self) -> dict[str, PermissionDef]:
        rows = (await self.s.execute(select(Permission))).scalars().all()
        return {
            p.code: PermissionDef(
                p.code,
                requires_second_approval=p.requires_second_approval,
                observer_may_execute=p.observer_may_execute,
                observer_may_view=p.code in CATALOGUE and CATALOGUE[p.code].observer_may_view,
            )
            for p in rows
        }

    async def department_parents(self) -> dict[UUID, UUID | None]:
        rows = (await self.s.execute(select(Department.id, Department.parent_id))).all()
        return {r[0]: r[1] for r in rows}

    def add(self, employee: Employee) -> None:
        self.s.add(employee)

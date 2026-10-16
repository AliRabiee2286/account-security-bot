from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_context import AuthContext
from app.core.db import unit_of_work
from app.core.errors import AppError
from app.entrypoints.api.dependencies import current_auth
from app.modules.identity.api import approve

router = APIRouter(prefix="/identity", tags=["identity"])


@router.post("/employees/{employee_id}/approve")
async def approve_employee(
    employee_id: UUID,
    ctx: AuthContext = Depends(current_auth),  # noqa: B008 - FastAPI dependency injection
) -> dict[str, str]:
    async with unit_of_work() as session:
        try:
            dto = await approve(session, actor_id=ctx.employee_id, employee_id=employee_id)
        except AppError as exc:
            raise HTTPException(status_code=403, detail=exc.user_message) from exc
    return {"id": str(dto.id), "status": dto.status}

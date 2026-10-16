from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth_context import require_authentication
from app.core.db import unit_of_work
from app.core.errors import AppError
from app.modules.incidents import api as incident_api

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentReportBody(BaseModel):
    severity: str = Field(pattern=r"^(low|medium|critical)$")
    social_account_id: UUID | None = None
    summary: str = Field(min_length=10, max_length=2000)


# Authentication middleware is intentionally a dependency boundary for Phase 2.
# It must resolve an active employee, never trust an ID from request body.
async def current_employee_id() -> UUID:
    try:
        return (await require_authentication()).employee_id
    except Exception as exc:
        raise HTTPException(status_code=503, detail="authentication is not configured") from exc


@router.post("", status_code=201)
async def report_incident(
    body: IncidentReportBody,
    actor_id: UUID = Depends(current_employee_id),  # noqa: B008 - FastAPI dependency injection
) -> incident_api.IncidentDTO:
    async with unit_of_work() as session:
        try:
            return await incident_api.report(
                session,
                request=incident_api.IncidentReport(**body.model_dump()),
                reporter_id=actor_id,
            )
        except AppError as exc:
            raise HTTPException(status_code=400, detail=exc.user_message) from exc

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class IncidentReport(BaseModel):
    severity: str = Field(pattern=r"^(low|medium|critical)$")
    social_account_id: UUID | None = None
    summary: str = Field(min_length=10, max_length=2000)


class IncidentDTO(IncidentReport):
    id: UUID
    status: str
    source: str
    owner_id: UUID

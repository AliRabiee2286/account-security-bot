from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmployeeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)
    id: UUID
    telegram_user_id: int
    full_name: str
    status: str
    role_id: UUID
    department_id: UUID | None


class RegisterRequest(BaseModel):
    telegram_user_id: int = Field(gt=0)
    full_name: str = Field(min_length=3, max_length=200, pattern=r"^[^\x00-\x1f<>]+$")

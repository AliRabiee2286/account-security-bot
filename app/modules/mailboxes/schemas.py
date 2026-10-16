from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MailboxDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)
    id: UUID
    provider: str
    address: str
    status: str
    current_owner_id: UUID | None


class MailboxRequest(BaseModel):
    employee_id: UUID
    provider: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_-]{1,49}$")
    local_part_hint: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]+$")

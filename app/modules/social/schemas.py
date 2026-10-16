from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SocialAccountDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)
    id: UUID
    platform: str
    handle: str
    owner_id: UUID
    purpose: str
    status: str
    auth_type: str


class SocialAccountRequest(BaseModel):
    platform: str = Field(pattern=r"^(instagram|x|telegram)$")
    handle: str = Field(min_length=1, max_length=255, pattern=r"^[^\x00-\x1f<>]+$")
    mailbox_id: UUID
    purpose: str = Field(min_length=10, max_length=500)
    auth_type: str = Field(pattern=r"^(oauth|manual)$")

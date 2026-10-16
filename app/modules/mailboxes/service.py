"""Mailbox business logic. Slow provider calls belong in arq, not Telegram handlers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, ValidationFailed
from app.core.ids import uuid7
from app.modules.audit import api as audit
from app.modules.identity import api as identity
from app.modules.mailboxes.models import Mailbox
from app.modules.mailboxes.repository import MailboxRepository
from app.modules.mailboxes.schemas import MailboxDTO, MailboxRequest


async def request_provision(
    session: AsyncSession, *, request: MailboxRequest, actor_id: UUID
) -> MailboxDTO:
    employee = await identity.get_active_employee(session, request.employee_id)
    if employee is None:
        raise NotFound("active employee")
    if employee.id != actor_id:
        raise ValidationFailed("self or permitted manager required")
    if request.provider not in {"atomicmail", "google_workspace", "microsoft_365", "migadu"}:
        raise ValidationFailed("provider not enabled")
    # No network call here. Outbox/worker will create it and then persist provider_ref.
    mailbox = Mailbox(
        provider=request.provider,
        address=f"pending+{uuid7().hex}@invalid.local",
        status="pending",
        current_owner_id=employee.id,
    )
    MailboxRepository(session).add(mailbox)
    await session.flush()
    await audit.record(
        session,
        action="mailbox.provision.requested",
        actor_type="employee",
        actor_id=str(actor_id),
        target_type="mailbox",
        target_id=str(mailbox.id),
        metadata={"provider": request.provider},
    )
    return MailboxDTO.model_validate(mailbox)


async def get_active_owned_mailbox(
    session: AsyncSession, *, mailbox_id: UUID, owner_id: UUID
) -> MailboxDTO | None:
    mailbox = await MailboxRepository(session).get(mailbox_id)
    if mailbox is None or mailbox.status != "active" or mailbox.current_owner_id != owner_id:
        return None
    return MailboxDTO.model_validate(mailbox)

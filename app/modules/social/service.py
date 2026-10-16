from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, ValidationFailed
from app.core.ids import uuid7
from app.modules.audit import api as audit
from app.modules.identity import api as identity
from app.modules.mailboxes import api as mailboxes
from app.modules.social.models import SocialAccount
from app.modules.social.schemas import SocialAccountDTO, SocialAccountRequest


async def submit(
    session: AsyncSession, *, request: SocialAccountRequest, owner_id: UUID
) -> SocialAccountDTO:
    employee = await identity.get_active_employee(session, owner_id)
    mailbox = await mailboxes.get_active_owned_mailbox(
        session, mailbox_id=request.mailbox_id, owner_id=owner_id
    )
    if employee is None:
        raise NotFound("active employee")
    if mailbox is None:
        raise ValidationFailed("mailbox is not assigned and active")
    if request.auth_type == "manual":
        # Passwords are never accepted by this method. The secure form is the only path.
        raise ValidationFailed("manual credential entry must use a one-time secure form")
    account = SocialAccount(
        id=uuid7(),
        platform=request.platform,
        handle=request.handle,
        mailbox_id=request.mailbox_id,
        owner_id=owner_id,
        purpose=request.purpose,
        auth_type=request.auth_type,
        status="submitted",
    )
    session.add(account)
    await session.flush()
    await audit.record(
        session,
        action="social.account.submitted",
        actor_type="employee",
        actor_id=str(owner_id),
        target_type="social_account",
        target_id=str(account.id),
        metadata={"platform": request.platform, "handle": request.handle},
    )
    return SocialAccountDTO.model_validate(account)

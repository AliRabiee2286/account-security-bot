from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mailboxes.models import Mailbox


class MailboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def get(self, mailbox_id: UUID, *, lock: bool = False) -> Mailbox | None:
        stmt = select(Mailbox).where(Mailbox.id == mailbox_id)
        if lock:
            stmt = stmt.with_for_update()
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def for_employee(self, employee_id: UUID) -> list[Mailbox]:
        return list(
            (
                await self.s.execute(select(Mailbox).where(Mailbox.current_owner_id == employee_id))
            ).scalars()
        )

    def add(self, mailbox: Mailbox) -> None:
        self.s.add(mailbox)

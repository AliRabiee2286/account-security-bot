"""DB-backed one-time forms. Consume is one conditional UPDATE: one winner only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.one_time_form import FormClaims
from app.core.token_hash import hash_token


@dataclass(frozen=True)
class ConsumedForm:
    subject_id: UUID
    owner_type: str
    owner_id: UUID
    purpose: str


async def issue_form(
    session: AsyncSession,
    *,
    subject_id: UUID,
    purpose: str,
    owner_type: str,
    owner_id: UUID,
    ttl: timedelta = timedelta(minutes=10),
) -> str:
    if owner_type not in {"social_account", "mailbox"}:
        raise ValueError("unsupported form owner type")
    claims, raw = FormClaims.issue(subject_id=str(subject_id), purpose=purpose, ttl=ttl)
    await session.execute(
        text(
            """
      INSERT INTO social.one_time_forms(
        token_hash, subject_id, purpose, owner_type, owner_id, expires_at
      ) VALUES (:hash, :subject, :purpose, :owner_type, :owner_id, :expires)
    """
        ),
        {
            "hash": claims.token_hash,
            "subject": subject_id,
            "purpose": purpose,
            "owner_type": owner_type,
            "owner_id": owner_id,
            "expires": claims.expires_at,
        },
    )
    return raw


async def consume_form(
    session: AsyncSession, *, raw_token: str, purpose: str
) -> ConsumedForm | None:
    if not raw_token or not purpose:
        return None
    result = await session.execute(
        text(
            """
      UPDATE social.one_time_forms
         SET consumed_at = now()
       WHERE token_hash = :hash AND purpose = :purpose
         AND consumed_at IS NULL AND expires_at > now()
       RETURNING subject_id, owner_type, owner_id, purpose
    """
        ),
        {"hash": hash_token(raw_token), "purpose": purpose},
    )
    row = result.mappings().first()
    return (
        ConsumedForm(row["subject_id"], row["owner_type"], row["owner_id"], row["purpose"])
        if row
        else None
    )

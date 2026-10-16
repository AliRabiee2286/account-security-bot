"""Credential persistence contract: ciphertext only, envelope encrypted.

This module intentionally does not expose plaintext after write. The form endpoint will call
store_secret with a KeyProvider and immediately discard the request value.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import KeyProvider, new_dek, seal
from app.core.ids import uuid7

MAX_SECRET_LENGTH = 4096


async def store_secret(
    session: AsyncSession,
    *,
    owner_type: str,
    owner_id: UUID,
    plaintext: str,
    provider: KeyProvider,
    auth_type: str,
) -> None:
    if not plaintext or len(plaintext) > MAX_SECRET_LENGTH:
        raise ValueError("invalid secret")
    dek = new_dek()
    wrapped = provider.wrap(dek, context=f"{owner_type}:{owner_id}".encode())
    sealed = seal(
        dek,
        plaintext.encode("utf-8"),
        owner_type=owner_type,
        owner_id=str(owner_id),
        key_version=provider.kek_version,
    )
    await session.execute(
        text("""
      INSERT INTO social.credentials(id, owner_type, owner_id, ciphertext, wrapped_dek,
        key_version, auth_type, created_at)
      VALUES (:id, :owner_type, :owner_id, :ciphertext, :wrapped_dek, :version, :auth_type, :now)
    """),
        {
            "id": uuid7(),
            "owner_type": owner_type,
            "owner_id": owner_id,
            "ciphertext": sealed.ciphertext,
            "wrapped_dek": wrapped,
            "version": provider.kek_version,
            "auth_type": auth_type,
            "now": datetime.now(UTC),
        },
    )
    # plaintext is not returned, logged, cached, or included in an event.

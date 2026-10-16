"""Short-lived authenticated sessions. Store only a hash of the bearer token."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.token_hash import hash_token, matches_token

SESSION_TTL = timedelta(minutes=30)


def issue_session() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def verify_session(raw: str, stored_hash: str) -> bool:
    return matches_token(raw, stored_hash)


@dataclass(frozen=True)
class SessionClaims:
    employee_id: UUID
    session_id: UUID
    token_hash: str
    expires_at: datetime
    amr: tuple[str, ...]

    def active(self, now: datetime | None = None) -> bool:
        return self.expires_at > (now or datetime.now(UTC))

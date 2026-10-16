"""S-002/S-012: one-time secret form primitives.

The service implementation stores only a hash of the nonce. A token is:
  base64url(opaque_id).base64url(random_secret)
The random secret is never persisted. Consume is atomic at the DB layer in the
integration repository: UPDATE ... WHERE consumed_at IS NULL AND expires_at > now().
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.token_hash import hash_token, matches_token

TOKEN_BYTES = 32
OPAQUE_ID_BYTES = 16
DEFAULT_TTL = timedelta(minutes=10)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def generate_token() -> tuple[str, str, str]:
    """Return (opaque_id, raw_token, token_hash). Only raw_token is sent to the user."""
    opaque_id = _b64(secrets.token_bytes(OPAQUE_ID_BYTES))
    secret = _b64(secrets.token_bytes(TOKEN_BYTES))
    raw = f"{opaque_id}.{secret}"
    return opaque_id, raw, hash_token(raw)


def token_matches(raw_token: str, stored_hash: str) -> bool:
    """Backward-compatible form API for constant-time token verification."""

    return matches_token(raw_token, stored_hash)


def validate_token_shape(raw_token: str) -> bool:
    try:
        opaque, secret = raw_token.split(".", 1)
        return len(_unb64(opaque)) == OPAQUE_ID_BYTES and len(_unb64(secret)) == TOKEN_BYTES
    except (ValueError, UnicodeError):
        return False


@dataclass(frozen=True)
class FormClaims:
    opaque_id: str
    subject_id: str
    purpose: str
    expires_at: datetime
    token_hash: str

    @classmethod
    def issue(
        cls, *, subject_id: str, purpose: str, ttl: timedelta = DEFAULT_TTL
    ) -> tuple[FormClaims, str]:
        opaque_id, raw, token_hash = generate_token()
        return (
            cls(
                opaque_id=opaque_id,
                subject_id=subject_id,
                purpose=purpose,
                expires_at=datetime.now(UTC) + ttl,
                token_hash=token_hash,
            ),
            raw,
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        return self.expires_at <= (now or datetime.now(UTC))

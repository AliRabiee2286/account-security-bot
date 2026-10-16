"""Shared token hashing primitives.

Only deterministic digests cross persistence boundaries; raw bearer and form
tokens remain in local call scope and are never included in a stored value.
"""

from __future__ import annotations

import hashlib
import hmac


def hash_token(raw_token: str) -> str:
    """Return the lowercase SHA-256 digest for a token."""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def matches_token(raw_token: str, stored_hash: str) -> bool:
    """Compare a raw token with its stored digest in constant time."""

    return hmac.compare_digest(hash_token(raw_token), stored_hash)

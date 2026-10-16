"""OAuth 2.0 Authorization Code + PKCE primitives (S-016).

State and code_verifier are one-time values stored hashed server-side. Never put tokens in
Telegram or query strings. Provider adapters validate issuer, audience, redirect URI and state.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def pkce_pair() -> tuple[str, str]:
    verifier = b64(secrets.token_bytes(32))
    challenge = b64(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def state_pair() -> tuple[str, str]:
    raw = b64(secrets.token_bytes(32))
    return raw, hashlib.sha256(raw.encode("ascii")).hexdigest()


def state_matches(raw: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hashlib.sha256(raw.encode("ascii")).hexdigest(), stored_hash)


@dataclass(frozen=True)
class OAuthStart:
    provider: str
    state_hash: str
    code_verifier: str
    redirect_uri: str

    @classmethod
    def issue(cls, *, provider: str, redirect_uri: str) -> tuple[OAuthStart, str, str]:
        state, state_hash = state_pair()
        verifier, challenge = pkce_pair()
        return cls(provider, state_hash, verifier, redirect_uri), state, challenge

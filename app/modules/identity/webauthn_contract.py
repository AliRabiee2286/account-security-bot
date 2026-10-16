"""WebAuthn boundary. Use a reviewed FIDO2/WebAuthn library for actual ceremony verification.
Never accept client-provided credential IDs or assertions without cryptographic verification.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RegistrationOptions:
    challenge: bytes
    rp_id: str
    user_id: UUID


@dataclass(frozen=True)
class AssertionResult:
    credential_id: bytes
    sign_count: int
    user_verified: bool


class WebAuthnVerifier(Protocol):
    def verify_registration(
        self, *, options: RegistrationOptions, response: Mapping[str, object]
    ) -> bytes: ...
    def verify_assertion(
        self, *, challenge: bytes, response: Mapping[str, object]
    ) -> AssertionResult: ...


class WebAuthnNotConfigured(RuntimeError):
    pass


def require_verified_assertion(result: AssertionResult) -> None:
    if not result.user_verified or result.sign_count < 0:
        raise WebAuthnNotConfigured("verified WebAuthn assertion required")

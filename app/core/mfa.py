"""MFA policy boundary. Privileged actions require phishing-resistant WebAuthn."""

from __future__ import annotations

from dataclasses import dataclass

PHISHING_RESISTANT = frozenset({"webauthn"})


@dataclass(frozen=True)
class MFAResult:
    satisfied: bool
    methods: frozenset[str]


def require_privileged_mfa(methods: set[str]) -> MFAResult:
    normalized = frozenset(methods)
    if not normalized & PHISHING_RESISTANT:
        return MFAResult(False, normalized)
    return MFAResult(True, normalized)

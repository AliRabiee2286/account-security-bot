"""WebAuthn enrollment policy. Cryptographic assertion verification belongs to a reviewed
WebAuthn library; never implement ceremony verification by hand."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebAuthnPolicy:
    rp_id: str
    origin: str
    user_verification: str = "required"
    resident_key: str = "required"
    attestation: str = "none"

    def validate(self) -> None:
        if not self.rp_id or not self.origin.startswith("https://"):
            raise ValueError("production WebAuthn requires HTTPS origin and RP ID")
        if self.user_verification != "required" or self.resident_key != "required":
            raise ValueError(
                "privileged accounts require user verification and discoverable credential"
            )
